from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

import pytest

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


def test_evaluate_packaging_baseline_gate_records_required_artifact_count(tmp_path):
    artifact_root = tmp_path / "downloaded-artifacts"
    _write_packaging_baseline_artifact(
        artifact_root,
        "resource-hunter-packaging-baseline-ubuntu-latest-py3.12",
        baseline_contract_ok=True,
    )
    _write_packaging_baseline_artifact(
        artifact_root,
        "resource-hunter-packaging-baseline-windows-latest-py3.13",
        baseline_contract_ok=True,
    )

    payload = packaging_gate.evaluate_packaging_baseline_gate(
        [artifact_root],
        required_artifact_count=2,
    )

    assert payload["ok"] is True
    assert payload["failure_count"] == 0
    assert payload["expected_artifact_count"] == 2
    assert payload["actual_artifact_count"] == 2


def test_packaging_baseline_gate_main_json_exits_2_on_artifact_count_mismatch(capsys, tmp_path):
    artifact_root = tmp_path / "downloaded-artifacts"
    artifact_path = _write_packaging_baseline_artifact(
        artifact_root,
        "resource-hunter-packaging-baseline-ubuntu-latest-py3.12",
        baseline_contract_ok=True,
    )

    rc = packaging_gate.main(["--json", "--require-artifact-count", "2", str(artifact_root)])

    captured = capsys.readouterr()
    assert rc == 2
    payload = json.loads(captured.out)
    assert payload["gate_schema_version"] == packaging_gate.PACKAGING_BASELINE_GATE_SCHEMA_VERSION
    assert payload["ok"] is False
    assert payload["failure_count"] == 1
    assert payload["artifact_path"] == str(artifact_path.resolve())
    assert payload["expected_artifact_count"] == 2
    assert payload["actual_artifact_count"] == 1
    assert (
        "Packaging baseline gate expected 2 artifact(s) but found 1."
        in payload["failures"]
    )
    assert "Packaging baseline gate expected 2 artifact(s) but found 1." in captured.err


def test_packaging_baseline_gate_main_json_emits_error_payload_when_artifacts_missing(capsys, tmp_path):
    artifact_root = tmp_path / "downloaded-artifacts"
    artifact_root.mkdir()

    rc = packaging_gate.main(["--json", "--require-artifact-count", "2", str(artifact_root)])

    captured = capsys.readouterr()
    error = f"No packaging-baseline.json artifacts found under {artifact_root.resolve()}."
    assert rc == 1
    assert json.loads(captured.out) == {
        "gate_schema_version": packaging_gate.PACKAGING_BASELINE_GATE_SCHEMA_VERSION,
        "report_type": "error",
        "summary": {},
        "ok": False,
        "failure_count": 1,
        "failures": [error],
        "error": error,
        "expected_artifact_count": 2,
    }
    assert captured.err.strip() == error


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


def test_evaluate_packaging_baseline_gate_from_github_run_downloads_artifacts(monkeypatch, tmp_path):
    download_dir = tmp_path / "downloaded-gh-artifacts"
    seen: dict[str, object] = {}
    ubuntu_artifact = download_dir / "resource-hunter-packaging-baseline-ubuntu-latest-py3.12" / "packaging-baseline.json"
    windows_artifact = download_dir / "resource-hunter-packaging-baseline-windows-latest-py3.13" / "packaging-baseline.json"

    def fake_run_command(args, *, cwd, timeout=300):
        seen["args"] = list(args)
        seen["cwd"] = str(cwd)
        seen["timeout"] = timeout
        _write_packaging_baseline_artifact(
            download_dir,
            "resource-hunter-packaging-baseline-ubuntu-latest-py3.12",
            baseline_contract_ok=True,
        )
        _write_packaging_baseline_artifact(
            download_dir,
            "resource-hunter-packaging-baseline-windows-latest-py3.13",
            baseline_contract_ok=True,
        )
        return {
            "command": list(args),
            "cwd": str(cwd),
            "returncode": 0,
            "stdout": "downloaded",
            "stderr": "",
        }

    monkeypatch.setattr(packaging_gate.shutil, "which", lambda name: "/fake/bin/gh" if name == "gh" else None)
    monkeypatch.setattr(packaging_gate, "_run_command", fake_run_command)

    payload = packaging_gate.evaluate_packaging_baseline_gate_from_github_run(
        "123456",
        repo="openclaw/resource-hunter",
        download_dir=download_dir,
        required_artifact_count=2,
    )

    assert payload["ok"] is True
    assert payload["failure_count"] == 0
    assert payload["expected_artifact_count"] == 2
    assert payload["actual_artifact_count"] == 2
    assert payload["download"] == {
        "provider": "github-actions",
        "run_id": "123456",
        "repo": "openclaw/resource-hunter",
        "download_dir": str(download_dir.resolve()),
        "download_dir_source": "argument",
        "download_dir_retained": True,
        "artifact_names": [],
        "artifact_patterns": [packaging_gate.DEFAULT_GITHUB_ARTIFACT_PATTERN],
        "artifact_filter_source": "default",
        "resolved_artifact_count": 2,
        "resolved_artifact_paths": [str(ubuntu_artifact.resolve()), str(windows_artifact.resolve())],
        "resolved_archive_member_count": 0,
        "resolved_filesystem_artifact_count": 2,
        "download_command": [
            "/fake/bin/gh",
            "run",
            "download",
            "123456",
            "--repo",
            "openclaw/resource-hunter",
            "--dir",
            str(download_dir.resolve()),
            "--pattern",
            packaging_gate.DEFAULT_GITHUB_ARTIFACT_PATTERN,
        ],
    }
    assert seen == {
        "args": [
            "/fake/bin/gh",
            "run",
            "download",
            "123456",
            "--repo",
            "openclaw/resource-hunter",
            "--dir",
            str(download_dir.resolve()),
            "--pattern",
            packaging_gate.DEFAULT_GITHUB_ARTIFACT_PATTERN,
        ],
        "cwd": str(Path.cwd()),
        "timeout": 300,
    }


