from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

import resource_hunter.packaging_gate as packaging_gate


def _write_packaging_baseline_artifact(
    root: Path,
    artifact_name: str,
    *,
    baseline_contract_ok: bool,
) -> Path:
    artifact_dir = root / artifact_name
    artifact_dir.mkdir(parents=True)
    artifact_path = artifact_dir / "packaging-baseline.json"
    blocked_warning = "Blocked capture did not report failed_step."
    blocked_capture = {
        "path": str(artifact_dir / "blocked-packaging-capture.json"),
        "project_root": str(root),
        "project_root_source": "argument",
        "requested_project_root": str(root),
        "packaging_python": str(root / "__blocked_python__" / "missing-python"),
        "packaging_python_source": "argument",
        "doctor_packaging_ready": False,
        "packaging_smoke_ok": False,
        "strategy": "blocked" if baseline_contract_ok else "prefix-install",
        "strategy_family": "blocked" if baseline_contract_ok else "usable",
        "reason": "Packaging smoke blocked." if baseline_contract_ok else "Packaging smoke unexpectedly passed.",
        "failed_step": "packaging-status" if baseline_contract_ok else None,
        "expected_outcome": {
            "doctor_packaging_ready": False,
            "packaging_smoke_ok": False,
            "failed_step_present": True,
            "strategy_family_any_of": ["blocked"],
        },
        "matches_expectation": baseline_contract_ok,
        "expectation_drift": []
        if baseline_contract_ok
        else [
            {
                "capture": "blocked",
                "field": "failed_step",
                "kind": "missing_failed_step",
                "expected_present": True,
                "actual": None,
                "message": blocked_warning,
            }
        ],
    }
    payload = {
        "schema_version": 1,
        "captured_at": "2026-03-23T00:00:00Z",
        "output_dir": str(artifact_dir),
        "project_root": str(root),
        "project_root_source": "argument",
        "requested_project_root": str(root),
        "blocked_python": str(root / "__blocked_python__" / "missing-python"),
        "passing_capture": {
            "path": str(artifact_dir / "passing-packaging-capture.json"),
            "project_root": str(root),
            "project_root_source": "argument",
            "requested_project_root": str(root),
            "packaging_python": sys.executable,
            "packaging_python_source": "current",
            "doctor_packaging_ready": True,
            "packaging_smoke_ok": True,
            "strategy": "venv",
            "strategy_family": "usable",
            "reason": "Packaging smoke passed.",
            "failed_step": None,
            "expected_outcome": {
                "doctor_packaging_ready": True,
                "packaging_smoke_ok": True,
                "failed_step_present": False,
                "strategy_family_any_of": ["usable"],
            },
            "matches_expectation": True,
            "expectation_drift": [],
        },
        "blocked_capture": blocked_capture,
        "summary": {
            "passing_capture_matches_expectation": True,
            "blocked_capture_matches_expectation": baseline_contract_ok,
            "baseline_contract_ok": baseline_contract_ok,
        },
        "warnings": [] if baseline_contract_ok else [blocked_warning],
        "requirements": {
            "require_expected_outcomes": True,
            "ok": baseline_contract_ok,
            "failures": []
            if baseline_contract_ok
            else [f"Packaging baseline requirement failed: {blocked_warning}"],
        },
    }
    artifact_path.write_text(json.dumps(payload), encoding="utf-8")
    return artifact_path


def _write_packaging_baseline_archive(archive_path: Path, members: dict[str, dict[str, object]]) -> Path:
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, "w") as archive:
        for member_name, payload in members.items():
            archive.writestr(member_name, json.dumps(payload))
    return archive_path


def test_evaluate_packaging_baseline_gate_aggregates_artifact_tree(tmp_path):
    artifact_root = tmp_path / "downloaded-artifacts"
    ok_path = _write_packaging_baseline_artifact(
        artifact_root,
        "resource-hunter-packaging-baseline-ubuntu-latest-py3.12",
        baseline_contract_ok=True,
    )
    drift_path = _write_packaging_baseline_artifact(
        artifact_root,
        "resource-hunter-packaging-baseline-windows-latest-py3.13",
        baseline_contract_ok=False,
    )

    payload = packaging_gate.evaluate_packaging_baseline_gate([artifact_root])

    assert payload == {
        "gate_schema_version": packaging_gate.PACKAGING_BASELINE_GATE_SCHEMA_VERSION,
        "ok": False,
        "failure_count": 1,
        "failures": [
            f"{drift_path.resolve()}: Packaging baseline requirement failed: Blocked capture did not report failed_step."
        ],
        "report_type": "aggregate",
        "summary": {
            "artifact_count": 2,
            "contract_ok_artifact_count": 1,
            "contract_drift_artifact_count": 1,
            "requirement_failed_artifact_count": 1,
            "warning_count": 1,
            "all_baseline_contracts_ok": False,
        },
        "artifacts_with_contract_drift": [str(drift_path.resolve())],
        "artifacts_with_requirement_failures": [str(drift_path.resolve())],
    }
    assert str(ok_path.resolve()) not in payload["failures"]


