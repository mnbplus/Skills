from __future__ import annotations

import json
import sys
from pathlib import Path

import resource_hunter.cli as cli


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


def test_cli_packaging_baseline_report_single_artifact_can_require_contract_ok(capsys, tmp_path):
    artifact_path = _write_packaging_baseline_artifact(
        tmp_path,
        "resource-hunter-packaging-baseline-windows-py3.13",
        baseline_contract_ok=False,
    )

    rc = cli.main(["packaging-baseline-report", "--require-contract-ok", str(artifact_path)])

    captured = capsys.readouterr()
    assert rc == 2
    assert "Resource Hunter packaging baseline report" in captured.out
    assert str(artifact_path.resolve()) in captured.err
    assert "Packaging baseline requirement failed" in captured.err


def test_cli_packaging_baseline_report_directory_aggregates_json(capsys, tmp_path):
    artifacts_root = tmp_path / "downloaded-artifacts"
    ok_path = _write_packaging_baseline_artifact(
        artifacts_root,
        "resource-hunter-packaging-baseline-ubuntu-latest-py3.12",
        baseline_contract_ok=True,
    )
    drift_path = _write_packaging_baseline_artifact(
        artifacts_root,
        "resource-hunter-packaging-baseline-windows-latest-py3.13",
        baseline_contract_ok=False,
    )

    rc = cli.main(["packaging-baseline-report", "--json", str(artifacts_root)])

    assert rc == 0
    report = json.loads(capsys.readouterr().out)
    assert report["report_type"] == "aggregate"
    assert report["summary"] == {
        "artifact_count": 2,
        "contract_ok_artifact_count": 1,
        "contract_drift_artifact_count": 1,
        "requirement_failed_artifact_count": 1,
        "warning_count": 1,
        "all_baseline_contracts_ok": False,
    }
    assert report["artifacts_with_contract_drift"] == [str(drift_path.resolve())]
    assert report["artifacts_with_requirement_failures"] == [str(drift_path.resolve())]
    assert report["warnings"] == [
        f"{drift_path.resolve()}: Blocked capture did not report failed_step."
    ]
    assert [artifact["artifact_path"] for artifact in report["artifacts"]] == [
        str(ok_path.resolve()),
        str(drift_path.resolve()),
    ]
    assert report["artifacts"][0]["report_type"] == "single"
    assert report["artifacts"][1]["summary"]["baseline_contract_ok"] is False


def test_cli_packaging_baseline_report_directory_without_artifacts_errors(capsys, tmp_path):
    empty_dir = tmp_path / "downloaded-artifacts"
    empty_dir.mkdir()

    rc = cli.main(["packaging-baseline-report", str(empty_dir)])

    captured = capsys.readouterr()
    assert rc == 1
    assert "No packaging-baseline.json artifacts found under" in captured.err
    assert str(empty_dir.resolve()) in captured.err
