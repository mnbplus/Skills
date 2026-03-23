from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .common import dump_json, ensure_utf8_stdio
from .errors import ResourceHunterError
from .packaging_report import (
    _attach_download_artifact_resolution,
    _resolved_download_artifact_paths,
    packaging_baseline_report_requirement_failures,
    read_packaging_baseline_reports,
)


PACKAGING_BASELINE_GATE_SCHEMA_VERSION = 1
DEFAULT_GITHUB_ARTIFACT_PATTERN = "resource-hunter-packaging-baseline-*"
DEFAULT_GITHUB_RUN_WORKFLOW = "resource-hunter-ci"
_GITHUB_RUN_DOWNLOAD_TIMEOUT_SECONDS = 300
_GITHUB_RUN_LIST_LIMIT = 20


class PackagingBaselineGateError(ResourceHunterError):
    def __init__(self, message: str, *, download_payload: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        self.download_payload = _copy_mapping(download_payload)


def _copy_mapping(value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    return dict(value)


def _copy_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _report_artifact_count(report_payload: Mapping[str, Any]) -> int:
    if report_payload.get("report_type") != "aggregate":
        return 1
    summary = report_payload.get("summary") if isinstance(report_payload.get("summary"), Mapping) else {}
    artifact_count = summary.get("artifact_count")
    if isinstance(artifact_count, int):
        return artifact_count
    artifacts = report_payload.get("artifacts")
    if isinstance(artifacts, list):
        return len(artifacts)
    return 0


def _artifact_count_failure(required_artifact_count: int, actual_artifact_count: int) -> str:
    return (
        "Packaging baseline gate expected "
        f"{required_artifact_count} artifact(s) but found {actual_artifact_count}."
    )


def _copy_string_sequence(values: Sequence[str] | None) -> list[str]:
    if values is None:
        return []
    return [str(value) for value in values if str(value).strip()]


def _normalize_repo_value(repo: str | None) -> str | None:
    if repo is None:
        return None
    normalized = str(repo).strip().strip("/")
    return normalized or None


def _repo_from_github_remote_url(remote_url: str | None) -> str | None:
    normalized = str(remote_url or "").strip()
    if not normalized:
        return None
    match = re.match(
        r"^(?:git@github\.com:|ssh://git@github\.com/|https?://github\.com/|git://github\.com/)(?P<repo>[^\s]+?)(?:\.git)?/?$",
        normalized,
    )
    if match is None:
        return None
    repo = match.group("repo").strip("/")
    if repo.count("/") != 1:
        return None
    owner, name = repo.split("/", 1)
    if not owner or not name:
        return None
    return f"{owner}/{name}"


def _repo_from_git_remote(*, cwd: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=str(cwd),
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return _repo_from_github_remote_url(result.stdout)


def _resolve_github_repo_context(repo: str | None, *, cwd: Path) -> tuple[str | None, str | None]:
    explicit_repo = _normalize_repo_value(repo)
    if explicit_repo is not None:
        return explicit_repo, None
    environment_repo = _normalize_repo_value(os.environ.get("GITHUB_REPOSITORY"))
    if environment_repo is not None:
        return environment_repo, "environment"
    git_remote_repo = _repo_from_git_remote(cwd=cwd)
    if git_remote_repo is not None:
        return git_remote_repo, "git-origin"
    return None, "gh-context"


def _build_github_run_download_payload(
    run_id: str,
    *,
    requested_run_id: str | None = None,
    repo: str | None,
    repo_source: str | None,
    artifact_names: Sequence[str] | None,
    artifact_patterns: Sequence[str] | None,
    download_dir: str | Path,
    download_dir_source: str,
    download_dir_retained: bool,
    run_lookup: Mapping[str, Any] | None = None,
    download_command: Sequence[str] | None = None,
    download_returncode: int | None = None,
    download_stdout: str | None = None,
    download_stderr: str | None = None,
) -> dict[str, Any]:
    names, patterns, filter_source = _resolve_download_filters(
        artifact_names=artifact_names,
        artifact_patterns=artifact_patterns,
    )
    payload: dict[str, Any] = {
        "provider": "github-actions",
        "run_id": str(run_id),
        "repo": repo,
        "download_dir": str(Path(download_dir).resolve()),
        "download_dir_source": download_dir_source,
        "download_dir_retained": download_dir_retained,
        "artifact_names": names,
        "artifact_patterns": patterns,
        "artifact_filter_source": filter_source,
    }
    if requested_run_id is not None:
        payload["requested_run_id"] = str(requested_run_id)
    if repo_source is not None:
        payload["repo_source"] = repo_source
    if isinstance(run_lookup, Mapping) and run_lookup:
        payload["run_lookup"] = dict(run_lookup)
    if download_command is not None:
        payload["download_command"] = [str(part) for part in download_command]
    if download_returncode is not None:
        payload["download_returncode"] = int(download_returncode)
    if download_stdout:
        payload["download_stdout"] = str(download_stdout)
    if download_stderr:
        payload["download_stderr"] = str(download_stderr)
    return payload


def _run_command(
    args: Sequence[str],
    *,
    cwd: Path,
    timeout: int = _GITHUB_RUN_DOWNLOAD_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    result = subprocess.run(
        list(args),
        cwd=str(cwd),
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return {
        "command": list(args),
        "cwd": str(cwd),
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def _resolve_download_filters(
    *,
    artifact_names: Sequence[str] | None = None,
    artifact_patterns: Sequence[str] | None = None,
) -> tuple[list[str], list[str], str]:
    names = _copy_string_sequence(artifact_names)
    patterns = _copy_string_sequence(artifact_patterns)
    if names or patterns:
        return names, patterns, "argument"
    return [], [DEFAULT_GITHUB_ARTIFACT_PATTERN], "default"


def _is_latest_github_run_selector(run_id: str) -> bool:
    return str(run_id).strip().lower() == "latest"


def _selected_github_run_summary(run: Mapping[str, Any]) -> dict[str, Any]:
    summary = {"id": str(run.get("databaseId") or "")}
    for source_key, target_key in (
        ("status", "status"),
        ("conclusion", "conclusion"),
        ("workflowName", "workflow_name"),
        ("headBranch", "head_branch"),
        ("event", "event"),
        ("url", "url"),
        ("displayTitle", "display_title"),
    ):
        value = run.get(source_key)
        if value is not None and str(value):
            summary[target_key] = str(value)
    return summary


def _select_latest_completed_github_run(runs: object) -> tuple[dict[str, Any] | None, int]:
    if not isinstance(runs, list):
        return None, 0
    normalized_runs = [dict(run) for run in runs if isinstance(run, Mapping)]
    for run in normalized_runs:
        if str(run.get("status") or "").lower() == "completed" and run.get("databaseId") is not None:
            return run, len(normalized_runs)
    return None, len(normalized_runs)


def _download_packaging_baseline_github_run(
    run_id: str,
    *,
    repo: str | None = None,
    artifact_names: Sequence[str] | None = None,
    artifact_patterns: Sequence[str] | None = None,
    download_dir: str | Path,
    download_dir_source: str,
    download_dir_retained: bool,
) -> dict[str, Any]:
    requested_run_id = str(run_id)
    gh_binary = shutil.which("gh")
    resolved_repo, repo_source = _resolve_github_repo_context(repo, cwd=Path.cwd())
    download_payload = _build_github_run_download_payload(
        requested_run_id,
        repo=resolved_repo,
        repo_source=repo_source,
        artifact_names=artifact_names,
        artifact_patterns=artifact_patterns,
        download_dir=download_dir,
        download_dir_source=download_dir_source,
        download_dir_retained=download_dir_retained,
    )
    if gh_binary is None:
        raise PackagingBaselineGateError(
            "GitHub CLI (gh) is required for --github-run. Install gh or provide downloaded artifact paths instead.",
            download_payload=download_payload,
        )
    resolved_run_id = requested_run_id
    run_lookup: dict[str, Any] | None = None
    if _is_latest_github_run_selector(requested_run_id):
        list_command: list[str] = [
            gh_binary,
            "run",
            "list",
            "--workflow",
            DEFAULT_GITHUB_RUN_WORKFLOW,
            "--limit",
            str(_GITHUB_RUN_LIST_LIMIT),
            "--json",
            "databaseId,status,conclusion,workflowName,headBranch,event,url,displayTitle",
        ]
        if resolved_repo:
            list_command.extend(["--repo", resolved_repo])
        list_result = _run_command(list_command, cwd=Path.cwd())
        run_lookup = {
            "selector": requested_run_id,
            "workflow": DEFAULT_GITHUB_RUN_WORKFLOW,
            "command": [str(part) for part in list_result.get("command", [])],
        }
        if list_result["returncode"] != 0:
            run_lookup["returncode"] = int(list_result["returncode"])
            if list_result.get("stderr"):
                run_lookup["stderr"] = str(list_result["stderr"])
            if list_result.get("stdout"):
                run_lookup["stdout"] = str(list_result["stdout"])
            detail = (
                list_result.get("stderr")
                or list_result.get("stdout")
                or f"exit code {list_result['returncode']}"
            ).strip()
            target = resolved_repo or "current gh context"
            raise PackagingBaselineGateError(
                (
                    "GitHub Actions run lookup failed for "
                    f"{target} latest {DEFAULT_GITHUB_RUN_WORKFLOW} run: {detail}"
                ),
                download_payload=_build_github_run_download_payload(
                    requested_run_id,
                    requested_run_id=requested_run_id,
                    repo=resolved_repo,
                    repo_source=repo_source,
                    artifact_names=artifact_names,
                    artifact_patterns=artifact_patterns,
                    download_dir=download_dir,
                    download_dir_source=download_dir_source,
                    download_dir_retained=download_dir_retained,
                    run_lookup=run_lookup,
                ),
            )
        try:
            run_candidates = json.loads(list_result.get("stdout") or "[]")
        except json.JSONDecodeError as exc:
            run_lookup["stdout"] = str(list_result.get("stdout") or "")
            raise PackagingBaselineGateError(
                (
                    "GitHub Actions run lookup returned invalid JSON for "
                    f"latest {DEFAULT_GITHUB_RUN_WORKFLOW} run: {exc}"
                ),
                download_payload=_build_github_run_download_payload(
                    requested_run_id,
                    requested_run_id=requested_run_id,
                    repo=resolved_repo,
                    repo_source=repo_source,
                    artifact_names=artifact_names,
                    artifact_patterns=artifact_patterns,
                    download_dir=download_dir,
                    download_dir_source=download_dir_source,
                    download_dir_retained=download_dir_retained,
                    run_lookup=run_lookup,
                ),
            ) from exc
        selected_run, matched_run_count = _select_latest_completed_github_run(run_candidates)
        run_lookup["matched_run_count"] = matched_run_count
        if selected_run is None:
            raise PackagingBaselineGateError(
                (
                    "No completed GitHub Actions runs matched "
                    f"latest {DEFAULT_GITHUB_RUN_WORKFLOW} for {resolved_repo or 'the current gh context'}."
                ),
                download_payload=_build_github_run_download_payload(
                    requested_run_id,
                    requested_run_id=requested_run_id,
                    repo=resolved_repo,
                    repo_source=repo_source,
                    artifact_names=artifact_names,
                    artifact_patterns=artifact_patterns,
                    download_dir=download_dir,
                    download_dir_source=download_dir_source,
                    download_dir_retained=download_dir_retained,
                    run_lookup=run_lookup,
                ),
            )
        run_lookup["selected_run"] = _selected_github_run_summary(selected_run)
        resolved_run_id = str(selected_run["databaseId"])
    resolved_download_dir = Path(download_dir).resolve()
    resolved_download_dir.mkdir(parents=True, exist_ok=True)
    command: list[str] = [gh_binary, "run", "download", str(resolved_run_id)]
    if resolved_repo:
        command.extend(["--repo", resolved_repo])
    command.extend(["--dir", str(resolved_download_dir)])
    for name in download_payload["artifact_names"]:
        command.extend(["--name", name])
    for pattern in download_payload["artifact_patterns"]:
        command.extend(["--pattern", pattern])
    result = _run_command(command, cwd=Path.cwd())
    if result["returncode"] != 0:
        detail = (result.get("stderr") or result.get("stdout") or f"exit code {result['returncode']}").strip()
        target = f"{resolved_repo} run {resolved_run_id}" if resolved_repo else f"run {resolved_run_id}"
        raise PackagingBaselineGateError(
            f"GitHub Actions artifact download failed for {target}: {detail}",
            download_payload=_build_github_run_download_payload(
                resolved_run_id,
                requested_run_id=requested_run_id if requested_run_id != resolved_run_id else None,
                repo=resolved_repo,
                repo_source=repo_source,
                artifact_names=artifact_names,
                artifact_patterns=artifact_patterns,
                download_dir=resolved_download_dir,
                download_dir_source=download_dir_source,
                download_dir_retained=download_dir_retained,
                run_lookup=run_lookup,
                download_command=result.get("command"),
                download_returncode=result.get("returncode"),
                download_stdout=result.get("stdout"),
                download_stderr=result.get("stderr"),
            ),
        )
    return _build_github_run_download_payload(
        resolved_run_id,
        requested_run_id=requested_run_id if requested_run_id != resolved_run_id else None,
        repo=resolved_repo,
        repo_source=repo_source,
        artifact_names=artifact_names,
        artifact_patterns=artifact_patterns,
        download_dir=resolved_download_dir,
        download_dir_source=download_dir_source,
        download_dir_retained=download_dir_retained,
        run_lookup=run_lookup,
        download_command=result["command"],
    )


def build_packaging_baseline_gate_payload(
    report_payload: Mapping[str, Any],
    *,
    required_artifact_count: int | None = None,
    download_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    failures = list(packaging_baseline_report_requirement_failures(report_payload))
    payload: dict[str, Any] = {
        "gate_schema_version": PACKAGING_BASELINE_GATE_SCHEMA_VERSION,
        "report_type": report_payload.get("report_type"),
        "summary": _copy_mapping(report_payload.get("summary")),
    }
    if download_payload is not None:
        payload["download"] = _copy_mapping(download_payload)
    if report_payload.get("report_type") == "aggregate":
        payload["artifacts_with_contract_drift"] = _copy_string_list(
            report_payload.get("artifacts_with_contract_drift")
        )
        payload["artifacts_with_requirement_failures"] = _copy_string_list(
            report_payload.get("artifacts_with_requirement_failures")
        )
    else:
        artifact_path = report_payload.get("artifact_path")
        if artifact_path is not None:
            payload["artifact_path"] = str(artifact_path)
    if required_artifact_count is not None:
        actual_artifact_count = _report_artifact_count(report_payload)
        payload["expected_artifact_count"] = required_artifact_count
        payload["actual_artifact_count"] = actual_artifact_count
        if actual_artifact_count != required_artifact_count:
            failures.append(_artifact_count_failure(required_artifact_count, actual_artifact_count))
    payload["ok"] = len(failures) == 0
    payload["failure_count"] = len(failures)
    payload["failures"] = failures
    return payload


def build_packaging_baseline_gate_error_payload(
    error: str,
    *,
    required_artifact_count: int | None = None,
    download_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "gate_schema_version": PACKAGING_BASELINE_GATE_SCHEMA_VERSION,
        "report_type": "error",
        "summary": {},
        "ok": False,
        "failure_count": 1,
        "failures": [error],
        "error": error,
    }
    if required_artifact_count is not None:
        payload["expected_artifact_count"] = required_artifact_count
    if download_payload is not None:
        payload["download"] = _copy_mapping(download_payload)
    return payload


def evaluate_packaging_baseline_gate(
    paths: Sequence[str | Path] | None = None, *, required_artifact_count: int | None = None
) -> dict[str, Any]:
    report_payload = read_packaging_baseline_reports(paths)
    return build_packaging_baseline_gate_payload(
        report_payload,
        required_artifact_count=required_artifact_count,
    )


def _evaluate_downloaded_packaging_baseline_gate(
    download_payload: Mapping[str, Any],
    *,
    required_artifact_count: int | None = None,
) -> dict[str, Any]:
    artifact_paths = _resolved_download_artifact_paths(download_payload)
    download_payload = _attach_download_artifact_resolution(download_payload, artifact_paths)
    if not artifact_paths:
        raise PackagingBaselineGateError(
            f"No packaging-baseline.json artifacts found under {download_payload['download_dir']}.",
            download_payload=download_payload,
        )
    try:
        report_payload = read_packaging_baseline_reports(artifact_paths)
    except ResourceHunterError as exc:
        raise PackagingBaselineGateError(str(exc), download_payload=download_payload) from exc
    return build_packaging_baseline_gate_payload(
        report_payload,
        required_artifact_count=required_artifact_count,
        download_payload=download_payload,
    )


def evaluate_packaging_baseline_gate_from_github_run(
    run_id: str,
    *,
    repo: str | None = None,
    artifact_names: Sequence[str] | None = None,
    artifact_patterns: Sequence[str] | None = None,
    download_dir: str | Path | None = None,
    keep_download_dir: bool = False,
    required_artifact_count: int | None = None,
) -> dict[str, Any]:
    if download_dir is not None:
        download_payload = _download_packaging_baseline_github_run(
            run_id,
            repo=repo,
            artifact_names=artifact_names,
            artifact_patterns=artifact_patterns,
            download_dir=download_dir,
            download_dir_source="argument",
            download_dir_retained=True,
        )
        return _evaluate_downloaded_packaging_baseline_gate(
            download_payload,
            required_artifact_count=required_artifact_count,
        )

    if keep_download_dir:
        retained_dir = Path(tempfile.mkdtemp(prefix="resource-hunter-gh-run-download-"))
        download_payload = _download_packaging_baseline_github_run(
            run_id,
            repo=repo,
            artifact_names=artifact_names,
            artifact_patterns=artifact_patterns,
            download_dir=retained_dir,
            download_dir_source="temporary",
            download_dir_retained=True,
        )
        return _evaluate_downloaded_packaging_baseline_gate(
            download_payload,
            required_artifact_count=required_artifact_count,
        )

    with tempfile.TemporaryDirectory(prefix="resource-hunter-gh-run-download-") as temp_dir:
        download_payload = _download_packaging_baseline_github_run(
            run_id,
            repo=repo,
            artifact_names=artifact_names,
            artifact_patterns=artifact_patterns,
            download_dir=temp_dir,
            download_dir_source="temporary",
            download_dir_retained=False,
        )
        return _evaluate_downloaded_packaging_baseline_gate(
            download_payload,
            required_artifact_count=required_artifact_count,
        )


def format_packaging_baseline_gate_text(payload: Mapping[str, Any]) -> str:
    lines = [
        "Resource Hunter packaging baseline gate",
        f"Status: {'ok' if payload.get('ok') else 'drift'}",
        f"Report type: {payload.get('report_type') or 'unknown'}",
    ]
    download = payload.get("download") if isinstance(payload.get("download"), Mapping) else {}
    if download.get("provider") == "github-actions":
        run_label = str(download.get("run_id") or "unknown")
        requested_run_id = download.get("requested_run_id")
        if requested_run_id is not None and str(requested_run_id) and str(requested_run_id) != run_label:
            run_label = f"{run_label} (requested {requested_run_id})"
        lines.append(f"GitHub run: {run_label}")
        if download.get("repo") is not None:
            repo_label = str(download.get("repo"))
            if download.get("repo_source"):
                repo_label = f"{repo_label} ({download.get('repo_source')})"
            lines.append(f"Repository: {repo_label}")
        elif download.get("repo_source") == "gh-context":
            lines.append("Repository: current gh context")
        lines.append(f"Downloaded artifacts: {download.get('download_dir')}")
        artifact_names = download.get("artifact_names")
        artifact_patterns = download.get("artifact_patterns")
        if isinstance(artifact_names, list) and artifact_names:
            lines.append(f"Artifact names: {', '.join(str(name) for name in artifact_names)}")
        if isinstance(artifact_patterns, list) and artifact_patterns:
            lines.append(f"Artifact patterns: {', '.join(str(pattern) for pattern in artifact_patterns)}")
    summary = payload.get("summary") if isinstance(payload.get("summary"), Mapping) else {}
    if payload.get("report_type") == "aggregate":
        lines.extend(
            [
                f"Artifacts: {summary.get('artifact_count')}",
                f"Contract drift artifacts: {summary.get('contract_drift_artifact_count')}",
                f"Requirement failure artifacts: {summary.get('requirement_failed_artifact_count')}",
            ]
        )
    else:
        artifact_path = payload.get("artifact_path")
        if artifact_path is not None:
            lines.append(f"Artifact: {artifact_path}")
        lines.append(f"Baseline contract ok: {summary.get('baseline_contract_ok')}")
    if payload.get("expected_artifact_count") is not None:
        lines.append(f"Expected artifacts: {payload.get('expected_artifact_count')}")
        lines.append(f"Discovered artifacts: {payload.get('actual_artifact_count')}")
    lines.append(f"Failure count: {payload.get('failure_count')}")
    failures = payload.get("failures")
    if isinstance(failures, list) and failures:
        lines.append("Failures:")
        lines.extend(f"- {failure}" for failure in failures)
    return "\n".join(lines)


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid positive integer value: {value!r}") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError("value must be >= 1")
    return parsed


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="resource-hunter-packaging-baseline-gate",
        description=(
            "Evaluate archived packaging-baseline.json artifacts through the shared Python API and "
            "exit with code 2 when contract drift is detected."
        ),
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help=(
            "artifact file(s), .zip archive(s), or directories to scan recursively for packaging-baseline.json and nested .zip archives; "
            "defaults to artifacts/packaging-baseline/packaging-baseline.json"
        ),
    )
    parser.add_argument("--json", action="store_true", help="emit a compact gate summary as JSON")
    parser.add_argument(
        "--require-artifact-count",
        type=_positive_int,
        help=(
            "require exactly N discovered packaging-baseline artifacts before evaluating drift; "
            "useful when gating downloaded CI matrix artifacts"
        ),
    )
    parser.add_argument(
        "--github-run",
        help=(
            "download packaging-baseline artifacts from a GitHub Actions run with `gh run download` before gating; "
            "defaults to the resource-hunter-packaging-baseline-* artifact pattern"
        ),
    )
    parser.add_argument(
        "--repo",
        help=(
            "repository passed through to `gh run download --repo`; defaults to GITHUB_REPOSITORY, "
            "then the git origin remote, then the current gh repository context"
        ),
    )
    parser.add_argument(
        "--artifact-name",
        action="append",
        dest="artifact_names",
        help="artifact name to download from --github-run; may be passed multiple times",
    )
    parser.add_argument(
        "--artifact-pattern",
        action="append",
        dest="artifact_patterns",
        help="artifact glob pattern to download from --github-run; may be passed multiple times",
    )
    parser.add_argument(
        "--download-dir",
        help="directory passed to `gh run download --dir`; defaults to a temporary directory when --github-run is used",
    )
    parser.add_argument(
        "--keep-download-dir",
        action="store_true",
        help="retain the temporary download directory created for --github-run evaluation",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    ensure_utf8_stdio()
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.github_run and args.paths:
        parser.error("paths cannot be combined with --github-run")
    if not args.github_run and (
        args.repo or args.artifact_names or args.artifact_patterns or args.download_dir or args.keep_download_dir
    ):
        parser.error(
            "--repo, --artifact-name, --artifact-pattern, --download-dir, and --keep-download-dir require --github-run"
        )
    try:
        if args.github_run:
            payload = evaluate_packaging_baseline_gate_from_github_run(
                args.github_run,
                repo=args.repo,
                artifact_names=args.artifact_names,
                artifact_patterns=args.artifact_patterns,
                download_dir=args.download_dir,
                keep_download_dir=args.keep_download_dir,
                required_artifact_count=args.require_artifact_count,
            )
        else:
            payload = evaluate_packaging_baseline_gate(
                args.paths,
                required_artifact_count=args.require_artifact_count,
            )
    except ResourceHunterError as exc:
        if args.json:
            download_payload = getattr(exc, "download_payload", None)
            print(
                dump_json(
                    build_packaging_baseline_gate_error_payload(
                        str(exc),
                        required_artifact_count=args.require_artifact_count,
                        download_payload=download_payload,
                    )
                )
            )
        print(str(exc), file=sys.stderr)
        return 1
    if args.json:
        print(dump_json(payload))
    else:
        print(format_packaging_baseline_gate_text(payload))
    failures = payload.get("failures")
    if isinstance(failures, list) and failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "DEFAULT_GITHUB_ARTIFACT_PATTERN",
    "PACKAGING_BASELINE_GATE_SCHEMA_VERSION",
    "PackagingBaselineGateError",
    "build_packaging_baseline_gate_error_payload",
    "build_packaging_baseline_gate_payload",
    "evaluate_packaging_baseline_gate",
    "evaluate_packaging_baseline_gate_from_github_run",
    "format_packaging_baseline_gate_text",
    "main",
]
