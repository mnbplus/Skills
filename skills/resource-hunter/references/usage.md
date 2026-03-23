# Resource Hunter Usage

## Search

Main command:

```bash
python3 scripts/hunt.py search "<query>" [options]
```

Key options:

- `--kind movie|tv|anime|music|software|book|general`
- `--channel both|pan|torrent`
- `--quick`
- `--sub`
- `--4k`
- `--json`
- `--page`
- `--limit`

Examples:

```bash
python3 scripts/hunt.py search "Oppenheimer 2023" --kind movie --4k
python3 scripts/hunt.py search "Breaking Bad S01E01" --tv
python3 scripts/hunt.py search "杩涘嚮鐨勫法浜?Attack on Titan" --anime --sub
python3 scripts/hunt.py search "涓変綋 epub" --book --channel pan
python3 scripts/hunt.py search "鍛ㄦ澃浼?鏃犳崯" --music --quick
python3 scripts/hunt.py search "Adobe Photoshop 2024" --software --json
```

## Video

Public video URLs go through the `video` subcommands:

```bash
python3 scripts/hunt.py video info "https://youtu.be/..."
python3 scripts/hunt.py video probe "https://www.bilibili.com/video/BV..."
python3 scripts/hunt.py video download "https://youtu.be/..." best
python3 scripts/hunt.py video download "https://youtu.be/..." balanced
python3 scripts/hunt.py video download "https://youtu.be/..." small
python3 scripts/hunt.py video download "https://youtu.be/..." audio
python3 scripts/hunt.py video subtitle "https://youtu.be/..." --lang zh-Hans,zh,en
```

Download presets:

- `best`: highest quality available
- `balanced`: prefer <=1080p
- `small`: prefer <=720p
- `audio`: audio only

## Legacy wrappers

These remain available for one compatibility cycle:

```bash
python3 scripts/pansou.py "Oppenheimer 2023" --max 5
python3 scripts/torrent.py "Breaking Bad S01E01" --tv --limit 8
python3 scripts/video.py info "https://youtu.be/..."
```

## Packaging smoke

Use the packaging gate and the full smoke together when validating a checkout:

```bash
python3 scripts/hunt.py doctor --json --require-packaging-ready
python3 scripts/hunt.py doctor --json --python /path/to/python --require-packaging-ready
python3 scripts/hunt.py doctor --json --python auto --require-packaging-ready
python3 scripts/hunt.py doctor --json --project-root /path/to/repo --python auto --bootstrap-build-deps --require-packaging-ready
python3 scripts/hunt.py doctor --json --python auto --bootstrap-build-deps --require-packaging-ready
python3 scripts/hunt.py packaging-smoke --json
python3 scripts/hunt.py packaging-smoke --json --python /path/to/python
python3 scripts/hunt.py packaging-smoke --json --python auto
python3 scripts/hunt.py packaging-smoke --json --bootstrap-build-deps
python3 scripts/hunt.py packaging-capture --project-root /path/to/repo --python auto --bootstrap-build-deps --output artifacts/packaging-capture.json
python3 scripts/hunt.py packaging-capture --project-root /path/to/repo --python auto --bootstrap-build-deps --output artifacts/packaging-capture.json --require-packaging-ready --require-smoke-ok
python3 scripts/hunt.py packaging-baseline --project-root /path/to/repo --python auto --bootstrap-build-deps --output-dir artifacts/packaging-baseline --require-expected-outcomes
python3 scripts/hunt.py packaging-baseline-report artifacts/packaging-baseline/packaging-baseline.json
python3 scripts/hunt.py packaging-baseline-report --json artifacts/packaging-baseline/packaging-baseline.json
python3 scripts/hunt.py packaging-baseline-report artifacts/downloaded-gh-artifacts --json --require-contract-ok
python3 scripts/packaging_report.py --json artifacts/downloaded-gh-artifacts
resource-hunter-packaging-baseline-report artifacts/downloaded-gh-artifacts --json --require-contract-ok
python3 -m resource_hunter.packaging_gate artifacts/downloaded-gh-artifacts --json
python3 scripts/packaging_gate.py artifacts/downloaded-gh-artifacts --json
```

Notes:

- `packaging-smoke` auto-detects the project root from the current directory and also accepts `--project-root`
- `doctor` can also take `--project-root` so bootstrap-aware inspection still works when CI or ops runs outside the checkout, and `packaging-smoke --python auto` now forwards its explicit `--project-root` into interpreter auto-selection
- `doctor` and `packaging-smoke` both accept `--python` so CI or ops can inspect and smoke-test a different interpreter without changing the launcher command; pass `auto` to scan the current interpreter, active envs, PATH, and the Windows `py` launcher for the first packaging-ready interpreter, or combine `auto` with `--bootstrap-build-deps` to accept the first interpreter that can bootstrap this checkout's declared build requirements
- `packaging-smoke --bootstrap-build-deps` uses `pip install --target` to stage this checkout's declared build requirements into a disposable overlay before running the normal wheel-build smoke, which helps on lean Python runtimes that have `pip` but not `setuptools.build_meta` and/or `wheel`
- `doctor --bootstrap-build-deps` does not install anything; it reuses the same bootstrap feasibility check for auto-selection, JSON/text reporting, and `--require-packaging-ready` gating
- `packaging-capture` always emits JSON, reuses `doctor`'s selected packaging interpreter when it invokes `packaging-smoke`, mirrors the shared provenance fields plus top-level `failed_step`, records `summary` and `requirements` roll-ups for gate-friendly consumers, and can also write the same bundle to `--output` for CI or ops archival jobs. `summary` includes both the raw `strategy` and stable `strategy_family`.
- `packaging-capture` is archival-oriented: it still returns `0` once the combined artifact is produced by default, even when the nested smoke payload is intentionally blocked, so baseline refresh flows can archive blocked fixtures; add `--require-packaging-ready` and/or `--require-smoke-ok` when downstream automation should fail with exit code `2` after the artifact is written
- `packaging-baseline` writes three JSON artifacts in one go: `passing-packaging-capture.json`, `blocked-packaging-capture.json`, and `packaging-baseline.json`; the roll-up mirrors each capture's `project_root`, `project_root_source`, `requested_project_root`, `doctor_packaging_ready`, `packaging_smoke_ok`, `strategy`, `strategy_family`, `reason`, and `failed_step`, includes top-level `summary`, `warnings`, and `requirements`, and supports `--require-expected-outcomes` when a refresh job should fail after writing artifacts if the expected pass/block contrast drifts. That expectation now checks both the outcome booleans and the smoke route family: the passing capture must remain in `strategy_family=usable` while the intentionally blocked capture must remain `strategy_family=blocked` and report a `failed_step`. The raw `strategy` still remains available for concrete route diagnostics. The `requirements` block records whether that gate was requested, whether it passed overall, and the exact failure strings that also reach stderr.
- `packaging-baseline-report` consumes one archived `packaging-baseline.json`, multiple explicit baseline files, `.zip` archives that contain one or more `packaging-baseline.json` members, or directories that are scanned recursively for `packaging-baseline.json` and nested `.zip` downloads so downloaded CI artifact trees can be consumed without ad-hoc shell loops or a pre-extract step. Single-artifact input keeps the normalized `artifact_path` + `captures` view; multi-artifact input emits an aggregate report with top-level contract counts, prefixed warnings, and nested per-artifact reports. Zip-backed artifacts are rendered as `archive.zip!/inner/path/packaging-baseline.json` so logs still point at the original archive member. Add `--json` for machine-readable output, add `--require-contract-ok` when downstream automation should exit with code `2` after printing the report if any archived artifact drifts from the expected passing-vs-blocked contract, or add `--github-run <run-id>` with optional `--repo`, `--artifact-name`, `--artifact-pattern`, `--download-dir`, and `--keep-download-dir` when the report flow should fetch one GitHub Actions run via `gh run download` before normalization. When `--repo` is omitted, the download path now tries `GITHUB_REPOSITORY`, then the checkout's git `origin`, and only then falls back to the current `gh` repository context. In that mode the emitted JSON carries a top-level `download` block plus `resolved_artifact_count`, `resolved_artifact_paths`, `resolved_archive_member_count`, `resolved_filesystem_artifact_count`, and any inferred `repo_source` so CI can see exactly which artifacts were consumed after download. Pre-report failures with `--json` still emit a `report_type=error` payload so CI can archive structured diagnostics after a failed download or empty bundle. Use `scripts/packaging_report.py` or the installed `resource-hunter-packaging-baseline-report` entrypoint when a caller wants the report flow without routing through `resource-hunter`.
- Direct Python consumers can now import `resource_hunter.packaging_report.read_packaging_baseline_report()`, `resource_hunter.packaging_report.read_packaging_baseline_reports()`, `resource_hunter.packaging_report.read_packaging_baseline_reports_from_github_run()`, or `resource_hunter.packaging_report.build_packaging_baseline_report()` to get the same normalized single-artifact envelope or aggregate report without shelling out or re-parsing `passing_capture` / `blocked_capture`. Installed callers can also use `resource-hunter-packaging-baseline-report` or `python -m resource_hunter.packaging_report`, while source checkouts can use `python3 scripts/packaging_report.py`, when they want that report flow without routing through the main CLI. When a downstream job only needs the read-only gate result, `resource_hunter.packaging_gate.evaluate_packaging_baseline_gate()` wraps that report API together with `packaging_baseline_report_requirement_failures()` and now returns a versioned payload via `gate_schema_version`, while `evaluate_packaging_baseline_gate_from_github_run()` adds an in-process `gh run download` path for release jobs that want to pull archived baseline artifacts from a specific Actions run before evaluating drift. The installed `resource-hunter-packaging-baseline-gate` entrypoint, `python -m resource_hunter.packaging_gate`, and `python3 scripts/packaging_gate.py` surface the same summary for release jobs and source checkouts, including `--github-run`, `--repo`, `--artifact-name`, `--artifact-pattern`, `--download-dir`, and `--require-artifact-count` when the caller wants the gate to fetch the run artifacts itself. The GitHub Actions workflow now runs both the read-only report and the stricter gate after downloading matrix artifacts, then uploads `resource-hunter-packaging-baseline-report-summary` alongside `resource-hunter-packaging-baseline-gate-summary` so downstream consumers can archive both views from the same run. With `--json`, pre-report failures now emit a `report_type=error` gate payload on stdout so callers can still archive a machine-readable summary when artifact discovery or post-download scanning fails.
- `RESOURCE_HUNTER_PACKAGING_PYTHON=/path/to/python` sets the default packaging interpreter for both commands when `--python` is omitted, and `RESOURCE_HUNTER_PACKAGING_PYTHON=auto` enables the same discovery flow across shared CI/ops entrypoints
- `resource_hunter.packaging_smoke.run_packaging_smoke()` returns the same `packaging_python` provenance fields as the CLI, includes `strategy_family`, and accepts optional source/candidate overrides when interpreter selection happens upstream
- It builds a wheel, installs it with either `venv` or the `pip install --prefix` fallback, then verifies both `python -m resource_hunter` and the generated `resource-hunter` console script
- It exits with code `2` when packaging prerequisites are blocked or when any smoke step fails

