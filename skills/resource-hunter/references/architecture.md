# Resource Hunter v2 Architecture

## Layout

- `src/resource_hunter/`: installable Python package
- `src/resource_hunter/config.py`: path and environment resolution
- `src/resource_hunter/errors.py`: shared error types
- `src/resource_hunter/intent.py`: intent parsing and alias resolution exports
- `src/resource_hunter/adapters.py`: source adapter exports
- `src/resource_hunter/ranking.py`: ranking and dedupe exports
- `src/resource_hunter/rendering.py`: text and JSON rendering exports
- `src/resource_hunter/engine.py`: engine export
- `src/resource_hunter/precision_core.py`: compatibility implementation layer for the current v2 core
- `src/resource_hunter/video_core.py`: yt-dlp workflow and manifest handling
- `src/resource_hunter/cli.py`: unified CLI surface
- `scripts/hunt.py`: primary legacy CLI wrapper
- `scripts/pansou.py`: legacy pan wrapper
- `scripts/torrent.py`: legacy torrent wrapper
- `scripts/video.py`: legacy video wrapper

## Search flow

1. Parse query into `SearchIntent`
2. Resolve aliases for movie-like Chinese queries when applicable
3. Build a `SearchPlan`
4. Route to pan/torrent/video pipeline
5. Query source adapters with fallback query variants
6. Normalize all results into `SearchResult`
7. Deduplicate
8. Score and sort
9. Render text output or JSON
10. Cache response and source health

## Source adapter contract

Each adapter implements:

- `search(query, intent, limit, page, http_client) -> list[SearchResult]`
- `healthcheck(http_client) -> (ok, error)`

All adapter outputs must already be normalized into the shared `SearchResult` structure.

## Cache

SQLite database stores:

- `search_cache`: short-TTL normalized responses
- `source_status`: rolling source health results and circuit-breaker input
- `video_manifest`: recent download artifacts

The circuit breaker skips sources that have failed repeatedly in the recent cooldown window.

## JSON schema

Top level search payload:

```json
{
  "query": "...",
  "intent": {},
  "plan": {},
  "results": [],
  "warnings": [],
  "source_status": [],
  "meta": {}
}
```

Top level video payload:

```json
{
  "url": "...",
  "platform": "...",
  "title": "...",
  "duration": 0,
  "formats": [],
  "recommended": [],
  "artifacts": [],
  "meta": {}
}
```

Top level doctor payload:

```json
{
  "version": "...",
  "python": "...",
  "packaging_python": "...",
  "packaging_python_source": "current",
  "packaging_python_candidates": [],
  "packaging_python_auto_selected": false,
  "stdout_encoding": "...",
  "cache_db": "...",
  "storage_root": "...",
  "project_root": "...",
  "project_root_source": "discovered",
  "binaries": {},
  "packaging": {
    "project_root": "...",
    "project_root_source": "discovered",
    "pip": true,
    "venv": true,
    "setuptools_build_meta": true,
    "wheel": true,
    "wheel_build_ready": true,
    "python_module_smoke_ready": true,
    "console_script_smoke_ready": true,
    "full_packaging_smoke_ready": true,
    "blockers": [],
    "optional_gaps": [],
    "console_script_strategy": "venv"
  },
  "recent_sources": {},
  "recent_manifests": [],
  "advice": []
}
```

`packaging_python` records which interpreter `doctor` inspected for packaging readiness, while `packaging_python_source` reports whether it came from `--python`, `RESOURCE_HUNTER_PACKAGING_PYTHON`, `auto` discovery, or the current launcher. The top-level `project_root` and nested `packaging.project_root` always record the resolved checkout root that those packaging checks targeted, even when the caller omits `--project-root` and discovery falls back to the current working tree. `project_root_source` mirrors that decision path with `argument` for an explicit `--project-root` / API `project_root=` input and `discovered` when the command had to walk upward from the current working directory. When the caller explicitly passes `--project-root`, the payload also records that original path via top-level `requested_project_root` plus `packaging.requested_project_root`, which lets downstream consumers distinguish the requested workspace from the resolved checkout root after the upward walk. When `auto` is requested, `packaging_python_candidates` records each discovered interpreter plus its packaging status and `packaging_python_auto_selected` tells consumers whether discovery actually found a packaging-ready target. `wheel_build_ready` is `true` only when `pip`, `wheel`, and `setuptools.build_meta` are importable, matching the current `python -m pip wheel --no-build-isolation` smoke path. `blockers` lists whichever of those required modules are still missing. `console_script_smoke_ready` follows the same contract, while `console_script_strategy` makes the chosen path explicit: `venv` when stdlib `venv` is available, `prefix-install` when `venv` is the only gap, and `blocked` when required packaging modules are still missing. `optional_gaps` currently records the missing `venv` helper without treating it as a hard blocker.

`doctor --require-packaging-ready` turns that contract into a gate: it still prints the normal text or JSON payload, then exits with code `2` whenever `blockers` is non-empty or `full_packaging_smoke_ready` is `false`. When `--bootstrap-build-deps` is present, doctor augments the packaging payload with `bootstrap_build_deps_ready`, `bootstrap_build_requirements`, `bootstrap_console_script_strategy`, and `packaging_smoke_ready_with_bootstrap`, then treats that bootstrap-capable path as acceptable for both auto-selection and gate evaluation. `doctor --project-root` lets that bootstrap feasibility check target a checkout outside the current working directory, and the same explicit root now feeds `auto` interpreter discovery. When `auto` was requested and no candidate is ready, the gate failure message explicitly calls out the discovery miss before reporting fallback blockers.