def test_evaluate_packaging_baseline_gate_from_github_run_uses_environment_repo_when_repo_omitted(
    monkeypatch, tmp_path
):
    download_dir = tmp_path / "downloaded-gh-artifacts"
    seen: dict[str, object] = {}

    def fake_run_command(args, *, cwd, timeout=300):
        seen["args"] = list(args)
        _write_packaging_baseline_artifact(
            download_dir,
            "resource-hunter-packaging-baseline-ubuntu-latest-py3.12",
            baseline_contract_ok=True,
        )
        return {
            "command": list(args),
            "cwd": str(cwd),
            "returncode": 0,
            "stdout": "downloaded",
            "stderr": "",
        }

    monkeypatch.setenv("GITHUB_REPOSITORY", "openclaw/resource-hunter")
    monkeypatch.setattr(packaging_gate.shutil, "which", lambda name: "/fake/bin/gh" if name == "gh" else None)
    monkeypatch.setattr(packaging_gate, "_run_command", fake_run_command)

    payload = packaging_gate.evaluate_packaging_baseline_gate_from_github_run(
        "123456",
        download_dir=download_dir,
        required_artifact_count=1,
    )

    assert payload["download"]["repo"] == "openclaw/resource-hunter"
    assert payload["download"]["repo_source"] == "environment"
    assert seen["args"] == [
        "/fake/bin/gh",
        "run",
        "download",
        "123456",
        "--repo",
        "openclaw/resource-hunter",
        "--dir",
        str(download_dir.resolve()),
        "--pattern",
        packaging_gate.DEFAULT_GITHUB_ARTIFACT_PATTERN,
    ]


def test_evaluate_packaging_baseline_gate_from_github_run_uses_git_origin_repo_when_repo_omitted(
    monkeypatch, tmp_path
):
    download_dir = tmp_path / "downloaded-gh-artifacts"
    seen: dict[str, object] = {}

    def fake_git_run(args, *, cwd, check, capture_output, text, timeout):
        assert args == ["git", "remote", "get-url", "origin"]
        assert check is False
        assert capture_output is True
        assert text is True
        assert timeout == 10
        return packaging_gate.subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout="https://github.com/openclaw/resource-hunter.git\n",
            stderr="",
        )

    def fake_run_command(args, *, cwd, timeout=300):
        seen["args"] = list(args)
        _write_packaging_baseline_artifact(
            download_dir,
            "resource-hunter-packaging-baseline-ubuntu-latest-py3.12",
            baseline_contract_ok=True,
        )
        return {
            "command": list(args),
            "cwd": str(cwd),
            "returncode": 0,
            "stdout": "downloaded",
            "stderr": "",
        }

    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    monkeypatch.setattr(packaging_gate.shutil, "which", lambda name: "/fake/bin/gh" if name == "gh" else None)
    monkeypatch.setattr(packaging_gate.subprocess, "run", fake_git_run)
    monkeypatch.setattr(packaging_gate, "_run_command", fake_run_command)

    payload = packaging_gate.evaluate_packaging_baseline_gate_from_github_run(
        "123456",
        download_dir=download_dir,
        required_artifact_count=1,
    )

    assert payload["download"]["repo"] == "openclaw/resource-hunter"
    assert payload["download"]["repo_source"] == "git-origin"
    assert seen["args"] == [
        "/fake/bin/gh",
        "run",
        "download",
        "123456",
        "--repo",
        "openclaw/resource-hunter",
        "--dir",
        str(download_dir.resolve()),
        "--pattern",
        packaging_gate.DEFAULT_GITHUB_ARTIFACT_PATTERN,
    ]


def test_packaging_baseline_gate_main_errors_when_gh_download_fails(capsys, monkeypatch):
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    monkeypatch.setattr(packaging_gate.shutil, "which", lambda name: "/fake/bin/gh" if name == "gh" else None)
    monkeypatch.setattr(
        packaging_gate.subprocess,
        "run",
        lambda *args, **kwargs: packaging_gate.subprocess.CompletedProcess(args=args[0], returncode=1),
    )
    monkeypatch.setattr(
        packaging_gate,
        "_run_command",
        lambda args, *, cwd, timeout=300: {
            "command": list(args),
            "cwd": str(cwd),
            "returncode": 1,
            "stdout": "",
            "stderr": "artifact download failed",
        },
    )

    rc = packaging_gate.main(["--github-run", "987654"])

    captured = capsys.readouterr()
    assert rc == 1
    assert captured.out == ""
    assert (
        captured.err.strip()
        == "GitHub Actions artifact download failed for run 987654: artifact download failed"
    )