## JSON

`search --json` returns:

- `query`
- `intent`
- `plan`
- `results`
- `warnings`
- `source_status`
- `meta`

Each item in `results` includes:

- `channel`
- `source`
- `provider`
- `title`
- `link_or_magnet`
- `password`
- `share_id_or_info_hash`
- `size`
- `seeders`
- `quality`
- `score`
- `reasons`
- `raw`

## Operational notes

- The engine caches recent normalized responses and source health in SQLite
- `sources` shows recent health snapshots; `sources --probe` actively checks sources
- `doctor` reports binaries, cache paths, the resolved checkout root via `project_root` / `packaging.project_root`, root provenance via `project_root_source` / `packaging.project_root_source`, machine-readable packaging blockers/strategy, plus `packaging_python`, `packaging_python_source`, and auto-discovery fields when `auto` is requested so automation can confirm which interpreter was inspected and whether the checkout root was explicit or discovered
- `doctor --require-packaging-ready` exits with code `2` when `packaging.blockers` is non-empty or `full_packaging_smoke_ready` is `false`; add `--bootstrap-build-deps` when bootstrap-capable interpreters should count as packaging-ready for this checkout, and use `--json`, `--python`, `--python auto`, or `RESOURCE_HUNTER_PACKAGING_PYTHON` when the packaging-capable interpreter differs from the current launcher
- `packaging-smoke --json` returns `project_root`, `project_root_source`, `requested_project_root` when `--project-root` is passed, `packaging.project_root`, `packaging.project_root_source`, `packaging.requested_project_root`, `packaging_python`, `packaging_python_source`, the chosen install `strategy` plus stable `strategy_family`, wheel path, console script path, each smoke step, `failed_step` for both preflight blockers (for example `packaging-status` or `packaging-gate`) and later build/install failures, `bootstrapped_build_requirements` / `bootstrap_overlay` when build dependencies were staged, and auto-discovery candidates when `auto` is requested
- `packaging-capture` returns a bundled artifact with top-level `schema_version`, `captured_at`, `requested_project_root`, `project_root`, `project_root_source`, `packaging_python`, `packaging_python_source`, `packaging_python_auto_selected`, `packaging_python_candidates`, `failed_step`, `summary`, `requirements`, and nested `doctor` / `packaging_smoke` payloads so capture jobs can archive the exact raw payloads alongside a small roll-up
- `packaging-baseline` returns a small roll-up JSON with the output directory, the generated blocked interpreter path, per-artifact provenance/status metadata, per-capture `expected_outcome` / `matches_expectation` / `expectation_drift` details, top-level expectation `summary`, human-readable `warnings`, and a machine-readable `requirements` gate block while writing the full passing and blocked capture bundles to disk for archival consumers; `expected_outcome` records the allowed readiness booleans, `failed_step` presence, and `strategy_family` set for each capture, `expectation_drift` includes structured mismatches such as `strategy_mismatch`, and `--require-expected-outcomes` now verifies the expected strategy family as well as the pass/block booleans
- `packaging-baseline-report --json` now includes `report_type=single` for one artifact or `report_type=aggregate` for multi-artifact directory scans, which lets dashboards branch on the shape without guessing from the caller input
- No login, no cookie injection, no DRM bypass