`packaging-smoke` executes the runtime contract behind that gate. It auto-discovers the checkout root by walking upward for `pyproject.toml` plus `src/resource_hunter`, builds a wheel with `python -m pip wheel --no-build-isolation`, installs it via either an isolated `venv` or a `pip install --prefix` fallback when `venv` is the only missing helper, and then checks both `python -m resource_hunter` and the generated `resource-hunter` console script. When `--bootstrap-build-deps` is enabled and the selected interpreter has `pip` but is missing only `setuptools.build_meta` and/or `wheel`, the command first stages the declared `build-system.requires` entries into a temporary `pip install --target` overlay and then reuses that overlay for the wheel-build step. Auto-selection now reuses the same bootstrap feasibility metadata, so `--python auto --bootstrap-build-deps` can land on the first bootstrap-capable interpreter instead of falling back to the current launcher, and an explicit `--project-root` is forwarded into that discovery step so out-of-tree ops runs evaluate the intended checkout. Its JSON payload records the resolved `project_root`, records `project_root_source` to show whether that root came from an explicit argument or discovery, records `requested_project_root` when the caller passed an explicit root, mirrors those values under `packaging.project_root`, `packaging.project_root_source`, and `packaging.requested_project_root`, records `packaging_python`, `packaging_python_source`, the chosen strategy, wheel path, console script path, every subprocess step, `bootstrapped_build_requirements` / `bootstrap_overlay` when the overlay path is used, and `failed_step` when the smoke run stops early. When `auto` is requested, that payload also carries the discovered candidate list so ops logs can show why discovery succeeded or stayed blocked, and direct Python callers can preserve the same provenance by passing source/candidate overrides into `resource_hunter.packaging_smoke.run_packaging_smoke()`.

`packaging-capture` is the archival wrapper around those two flows. It first builds the normal `doctor` payload, then reuses `doctor.packaging_python`, `doctor.packaging_python_source`, `doctor.packaging_python_auto_selected`, and `doctor.packaging_python_candidates` when it invokes `packaging-smoke`, which keeps the combined artifact tied to one interpreter-selection decision. The bundled JSON adds top-level `schema_version`, `captured_at`, `requested_project_root`, `project_root`, `project_root_source`, `packaging_python`, `packaging_python_source`, `packaging_python_auto_selected`, `packaging_python_candidates`, `failed_step`, `summary`, and `requirements`, while preserving the full raw `doctor` and `packaging_smoke` payloads under those nested keys. `summary.doctor_packaging_ready` mirrors the `doctor --require-packaging-ready` gate evaluation for the same arguments, `summary.packaging_smoke_ok` mirrors the nested smoke `ok` flag, and `summary.strategy` / `summary.strategy_family` / `summary.reason` surface the smoke result without forcing downstream jobs to inspect the nested payload first. The `requirements` block records whether `--require-packaging-ready` and/or `--require-smoke-ok` were requested for this capture, whether those requested gates passed overall, and the exact failure messages that also reach stderr. The command always emits JSON, can optionally duplicate that JSON to `--output`, and still defaults to success once capture completes so CI / ops jobs can archive both passing and intentionally blocked baselines. For jobs that want the bundled artifact and a failing process status, `--require-packaging-ready` and `--require-smoke-ok` now return exit code `2` after the JSON is emitted whenever the nested doctor or smoke expectations are not met. `packaging-baseline` sits one level above that wrapper: it runs `packaging-capture` twice, once with the requested or auto-selected interpreter and once with an intentionally missing interpreter path, then writes the paired raw bundles plus a lightweight `packaging-baseline.json` index so local baseline refreshes do not need ad-hoc shell orchestration. That index now mirrors each capture's provenance plus `summary.doctor_packaging_ready`, `summary.packaging_smoke_ok`, `summary.strategy`, `summary.strategy_family`, `summary.reason`, and `failed_step`, adds per-capture `expected_outcome`, `matches_expectation`, and machine-readable `expectation_drift` entries so archived views can surface both the contract and any drift without re-opening the nested bundles, adds a top-level expectation summary (`passing_capture_matches_expectation`, `blocked_capture_matches_expectation`, `baseline_contract_ok`) together with human-readable `warnings`, and carries a baseline-level `requirements` block that records whether `--require-expected-outcomes` was requested, whether it passed overall, and the exact failure strings emitted on stderr when the expected passing/blocked contrast drifts. `expected_outcome` records the same rules the gate applies (`doctor_packaging_ready`, `packaging_smoke_ok`, whether `failed_step` should be present, and the allowed `strategy_family` values), while `expectation_drift` emits structured mismatch records keyed by field, including `strategy_mismatch` whenever the observed smoke route leaves the allowed strategy family. The expectation gate now checks `strategy_family=usable` for the passing capture and `strategy_family=blocked` plus `failed_step` for the intentionally blocked capture, while preserving the raw `strategy` for concrete route diagnostics. `packaging-baseline-report` is the lightweight consumer for that index: it now accepts one archived roll-up, multiple explicit baseline paths, or directories that are scanned recursively for `packaging-baseline.json` so downloaded matrix-artifact trees can be consumed without extra shell orchestration. Single-artifact input still emits the normalized `artifact_path` + `captures` envelope, while multi-artifact input emits `report_type=aggregate` with top-level contract counters, prefixed warnings, nested per-artifact reports, and `artifacts_with_contract_drift` / `artifacts_with_requirement_failures` lists for downstream dashboards. `--require-contract-ok` adds a read-only gate on top of the report flow and returns exit code `2` after printing when any archived artifact shows packaging-baseline contract drift. That same single-artifact normalization is also available as a Python API via `resource_hunter.packaging_report`, so shared tooling can import the reader/builder instead of shelling out or hardcoding `passing_capture` / `blocked_capture` parsing.