def test_packaging_baseline_gate_main_json_emits_error_payload_when_gh_download_fails(capsys, monkeypatch, tmp_path):
    download_dir = tmp_path / "downloaded-gh-artifacts"
    monkeypatch.setattr(packaging_gate.shutil, "which", lambda name: "/fake/bin/gh" if name == "gh" else None)
    monkeypatch.setattr(
        packaging_gate,
        "_run_command",
        lambda args, *, cwd, timeout=300: {
            "command": list(args),
            "cwd": str(cwd),
            "returncode": 1,
            "stdout": "",
            "stderr": "artifact download failed",
        },
    )

    rc = packaging_gate.main(
        [
            "--json",
            "--github-run",
            "987654",
            "--repo",
            "openclaw/resource-hunter",
            "--download-dir",
            str(download_dir),
        ]
    )

    captured = capsys.readouterr()
    error = "GitHub Actions artifact download failed for openclaw/resource-hunter run 987654: artifact download failed"
    assert rc == 1
    assert json.loads(captured.out) == {
        "gate_schema_version": packaging_gate.PACKAGING_BASELINE_GATE_SCHEMA_VERSION,
        "report_type": "error",
        "summary": {},
        "ok": False,
        "failure_count": 1,
        "failures": [error],
        "error": error,
        "download": {
            "provider": "github-actions",
            "run_id": "987654",
            "repo": "openclaw/resource-hunter",
            "download_dir": str(download_dir.resolve()),
            "download_dir_source": "argument",
            "download_dir_retained": True,
            "artifact_names": [],
            "artifact_patterns": [packaging_gate.DEFAULT_GITHUB_ARTIFACT_PATTERN],
            "artifact_filter_source": "default",
            "download_command": [
                "/fake/bin/gh",
                "run",
                "download",
                "987654",
                "--repo",
                "openclaw/resource-hunter",
                "--dir",
                str(download_dir.resolve()),
                "--pattern",
                packaging_gate.DEFAULT_GITHUB_ARTIFACT_PATTERN,
            ],
            "download_returncode": 1,
            "download_stderr": "artifact download failed",
        },
    }
    assert captured.err.strip() == error


def test_packaging_baseline_gate_main_json_emits_error_payload_when_github_run_has_no_artifacts(
    capsys, monkeypatch, tmp_path
):
    download_dir = tmp_path / "downloaded-gh-artifacts"
    monkeypatch.setattr(packaging_gate.shutil, "which", lambda name: "/fake/bin/gh" if name == "gh" else None)
    monkeypatch.setattr(
        packaging_gate,
        "_run_command",
        lambda args, *, cwd, timeout=300: {
            "command": list(args),
            "cwd": str(cwd),
            "returncode": 0,
            "stdout": "downloaded",
            "stderr": "",
        },
    )

    rc = packaging_gate.main(
        [
            "--json",
            "--github-run",
            "123456",
            "--repo",
            "openclaw/resource-hunter",
            "--download-dir",
            str(download_dir),
            "--require-artifact-count",
            "2",
        ]
    )

    captured = capsys.readouterr()
    error = f"No packaging-baseline.json artifacts found under {download_dir.resolve()}."
    assert rc == 1
    assert json.loads(captured.out) == {
        "gate_schema_version": packaging_gate.PACKAGING_BASELINE_GATE_SCHEMA_VERSION,
        "report_type": "error",
        "summary": {},
        "ok": False,
        "failure_count": 1,
        "failures": [error],
        "error": error,
        "expected_artifact_count": 2,
        "download": {
            "provider": "github-actions",
            "run_id": "123456",
            "repo": "openclaw/resource-hunter",
            "download_dir": str(download_dir.resolve()),
            "download_dir_source": "argument",
            "download_dir_retained": True,
            "artifact_names": [],
            "artifact_patterns": [packaging_gate.DEFAULT_GITHUB_ARTIFACT_PATTERN],
            "artifact_filter_source": "default",
            "resolved_artifact_count": 0,
            "resolved_artifact_paths": [],
            "resolved_archive_member_count": 0,
            "resolved_filesystem_artifact_count": 0,
            "download_command": [
                "/fake/bin/gh",
                "run",
                "download",
                "123456",
                "--repo",
                "openclaw/resource-hunter",
                "--dir",
                str(download_dir.resolve()),
                "--pattern",
                packaging_gate.DEFAULT_GITHUB_ARTIFACT_PATTERN,
            ],
        },
    }
    assert captured.err.strip() == error


def test_packaging_baseline_gate_main_rejects_paths_with_github_run():
    with pytest.raises(SystemExit) as excinfo:
        packaging_gate.main(["--github-run", "123456", "artifacts/downloaded-gh-artifacts"])

    assert excinfo.value.code == 2
