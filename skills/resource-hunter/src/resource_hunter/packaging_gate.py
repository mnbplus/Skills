from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .common import dump_json, ensure_utf8_stdio
from .errors import ResourceHunterError
from .packaging_report import (
    packaging_baseline_report_requirement_failures,
    read_packaging_baseline_reports,
)


PACKAGING_BASELINE_GATE_SCHEMA_VERSION = 1


def _copy_mapping(value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    return dict(value)


def _copy_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def build_packaging_baseline_gate_payload(report_payload: Mapping[str, Any]) -> dict[str, Any]:
    failures = packaging_baseline_report_requirement_failures(report_payload)
    payload: dict[str, Any] = {
        "gate_schema_version": PACKAGING_BASELINE_GATE_SCHEMA_VERSION,
        "ok": len(failures) == 0,
        "failure_count": len(failures),
        "failures": failures,
        "report_type": report_payload.get("report_type"),
        "summary": _copy_mapping(report_payload.get("summary")),
    }
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
    return payload


def evaluate_packaging_baseline_gate(paths: Sequence[str | Path] | None = None) -> dict[str, Any]:
    report_payload = read_packaging_baseline_reports(paths)
    return build_packaging_baseline_gate_payload(report_payload)


def format_packaging_baseline_gate_text(payload: Mapping[str, Any]) -> str:
    lines = [
        "Resource Hunter packaging baseline gate",
        f"Status: {'ok' if payload.get('ok') else 'drift'}",
        f"Report type: {payload.get('report_type') or 'unknown'}",
    ]
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
    lines.append(f"Failure count: {payload.get('failure_count')}")
    failures = payload.get("failures")
    if isinstance(failures, list) and failures:
        lines.append("Failures:")
        lines.extend(f"- {failure}" for failure in failures)
    return "\n".join(lines)


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
            "artifact file(s), .zip archive(s), or directories to scan recursively for packaging-baseline.json; "
            "defaults to artifacts/packaging-baseline/packaging-baseline.json"
        ),
    )
    parser.add_argument("--json", action="store_true", help="emit a compact gate summary as JSON")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    ensure_utf8_stdio()
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        payload = evaluate_packaging_baseline_gate(args.paths)
    except ResourceHunterError as exc:
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
    "PACKAGING_BASELINE_GATE_SCHEMA_VERSION",
    "build_packaging_baseline_gate_payload",
    "evaluate_packaging_baseline_gate",
    "format_packaging_baseline_gate_text",
    "main",
]
