# Resource Hunter

Installable Python package and OpenClaw/ClawHub skill for public pan, torrent, magnet, and public video URL discovery.

- Standard entrypoints: `resource-hunter`, `python -m resource_hunter`
- Source checkout wrappers: `scripts/hunt.py`, `scripts/packaging_gate.py`
- Quick runtime checks: `resource-hunter --version`, `resource-hunter doctor --json`, `resource-hunter doctor --json --require-packaging-ready`, `resource-hunter doctor --json --python /path/to/python --require-packaging-ready`, `resource-hunter doctor --json --python auto --require-packaging-ready`, `resource-hunter doctor --json --project-root /path/to/repo --python auto --bootstrap-build-deps --require-packaging-ready`, `resource-hunter packaging-smoke --json`, `resource-hunter packaging-smoke --json --bootstrap-build-deps`, `resource-hunter packaging-capture --project-root /path/to/repo --python auto --bootstrap-build-deps --output artifacts/packaging-capture.json`, `resource-hunter packaging-baseline --project-root /path/to/repo --python auto --bootstrap-build-deps --output-dir artifacts/packaging-baseline --require-expected-outcomes`, `resource-hunter packaging-baseline-report artifacts/packaging-baseline/packaging-baseline.json`, `resource-hunter packaging-baseline-report artifacts/downloaded-gh-artifacts --json --require-contract-ok`, `resource-hunter-packaging-baseline-gate artifacts/downloaded-gh-artifacts --json`
- `doctor --json` reports packaging blockers, interpreter probe failures via `packaging.error`, the resolved checkout root via top-level `project_root` plus `packaging.project_root`, and the root provenance via top-level `project_root_source` plus `packaging.project_root_source` (`argument` for an explicit `--project-root`, `discovered` for cwd/upward-walk resolution). When `--project-root` is passed it also records the original requested path via top-level `requested_project_root` plus `packaging.requested_project_root`. It also reports the selected console-script smoke strategy alongside `pip`, `wheel`, `setuptools.build_meta`, and `venv`. Add `--python /path/to/python` to inspect another interpreter without switching shells, set `RESOURCE_HUNTER_PACKAGING_PYTHON=/path/to/python` so CI/ops can reuse the same target interpreter across commands, or use `--python auto` / `RESOURCE_HUNTER_PACKAGING_PYTHON=auto` to auto-select the first packaging-ready interpreter discoverable via the current interpreter, active envs, PATH, and the Windows `py` launcher. Add `--bootstrap-build-deps` when doctor should also accept an interpreter that can bootstrap this checkout's declared build requirements into a disposable overlay, and add `--project-root` when the target checkout is not under the current working directory.
- `doctor --require-packaging-ready` preserves the normal doctor output but exits with code `2` when packaging smoke is blocked, which makes it suitable for CI or ops gates. Pair it with `--bootstrap-build-deps` when the selected interpreter has `pip` but is still missing only `setuptools.build_meta` and/or `wheel`.
- `packaging-smoke --json` performs the actual wheel-build, install, `python -m resource_hunter`, and `resource-hunter` entrypoint smoke against the current checkout; it now reports `project_root`, `project_root_source`, `requested_project_root` when `--project-root` is passed, `packaging.project_root`, `packaging.project_root_source`, `packaging.requested_project_root`, `packaging_python`, `packaging_python_source`, stable route fields `strategy` plus `strategy_family`, `packaging.error`, `failed_step` even for preflight failures such as `packaging-status` or `packaging-gate`, and auto-discovery candidate details when `auto` is requested, so CI/ops logs show both which interpreter ran and whether the checkout root came from an explicit request or discovery before any build/install step. Add `--project-root` when packaging validation targets another checkout, and `--bootstrap-build-deps` to temporarily install the declared build requirements into a disposable overlay when the selected interpreter has `pip` but is still missing `setuptools.build_meta` and/or `wheel`; `--python auto --bootstrap-build-deps` now auto-selects bootstrap-capable interpreters against that explicit root too.
- `packaging-capture` bundles one `doctor` payload plus one `packaging-smoke` payload into a single archival-oriented JSON artifact, mirrors the shared provenance fields (`requested_project_root`, `project_root`, `project_root_source`, `packaging_python`, `packaging_python_source`, `packaging_python_auto_selected`, `packaging_python_candidates`) plus top-level `failed_step`, and adds compact `summary` and `requirements` blocks so CI/ops capture jobs can archive both success and intentionally blocked baselines without stitching two commands together or scraping stderr. `summary` now includes both `strategy` and stable `strategy_family` so dashboards can distinguish usable vs blocked routes without understanding every concrete install path. The command always emits JSON, accepts `--output` to write the same bundle to disk, and still defaults to exit code `0` once the capture artifact is produced. Add `--require-packaging-ready` and/or `--require-smoke-ok` when a gate should fail with code `2` after writing the artifact if the nested doctor/smoke expectations are not met.
- `packaging-baseline` builds on `packaging-capture` for local artifact refreshes: it writes `passing-packaging-capture.json`, `blocked-packaging-capture.json`, and `packaging-baseline.json` under `--output-dir` (default `artifacts/packaging-baseline`) so ops can refresh one passing bundle plus one intentionally blocked bundle in a single command. The roll-up mirrors each capture's `project_root`, `project_root_source`, `requested_project_root`, `doctor_packaging_ready`, `packaging_smoke_ok`, `strategy`, `strategy_family`, `reason`, and `failed_step`, now adds per-capture `expected_outcome`, `matches_expectation`, and machine-readable `expectation_drift` entries (including `strategy_mismatch` when the route family changes), and still exposes top-level `summary`, `warnings`, and `requirements` for lightweight consumers. `expected_outcome` records the baseline contract directly beside each capture, including the expected readiness booleans, whether `failed_step` should be present, and the allowed `strategy_family` values, so dashboards can render the contract without hardcoding it. `--require-expected-outcomes` exits with code `2` after writing artifacts when the passing capture does not stay in the usable route family (`strategy_family=usable`) or the blocked capture does not stay intentionally blocked (`strategy_family=blocked` plus a `failed_step`). The raw `strategy` value remains in the artifact for concrete route diagnostics. The `requirements` block records whether that gate was requested, whether it passed overall, and the exact failure strings emitted on stderr when it fails. By default the blocked capture uses a generated missing interpreter path, or you can force a specific path via `--blocked-python`.
- `packaging-baseline-report` is the read-only companion for archived baseline artifacts. It now accepts individual `packaging-baseline.json` files, multiple explicit paths, `.zip` archives that contain one or more `packaging-baseline.json` members, or directories that are scanned recursively for `packaging-baseline.json` so downloaded GitHub Actions matrix artifacts can be consumed without ad-hoc shell glue. Single-artifact input keeps the normalized `captures` report, while multi-artifact input emits an aggregate envelope with `report_type=aggregate`, per-artifact nested reports, top-level contract counts, and prefixed warnings. Zip-backed artifacts are surfaced as `archive.zip!/inner/path/packaging-baseline.json` so downstream logs stay source-addressable. Add `--json` when a downstream consumer wants machine-readable output, and add `--require-contract-ok` when dashboards or release jobs should exit with code `2` after printing the report if any archived artifact shows packaging-baseline contract drift.
- Python consumers can now reuse the same single-artifact normalization and multi-artifact aggregation without shelling out by calling `resource_hunter.packaging_report.read_packaging_baseline_report(path)`, `resource_hunter.packaging_report.read_packaging_baseline_reports(paths)`, or `resource_hunter.packaging_report.build_packaging_baseline_report(payload, artifact_path=...)`. For downstream jobs that only need a gate-ready summary, `resource_hunter.packaging_gate.evaluate_packaging_baseline_gate(paths)` now returns a versioned payload with `gate_schema_version`, `ok`, `failure_count`, `failures`, and the normalized summary block in one call, while installed environments expose the same flow as `resource-hunter-packaging-baseline-gate` and source checkouts can run `python3 scripts/packaging_gate.py` without an editable install.
- `resource_hunter.packaging_smoke.run_packaging_smoke()` now returns the same interpreter-provenance plus requested/resolved-project-root fields as the CLI path, including `project_root_source` and `strategy_family`, and accepts optional source/candidate overrides for env-driven or auto-selected callers
- Legacy compatibility wrappers: `scripts/pansou.py`, `scripts/torrent.py`, `scripts/video.py`
- Key regression samples: `Breaking Bad S01E01`, `Oppenheimer 2023`, `赤橙黄绿青蓝紫 1982`

