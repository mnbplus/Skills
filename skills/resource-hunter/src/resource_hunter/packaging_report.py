from __future__ import annotations

import json
import os
import sys
import tempfile
import zipfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import ResourceHunterError


PACKAGING_BASELINE_REPORT_SCHEMA_VERSION = 1
DEFAULT_PACKAGING_BASELINE_ARTIFACT = Path("artifacts") / "packaging-baseline" / "packaging-baseline.json"
_PACKAGING_BASELINE_ARTIFACT_NAME = DEFAULT_PACKAGING_BASELINE_ARTIFACT.name


class PackagingBaselineReportError(ResourceHunterError):
    def __init__(self, message: str, *, download_payload: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        self.download_payload = _copy_mapping(download_payload)


@dataclass(frozen=True)
class _ArtifactRef:
    display_path: str
    filesystem_path: Path
    zip_member: str | None = None


def _artifact_display_path(path: str | Path, *, zip_member: str | None = None) -> str:
    if zip_member is None:
        archive_member_ref = _split_archive_member_path(path)
        if archive_member_ref is not None:
            archive_path, normalized_member = archive_member_ref
            return _artifact_display_path(archive_path, zip_member=normalized_member)
    resolved_path = Path(path).resolve()
    if zip_member is None:
        return str(resolved_path)
    normalized_member = zip_member.replace("\\", "/").lstrip("/")
    return f"{resolved_path}!/{normalized_member}"


def _copy_mapping(value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    return dict(value)


def _split_archive_member_path(path: str | Path) -> tuple[Path, str] | None:
    raw_path = str(path)
    marker_index = raw_path.find("!")
    if marker_index < 0:
        return None
    archive_path = raw_path[:marker_index]
    if not archive_path.lower().endswith(".zip"):
        return None
    member_path = raw_path[marker_index + 1 :].lstrip("/\\")
    resolved_archive_path = Path(archive_path).resolve()
    if not member_path:
        raise ResourceHunterError(
            f"Packaging baseline archive {resolved_archive_path} must include a member path after '!'."
        )
    return resolved_archive_path, member_path.replace("\\", "/")


def _artifact_key(display_path: str) -> str:
    archive_path, marker, member = display_path.partition("!/")
    if not marker:
        return os.path.normcase(display_path)
    return f"{os.path.normcase(archive_path)}!/{member.lower()}"


def _artifact_sort_key(artifact_ref: _ArtifactRef) -> str:
    return _artifact_key(artifact_ref.display_path)


def _zip_artifact_refs(archive_path: str | Path) -> list[_ArtifactRef]:
    resolved_archive_path = Path(archive_path).resolve()
    try:
        with zipfile.ZipFile(resolved_archive_path) as archive:
            member_names = sorted(
                member_name
                for member_name in archive.namelist()
                if not member_name.endswith("/") and Path(member_name).name == _PACKAGING_BASELINE_ARTIFACT_NAME
            )
    except (OSError, zipfile.BadZipFile) as exc:
        raise ResourceHunterError(f"Unable to read packaging baseline archive {resolved_archive_path}: {exc}") from exc

    return [
        _ArtifactRef(
            display_path=_artifact_display_path(resolved_archive_path, zip_member=member_name),
            filesystem_path=resolved_archive_path,
            zip_member=member_name,
        )
        for member_name in member_names
    ]


def _read_artifact_text(artifact_ref: _ArtifactRef) -> str:
    if artifact_ref.zip_member is None:
        try:
            return artifact_ref.filesystem_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ResourceHunterError(
                f"Unable to read packaging baseline artifact {artifact_ref.display_path}: {exc}"
            ) from exc

    try:
        with zipfile.ZipFile(artifact_ref.filesystem_path) as archive:
            with archive.open(artifact_ref.zip_member, "r") as handle:
                raw_bytes = handle.read()
    except (OSError, KeyError, RuntimeError, zipfile.BadZipFile) as exc:
        raise ResourceHunterError(
            f"Unable to read packaging baseline artifact {artifact_ref.display_path}: {exc}"
        ) from exc

    try:
        return raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ResourceHunterError(
            f"Packaging baseline artifact {artifact_ref.display_path} is not valid UTF-8: {exc}"
        ) from exc


def _load_packaging_baseline_payload_from_ref(artifact_ref: _ArtifactRef) -> dict[str, Any]:
    raw_text = _read_artifact_text(artifact_ref)
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ResourceHunterError(
            f"Packaging baseline artifact {artifact_ref.display_path} is not valid JSON: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise ResourceHunterError(f"Packaging baseline artifact {artifact_ref.display_path} must contain a JSON object.")
    _baseline_captures(payload, artifact_path=artifact_ref.display_path)
    return payload


def _coerce_artifact_ref(path: str | Path) -> _ArtifactRef:
    archive_member_ref = _split_archive_member_path(path)
    if archive_member_ref is not None:
        archive_path, zip_member = archive_member_ref
        return _ArtifactRef(
            display_path=_artifact_display_path(archive_path, zip_member=zip_member),
            filesystem_path=archive_path,
            zip_member=zip_member,
        )
    display_path = _artifact_display_path(path)
    return _ArtifactRef(display_path=display_path, filesystem_path=Path(path).resolve())


def _directory_artifact_refs(directory_path: str | Path) -> list[_ArtifactRef]:
    resolved_directory = Path(directory_path).resolve()
    matches = [
        _ArtifactRef(display_path=_artifact_display_path(path), filesystem_path=path.resolve())
        for path in resolved_directory.rglob(_PACKAGING_BASELINE_ARTIFACT_NAME)
        if path.is_file()
    ]
    archive_paths = sorted(
        path.resolve()
        for path in resolved_directory.rglob("*")
        if path.is_file() and path.suffix.lower() == ".zip"
    )
    for archive_path in archive_paths:
        matches.extend(_zip_artifact_refs(archive_path))
    return sorted(matches, key=_artifact_sort_key)


def _resolve_packaging_baseline_artifact_refs(
    raw_paths: Sequence[str | Path] | None = None, *, allow_empty: bool = False
) -> list[_ArtifactRef]:
    requested_paths = list(raw_paths or [])
    if not requested_paths:
        requested_paths = [DEFAULT_PACKAGING_BASELINE_ARTIFACT]

    artifact_refs: list[_ArtifactRef] = []
    empty_directories: list[Path] = []
    empty_archives: list[Path] = []
    seen: set[str] = set()
    for raw_path in requested_paths:
        candidate = Path(raw_path).resolve()
        if candidate.is_dir():
            matches = _directory_artifact_refs(candidate)
            if not matches:
                empty_directories.append(candidate)
                continue
            for match in matches:
                key = _artifact_key(match.display_path)
                if key in seen:
                    continue
                seen.add(key)
                artifact_refs.append(match)
            continue
        if candidate.suffix.lower() == ".zip":
            matches = _zip_artifact_refs(candidate)
            if not matches:
                empty_archives.append(candidate)
                continue
            for match in matches:
                key = _artifact_key(match.display_path)
                if key in seen:
                    continue
                seen.add(key)
                artifact_refs.append(match)
            continue
        key = _artifact_key(_artifact_display_path(candidate))
        if key in seen:
            continue
        seen.add(key)
        artifact_refs.append(_ArtifactRef(display_path=_artifact_display_path(candidate), filesystem_path=candidate))

    if allow_empty and not artifact_refs and (empty_directories or empty_archives):
        return []
    if empty_directories:
        directories = ", ".join(str(path) for path in empty_directories)
        raise ResourceHunterError(f"No packaging-baseline.json artifacts found under {directories}.")
    if empty_archives:
        archives = ", ".join(str(path) for path in empty_archives)
        raise ResourceHunterError(f"No packaging-baseline.json artifacts found in archive(s) {archives}.")
    if not artifact_refs:
        raise ResourceHunterError("No packaging baseline artifacts were requested.")
    return artifact_refs


def _baseline_captures(
    payload: Mapping[str, Any],
    *,
    artifact_path: str,
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    passing_capture = payload.get("passing_capture")
    blocked_capture = payload.get("blocked_capture")
    if not isinstance(passing_capture, Mapping) or not isinstance(blocked_capture, Mapping):
        raise ResourceHunterError(
            f"Packaging baseline artifact {artifact_path} does not contain passing_capture and blocked_capture entries."
        )
    return passing_capture, blocked_capture


def _report_capture(
    *,
    capture_name: str,
    label: str,
    capture: Mapping[str, Any],
) -> dict[str, Any]:
    expected_outcome = capture.get("expected_outcome")
    if not isinstance(expected_outcome, Mapping):
        expected_outcome = {}
    expectation_drift = capture.get("expectation_drift")
    if not isinstance(expectation_drift, list):
        expectation_drift = []
    report_capture: dict[str, Any] = {
        "name": capture_name,
        "label": label,
        "path": capture.get("path"),
        "project_root": capture.get("project_root"),
        "project_root_source": capture.get("project_root_source"),
        "expected_outcome": dict(expected_outcome),
        "actual": {
            "doctor_packaging_ready": capture.get("doctor_packaging_ready"),
            "packaging_smoke_ok": capture.get("packaging_smoke_ok"),
            "failed_step": capture.get("failed_step"),
            "strategy_family": capture.get("strategy_family"),
            "strategy": capture.get("strategy"),
            "reason": capture.get("reason"),
        },
        "matches_expectation": capture.get("matches_expectation"),
        "expectation_drift": expectation_drift,
    }
    requested_project_root = capture.get("requested_project_root")
    if requested_project_root is not None:
        report_capture["requested_project_root"] = requested_project_root
    packaging_python = capture.get("packaging_python")
    if packaging_python is not None:
        report_capture["packaging_python"] = packaging_python
    packaging_python_source = capture.get("packaging_python_source")
    if packaging_python_source is not None:
        report_capture["packaging_python_source"] = packaging_python_source
    packaging_python_auto_selected = capture.get("packaging_python_auto_selected")
    if packaging_python_auto_selected is not None:
        report_capture["packaging_python_auto_selected"] = packaging_python_auto_selected
    return report_capture


def build_packaging_baseline_report(payload: Mapping[str, Any], *, artifact_path: str | Path) -> dict[str, Any]:
    resolved_path = _artifact_display_path(artifact_path)
    if not isinstance(payload, Mapping):
        raise ResourceHunterError(f"Packaging baseline artifact {resolved_path} must contain a JSON object.")
    passing_capture, blocked_capture = _baseline_captures(payload, artifact_path=resolved_path)
    summary = payload.get("summary") if isinstance(payload.get("summary"), Mapping) else {}
    requirements = payload.get("requirements") if isinstance(payload.get("requirements"), Mapping) else {}
    warnings = payload.get("warnings")
    if not isinstance(warnings, list):
        warnings = []
    failures = requirements.get("failures")
    if not isinstance(failures, list):
        failures = []
    report_payload: dict[str, Any] = {
        "report_schema_version": PACKAGING_BASELINE_REPORT_SCHEMA_VERSION,
        "report_type": "single",
        "artifact_path": resolved_path,
        "artifact_schema_version": payload.get("schema_version"),
        "captured_at": payload.get("captured_at"),
        "output_dir": payload.get("output_dir"),
        "project_root": payload.get("project_root"),
        "project_root_source": payload.get("project_root_source"),
        "blocked_python": payload.get("blocked_python"),
        "summary": {
            "passing_capture_matches_expectation": summary.get("passing_capture_matches_expectation"),
            "blocked_capture_matches_expectation": summary.get("blocked_capture_matches_expectation"),
            "baseline_contract_ok": summary.get("baseline_contract_ok"),
        },
        "requirements": {
            "require_expected_outcomes": requirements.get("require_expected_outcomes"),
            "ok": requirements.get("ok"),
            "failures": failures,
        },
        "warnings": warnings,
        "captures": [
            _report_capture(
                capture_name="passing",
                label="Passing",
                capture=passing_capture,
            ),
            _report_capture(
                capture_name="blocked",
                label="Blocked",
                capture=blocked_capture,
            ),
        ],
    }
    requested_project_root = payload.get("requested_project_root")
    if requested_project_root is not None:
        report_payload["requested_project_root"] = requested_project_root
    return report_payload


def resolve_packaging_baseline_artifact_paths(raw_paths: Sequence[str | Path] | None = None) -> list[str | Path]:
    artifact_refs = _resolve_packaging_baseline_artifact_refs(raw_paths)
    return [
        artifact_ref.display_path if artifact_ref.zip_member is not None else artifact_ref.filesystem_path
        for artifact_ref in artifact_refs
    ]


def _resolved_download_artifact_paths(download_payload: Mapping[str, Any]) -> list[str | Path]:
    download_dir = download_payload.get("download_dir")
    if download_dir is None:
        return []
    artifact_refs = _resolve_packaging_baseline_artifact_refs([str(download_dir)], allow_empty=True)
    return [
        artifact_ref.display_path if artifact_ref.zip_member is not None else artifact_ref.filesystem_path
        for artifact_ref in artifact_refs
    ]


def _attach_download_artifact_resolution(
    download_payload: Mapping[str, Any], artifact_paths: Sequence[str | Path]
) -> dict[str, Any]:
    payload = _copy_mapping(download_payload)
    resolved_paths = [str(artifact_path) for artifact_path in artifact_paths]
    archive_member_count = sum(1 for artifact_path in resolved_paths if "!/" in artifact_path)
    payload["resolved_artifact_count"] = len(resolved_paths)
    payload["resolved_artifact_paths"] = resolved_paths
    payload["resolved_archive_member_count"] = archive_member_count
    payload["resolved_filesystem_artifact_count"] = len(resolved_paths) - archive_member_count
    return payload


def build_packaging_baseline_aggregate_report(report_payloads: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    artifact_reports = [dict(report_payload) for report_payload in report_payloads]
    contract_ok_artifact_count = 0
    contract_drift_artifacts: list[str] = []
    requirement_failed_artifacts: list[str] = []
    warnings: list[str] = []
    for report_payload in artifact_reports:
        artifact_path = str(report_payload.get("artifact_path") or "unknown")
        summary = report_payload.get("summary") if isinstance(report_payload.get("summary"), Mapping) else {}
        requirements = (
            report_payload.get("requirements") if isinstance(report_payload.get("requirements"), Mapping) else {}
        )
        artifact_warnings = report_payload.get("warnings")
        if not isinstance(artifact_warnings, list):
            artifact_warnings = []
        if summary.get("baseline_contract_ok") is True:
            contract_ok_artifact_count += 1
        else:
            contract_drift_artifacts.append(artifact_path)
        if requirements.get("ok") is False:
            requirement_failed_artifacts.append(artifact_path)
        warnings.extend(f"{artifact_path}: {warning}" for warning in artifact_warnings)

    artifact_count = len(artifact_reports)
    return {
        "report_schema_version": PACKAGING_BASELINE_REPORT_SCHEMA_VERSION,
        "report_type": "aggregate",
        "summary": {
            "artifact_count": artifact_count,
            "contract_ok_artifact_count": contract_ok_artifact_count,
            "contract_drift_artifact_count": artifact_count - contract_ok_artifact_count,
            "requirement_failed_artifact_count": len(requirement_failed_artifacts),
            "warning_count": len(warnings),
            "all_baseline_contracts_ok": contract_ok_artifact_count == artifact_count,
        },
        "artifacts_with_contract_drift": contract_drift_artifacts,
        "artifacts_with_requirement_failures": requirement_failed_artifacts,
        "warnings": warnings,
        "artifacts": artifact_reports,
    }


def load_packaging_baseline_payload(path: str | Path) -> dict[str, Any]:
    artifact_ref = _coerce_artifact_ref(path)
    if artifact_ref.zip_member is not None:
        return _load_packaging_baseline_payload_from_ref(artifact_ref)

    artifact_path = artifact_ref.filesystem_path
    if artifact_path.suffix.lower() == ".zip":
        artifact_refs = _zip_artifact_refs(artifact_path)
        if not artifact_refs:
            raise ResourceHunterError(f"No packaging-baseline.json artifacts found in archive(s) {artifact_path}.")
        if len(artifact_refs) != 1:
            raise ResourceHunterError(
                f"Packaging baseline archive {artifact_path} contains {len(artifact_refs)} packaging-baseline.json artifacts; "
                "use read_packaging_baseline_reports() when multiple archived artifacts must be aggregated."
            )
        return _load_packaging_baseline_payload_from_ref(artifact_refs[0])
    return _load_packaging_baseline_payload_from_ref(artifact_ref)


def read_packaging_baseline_report(path: str | Path) -> dict[str, Any]:
    artifact_ref = _coerce_artifact_ref(path)
    if artifact_ref.zip_member is not None:
        payload = _load_packaging_baseline_payload_from_ref(artifact_ref)
        return build_packaging_baseline_report(payload, artifact_path=artifact_ref.display_path)

    artifact_path = artifact_ref.filesystem_path
    if artifact_path.suffix.lower() == ".zip":
        artifact_refs = _zip_artifact_refs(artifact_path)
        if not artifact_refs:
            raise ResourceHunterError(f"No packaging-baseline.json artifacts found in archive(s) {artifact_path}.")
        if len(artifact_refs) != 1:
            raise ResourceHunterError(
                f"Packaging baseline archive {artifact_path} contains {len(artifact_refs)} packaging-baseline.json artifacts; "
                "use read_packaging_baseline_reports() when multiple archived artifacts must be aggregated."
            )
        payload = _load_packaging_baseline_payload_from_ref(artifact_refs[0])
        return build_packaging_baseline_report(payload, artifact_path=artifact_refs[0].display_path)
    payload = _load_packaging_baseline_payload_from_ref(artifact_ref)
    return build_packaging_baseline_report(payload, artifact_path=artifact_ref.display_path)


def read_packaging_baseline_reports(paths: Sequence[str | Path] | None = None) -> dict[str, Any]:
    artifact_refs = _resolve_packaging_baseline_artifact_refs(paths)
    report_payloads = [
        build_packaging_baseline_report(
            _load_packaging_baseline_payload_from_ref(artifact_ref),
            artifact_path=artifact_ref.display_path,
        )
        for artifact_ref in artifact_refs
    ]
    if len(report_payloads) == 1:
        return report_payloads[0]
    return build_packaging_baseline_aggregate_report(report_payloads)


def attach_packaging_baseline_download_payload(
    report_payload: Mapping[str, Any], *, download_payload: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    payload = dict(report_payload)
    if download_payload is not None:
        payload["download"] = _copy_mapping(download_payload)
    return payload


def build_packaging_baseline_report_error_payload(
    error: str, *, download_payload: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "report_schema_version": PACKAGING_BASELINE_REPORT_SCHEMA_VERSION,
        "report_type": "error",
        "summary": {},
        "warnings": [],
        "error": error,
    }
    if download_payload is not None:
        payload["download"] = _copy_mapping(download_payload)
    return payload


def _evaluate_downloaded_packaging_baseline_reports(download_payload: Mapping[str, Any]) -> dict[str, Any]:
    artifact_paths = _resolved_download_artifact_paths(download_payload)
    download_payload = _attach_download_artifact_resolution(download_payload, artifact_paths)
    if not artifact_paths:
        raise PackagingBaselineReportError(
            f"No packaging-baseline.json artifacts found under {download_payload['download_dir']}.",
            download_payload=download_payload,
        )
    try:
        report_payload = read_packaging_baseline_reports(artifact_paths)
    except ResourceHunterError as exc:
        raise PackagingBaselineReportError(str(exc), download_payload=download_payload) from exc
    return attach_packaging_baseline_download_payload(report_payload, download_payload=download_payload)


def read_packaging_baseline_reports_from_github_run(
    run_id: str,
    *,
    repo: str | None = None,
    artifact_names: Sequence[str] | None = None,
    artifact_patterns: Sequence[str] | None = None,
    download_dir: str | Path | None = None,
    keep_download_dir: bool = False,
) -> dict[str, Any]:
    from . import packaging_gate

    if download_dir is not None:
        try:
            download_payload = packaging_gate._download_packaging_baseline_github_run(
                run_id,
                repo=repo,
                artifact_names=artifact_names,
                artifact_patterns=artifact_patterns,
                download_dir=download_dir,
                download_dir_source="argument",
                download_dir_retained=True,
            )
        except ResourceHunterError as exc:
            raise PackagingBaselineReportError(
                str(exc),
                download_payload=getattr(exc, "download_payload", None),
            ) from exc
        return _evaluate_downloaded_packaging_baseline_reports(download_payload)

    if keep_download_dir:
        retained_dir = Path(tempfile.mkdtemp(prefix="resource-hunter-gh-run-download-"))
        try:
            download_payload = packaging_gate._download_packaging_baseline_github_run(
                run_id,
                repo=repo,
                artifact_names=artifact_names,
                artifact_patterns=artifact_patterns,
                download_dir=retained_dir,
                download_dir_source="temporary",
                download_dir_retained=True,
            )
        except ResourceHunterError as exc:
            raise PackagingBaselineReportError(
                str(exc),
                download_payload=getattr(exc, "download_payload", None),
            ) from exc
        return _evaluate_downloaded_packaging_baseline_reports(download_payload)

    with tempfile.TemporaryDirectory(prefix="resource-hunter-gh-run-download-") as temp_dir:
        try:
            download_payload = packaging_gate._download_packaging_baseline_github_run(
                run_id,
                repo=repo,
                artifact_names=artifact_names,
                artifact_patterns=artifact_patterns,
                download_dir=temp_dir,
                download_dir_source="temporary",
                download_dir_retained=False,
            )
        except ResourceHunterError as exc:
            raise PackagingBaselineReportError(
                str(exc),
                download_payload=getattr(exc, "download_payload", None),
            ) from exc
        return _evaluate_downloaded_packaging_baseline_reports(download_payload)


def packaging_baseline_report_requirement_failures(report_payload: Mapping[str, Any]) -> list[str]:
    report_type = report_payload.get("report_type")
    if report_type == "aggregate":
        artifacts = report_payload.get("artifacts")
        if not isinstance(artifacts, list):
            return ["Packaging baseline aggregate report did not contain artifacts."]
        failures: list[str] = []
        for artifact in artifacts:
            if not isinstance(artifact, Mapping):
                continue
            failures.extend(packaging_baseline_report_requirement_failures(artifact))
        return failures

    requirements = report_payload.get("requirements") if isinstance(report_payload.get("requirements"), Mapping) else {}
    requirement_failures = requirements.get("failures")
    if not isinstance(requirement_failures, list):
        requirement_failures = []
    artifact_path = report_payload.get("artifact_path") or "unknown artifact"
    if requirement_failures:
        return [f"{artifact_path}: {failure}" for failure in requirement_failures]

    summary = report_payload.get("summary") if isinstance(report_payload.get("summary"), Mapping) else {}
    if summary.get("baseline_contract_ok") is True:
        return []
    return [f"{artifact_path}: Packaging baseline contract drift detected."]


def main(argv: Sequence[str] | None = None) -> int:
    from .cli import main as cli_main

    forwarded_argv = list(argv) if argv is not None else list(sys.argv[1:])
    return cli_main(["packaging-baseline-report", *forwarded_argv])


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "DEFAULT_PACKAGING_BASELINE_ARTIFACT",
    "PACKAGING_BASELINE_REPORT_SCHEMA_VERSION",
    "PackagingBaselineReportError",
    "attach_packaging_baseline_download_payload",
    "build_packaging_baseline_report_error_payload",
    "build_packaging_baseline_aggregate_report",
    "build_packaging_baseline_report",
    "load_packaging_baseline_payload",
    "main",
    "packaging_baseline_report_requirement_failures",
    "read_packaging_baseline_report",
    "read_packaging_baseline_reports",
    "read_packaging_baseline_reports_from_github_run",
    "resolve_packaging_baseline_artifact_paths",
]
