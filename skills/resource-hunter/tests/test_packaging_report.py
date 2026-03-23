from __future__ import annotations

import json
import sys

import pytest

from resource_hunter.errors import ResourceHunterError
from resource_hunter.packaging_report import (
    PACKAGING_BASELINE_REPORT_SCHEMA_VERSION,
    build_packaging_baseline_report,
    load_packaging_baseline_payload,
    read_packaging_baseline_report,
)


def _baseline_payload(tmp_path):
    return {
        "schema_version": 1,
        "captured_at": "2026-03-23T00:00:00Z",
        "output_dir": str(tmp_path),
        "project_root": str(tmp_path),
        "project_root_source": "argument",
        "requested_project_root": str(tmp_path),
        "blocked_python": str(tmp_path / "__blocked_python__" / "missing-python"),
        "passing_capture": {
            "path": str(tmp_path / "passing-packaging-capture.json"),
            "project_root": str(tmp_path),
            "project_root_source": "argument",
            "requested_project_root": str(tmp_path),
            "packaging_python": sys.executable,
            "packaging_python_source": "current",
            "doctor_packaging_ready": True,
            "packaging_smoke_ok": True,
            "strategy": "prefix-install",
            "strategy_family": "usable",
            "reason": "Packaging smoke passed.",
            "failed_step": None,
            "expected_outcome": {
                "doctor_packaging_ready": True,
                "packaging_smoke_ok": True,
                "failed_step_present": False,
                "strategy_family_any_of": ["usable", "bootstrap"],
            },
            "matches_expectation": True,
            "expectation_drift": [],
        },
        "blocked_capture": {
            "path": str(tmp_path / "blocked-packaging-capture.json"),
            "project_root": str(tmp_path),
            "project_root_source": "argument",
            "requested_project_root": str(tmp_path),
            "packaging_python": str(tmp_path / "__blocked_python__" / "missing-python"),
            "packaging_python_source": "argument",
            "doctor_packaging_ready": False,
            "packaging_smoke_ok": False,
            "strategy": "missing-python",
            "strategy_family": "blocked",
            "reason": "Python executable was not found.",
            "failed_step": "packaging-status",
            "expected_outcome": {
                "doctor_packaging_ready": False,
                "packaging_smoke_ok": False,
                "failed_step_present": True,
                "strategy_family_any_of": ["blocked"],
            },
            "matches_expectation": True,
            "expectation_drift": [],
        },
        "summary": {
            "passing_capture_matches_expectation": True,
            "blocked_capture_matches_expectation": True,
            "baseline_contract_ok": True,
        },
        "warnings": [],
        "requirements": {
            "require_expected_outcomes": True,
            "ok": True,
            "failures": [],
        },
    }


def test_build_packaging_baseline_report_normalizes_artifact(tmp_path):
    payload = _baseline_payload(tmp_path)

    report = build_packaging_baseline_report(payload, artifact_path=tmp_path / "packaging-baseline.json")

    assert report["report_schema_version"] == PACKAGING_BASELINE_REPORT_SCHEMA_VERSION
    assert report["report_type"] == "single"
    assert report["summary"]["baseline_contract_ok"] is True
    assert [capture["name"] for capture in report["captures"]] == ["passing", "blocked"]
    assert report["captures"][0]["actual"] == {
        "doctor_packaging_ready": True,
        "packaging_smoke_ok": True,
        "failed_step": None,
        "strategy_family": "usable",
        "strategy": "prefix-install",
        "reason": "Packaging smoke passed.",
    }
    assert report["captures"][1]["expected_outcome"]["strategy_family_any_of"] == ["blocked"]


def test_read_packaging_baseline_report_reads_archive_from_disk(tmp_path):
    artifact_path = tmp_path / "packaging-baseline.json"
    artifact_path.write_text(json.dumps(_baseline_payload(tmp_path)), encoding="utf-8")

    report = read_packaging_baseline_report(artifact_path)

    assert report["artifact_path"] == str(artifact_path.resolve())
    assert report["captures"][1]["matches_expectation"] is True
    assert report["requirements"] == {
        "require_expected_outcomes": True,
        "ok": True,
        "failures": [],
    }


def test_load_packaging_baseline_payload_rejects_missing_capture_entries(tmp_path):
    artifact_path = tmp_path / "packaging-baseline.json"
    artifact_path.write_text(json.dumps({"schema_version": 1, "passing_capture": {}}), encoding="utf-8")

    with pytest.raises(ResourceHunterError, match="does not contain passing_capture and blocked_capture entries"):
        load_packaging_baseline_payload(artifact_path)