## Packaging probe errors

When `--python` points at a bad interpreter path, both JSON flows stay machine-readable instead of aborting. CI/ops consumers should key on `packaging.error`.

`doctor --json --python /bad/path` keeps the normal doctor payload and surfaces the probe failure under `packaging.error`:

```json
{
  "project_root": "/path/to/repo",
  "project_root_source": "discovered",
  "packaging_python": "/bad/path",
  "packaging_python_source": "argument",
  "packaging": {
    "project_root": "/path/to/repo",
    "project_root_source": "discovered",
    "pip": null,
    "venv": null,
    "setuptools_build_meta": null,
    "wheel": null,
    "console_script_strategy": "blocked",
    "error": "Unable to inspect packaging modules via /bad/path: <launcher error>"
  },
  "advice": [
    "/bad/path (via --python) could not be inspected for packaging readiness: Unable to inspect packaging modules via /bad/path: <launcher error>. Check the interpreter path or pass a working Python via --python."
  ]
}
```

`packaging-smoke --json --python /bad/path` returns a blocked payload instead of a generic crash; `reason` summarizes the failure and `packaging.error` preserves the original probe detail:

```json
{
  "ok": false,
  "strategy": "blocked",
  "project_root": "/path/to/repo",
  "project_root_source": "discovered",
  "reason": "Packaging smoke is blocked: Unable to inspect packaging modules via /bad/path: <launcher error>",
  "packaging_python": "/bad/path",
  "packaging_python_source": "argument",
  "packaging": {
    "project_root": "/path/to/repo",
    "project_root_source": "discovered",
    "error": "Unable to inspect packaging modules via /bad/path: <launcher error>"
  }
}
```

See [SKILL.md](./SKILL.md) for skill-focused usage.