def test_packaging_baseline_gate_main_json_exits_2_on_drift(capsys, tmp_path):
    artifact_root = tmp_path / "downloaded-artifacts"
    _write_packaging_baseline_artifact(
        artifact_root,
        "resource-hunter-packaging-baseline-ubuntu-latest-py3.12",
        baseline_contract_ok=True,
    )
    drift_path = _write_packaging_baseline_artifact(
        artifact_root,
        "resource-hunter-packaging-baseline-windows-latest-py3.13",
        baseline_contract_ok=False,
    )

    rc = packaging_gate.main(["--json", str(artifact_root)])

    captured = capsys.readouterr()
    assert rc == 2
    payload = json.loads(captured.out)
    assert payload["gate_schema_version"] == packaging_gate.PACKAGING_BASELINE_GATE_SCHEMA_VERSION
    assert payload["ok"] is False
    assert payload["failure_count"] == 1
    assert payload["artifacts_with_contract_drift"] == [str(drift_path.resolve())]
    assert (
        f"{drift_path.resolve()}: Packaging baseline requirement failed: Blocked capture did not report failed_step."
        in captured.err
    )


def test_packaging_baseline_gate_main_text_reports_single_ok_artifact(capsys, tmp_path):
    artifact_path = _write_packaging_baseline_artifact(
        tmp_path,
        "resource-hunter-packaging-baseline-windows-latest-py3.13",
        baseline_contract_ok=True,
    )

    rc = packaging_gate.main([str(artifact_path)])

    captured = capsys.readouterr()
    assert rc == 0
    assert "Resource Hunter packaging baseline gate" in captured.out
    assert "Status: ok" in captured.out
    assert f"Artifact: {artifact_path.resolve()}" in captured.out
    assert "Failure count: 0" in captured.out
    assert captured.err == ""


def test_evaluate_packaging_baseline_gate_accepts_zip_archives(tmp_path):
    archive_path = tmp_path / "downloaded-artifacts.zip"
    ok_payload_path = _write_packaging_baseline_artifact(
        tmp_path / "scratch",
        "resource-hunter-packaging-baseline-ubuntu-latest-py3.12",
        baseline_contract_ok=True,
    )
    ok_payload = json.loads(ok_payload_path.read_text(encoding="utf-8"))
    drift_payload_path = _write_packaging_baseline_artifact(
        tmp_path / "scratch",
        "resource-hunter-packaging-baseline-windows-latest-py3.13",
        baseline_contract_ok=False,
    )
    drift_payload = json.loads(drift_payload_path.read_text(encoding="utf-8"))
    _write_packaging_baseline_archive(
        archive_path,
        {
            "job-a/packaging-baseline.json": ok_payload,
            "job-b/packaging-baseline.json": drift_payload,
        },
    )

    payload = packaging_gate.evaluate_packaging_baseline_gate([archive_path])

    assert payload["gate_schema_version"] == packaging_gate.PACKAGING_BASELINE_GATE_SCHEMA_VERSION
    assert payload["ok"] is False
    assert payload["artifacts_with_contract_drift"] == [
        f"{archive_path.resolve()}!/job-b/packaging-baseline.json"
    ]


def test_packaging_baseline_gate_main_json_exits_2_on_zip_drift(capsys, tmp_path):
    archive_path = tmp_path / "downloaded-artifacts.zip"
    ok_payload_path = _write_packaging_baseline_artifact(
        tmp_path / "scratch",
        "resource-hunter-packaging-baseline-ubuntu-latest-py3.12",
        baseline_contract_ok=True,
    )
    ok_payload = json.loads(ok_payload_path.read_text(encoding="utf-8"))
    drift_payload_path = _write_packaging_baseline_artifact(
        tmp_path / "scratch",
        "resource-hunter-packaging-baseline-windows-latest-py3.13",
        baseline_contract_ok=False,
    )
    drift_payload = json.loads(drift_payload_path.read_text(encoding="utf-8"))
    _write_packaging_baseline_archive(
        archive_path,
        {
            "job-a/packaging-baseline.json": ok_payload,
            "job-b/packaging-baseline.json": drift_payload,
        },
    )

    rc = packaging_gate.main(["--json", str(archive_path)])

    captured = capsys.readouterr()
    drift_ref = f"{archive_path.resolve()}!/job-b/packaging-baseline.json"
    assert rc == 2
    payload = json.loads(captured.out)
    assert payload["gate_schema_version"] == packaging_gate.PACKAGING_BASELINE_GATE_SCHEMA_VERSION
    assert payload["ok"] is False
    assert payload["failure_count"] == 1
    assert payload["artifacts_with_contract_drift"] == [drift_ref]
    assert (
        f"{drift_ref}: Packaging baseline requirement failed: Blocked capture did not report failed_step."
        in captured.err
    )
