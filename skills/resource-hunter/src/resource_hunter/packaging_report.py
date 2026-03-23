from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .errors import ResourceHunterError


PACKAGING_BASELINE_REPORT_SCHEMA_VERSION = 1


def _baseline_captures(
    payload: Mapping[str, Any],
    *,
    artifact_path: Path,
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
    resolved_path = Path(artifact_path).resolve()
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
        "artifact_path": str(resolved_path),
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


def load_packaging_baseline_payload(path: str | Path) -> dict[str, Any]:
    artifact_path = Path(path).resolve()
    try:
        raw_text = artifact_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ResourceHunterError(f"Unable to read packaging baseline artifact {artifact_path}: {exc}") from exc
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ResourceHunterError(f"Packaging baseline artifact {artifact_path} is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ResourceHunterError(f"Packaging baseline artifact {artifact_path} must contain a JSON object.")
    _baseline_captures(payload, artifact_path=artifact_path)
    return payload


def read_packaging_baseline_report(path: str | Path) -> dict[str, Any]:
    artifact_path = Path(path).resolve()
    payload = load_packaging_baseline_payload(artifact_path)
    return build_packaging_baseline_report(payload, artifact_path=artifact_path)


__all__ = [
    "PACKAGING_BASELINE_REPORT_SCHEMA_VERSION",
    "build_packaging_baseline_report",
    "load_packaging_baseline_payload",
    "read_packaging_baseline_report",
]
