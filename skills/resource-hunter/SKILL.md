---
name: resource-hunter
description: Public resource hunter for movies, TV, anime, music, software, books, pan links, magnets, and public video URLs. Uses unified search routing, dual text/JSON output, and yt-dlp video workflows without login, API keys, or DRM bypass.
---

# Resource Hunter

Use this skill when the user wants to:

- Find public pan links, magnets, or torrent results
- Search movies, TV, anime, music, software, or books
- Handle a public video URL with `yt-dlp`
- Get compact chat-ready results or structured JSON

Do not use this skill for:

- Private accounts, cookies, login-only sites, invite-only trackers
- DRM, captchas, bypassing access controls, or restricted content
- Legality guarantees or long-term availability guarantees

## Main entrypoint

```bash
SKILL_ROOT="$(openclaw skills path resource-hunter)"
SKILL_DIR="$SKILL_ROOT/scripts"
python3 "$SKILL_DIR/hunt.py" search "<query>"
```

Legacy entrypoints still work:

```bash
python3 "$SKILL_DIR/pansou.py" "<query>"
python3 "$SKILL_DIR/torrent.py" "<query>"
python3 "$SKILL_DIR/video.py" info "<url>"
```

Standard package entrypoints are also supported after installation:

```bash
python -m resource_hunter search "<query>"
resource-hunter search "<query>"
```

## Default routing

- Movie: pan first, torrent as supplement
- TV: EZTV/TPB first, pan as supplement
- Anime: Nyaa first, pan as supplement
- Music, software, book: pan first
- Public video URL: route to `video probe` / `video info`

## Common commands

```bash
python3 "$SKILL_DIR/hunt.py" search "Oppenheimer 2023" --4k
python3 "$SKILL_DIR/hunt.py" search "Breaking Bad S01E01" --tv
python3 "$SKILL_DIR/hunt.py" search "进击的巨人 Attack on Titan" --anime --sub
python3 "$SKILL_DIR/hunt.py" search "周杰伦 无损" --music
python3 "$SKILL_DIR/hunt.py" search "Adobe Photoshop 2024" --software --channel pan
python3 "$SKILL_DIR/hunt.py" video probe "https://www.bilibili.com/video/BV..."
python3 "$SKILL_DIR/hunt.py" video download "https://youtu.be/..." balanced
python3 "$SKILL_DIR/hunt.py" sources
python3 "$SKILL_DIR/hunt.py" doctor
python3 "$SKILL_DIR/hunt.py" doctor --json --require-packaging-ready
python3 "$SKILL_DIR/hunt.py" doctor --json --python /path/to/python --require-packaging-ready
python3 "$SKILL_DIR/hunt.py" doctor --json --python auto --require-packaging-ready
python3 "$SKILL_DIR/hunt.py" doctor --json --project-root /path/to/repo --python auto --bootstrap-build-deps --require-packaging-ready
python3 "$SKILL_DIR/hunt.py" doctor --json --python auto --bootstrap-build-deps --require-packaging-ready
python3 "$SKILL_DIR/hunt.py" packaging-smoke --json
python3 "$SKILL_DIR/hunt.py" packaging-smoke --json --python /path/to/python
python3 "$SKILL_DIR/hunt.py" packaging-smoke --json --python auto
python3 "$SKILL_DIR/hunt.py" packaging-baseline --project-root /path/to/repo --python auto --bootstrap-build-deps --output-dir artifacts/packaging-baseline --require-expected-outcomes
python3 "$SKILL_DIR/hunt.py" packaging-baseline-report artifacts/packaging-baseline/packaging-baseline.json
python3 "$SKILL_DIR/hunt.py" packaging-baseline-report artifacts/downloaded-gh-artifacts --json --require-contract-ok
python3 "$SKILL_DIR/hunt.py" packaging-baseline-report --github-run latest --require-contract-ok
python3 "$SKILL_DIR/packaging_report.py" --json artifacts/downloaded-gh-artifacts
python3 "$SKILL_DIR/packaging_gate.py" artifacts/downloaded-gh-artifacts --json --require-artifact-count 6
python3 "$SKILL_DIR/packaging_verify.py" --github-run latest --output-dir artifacts/packaging-baseline-gh-verify --require-artifact-count 6
```

## Output modes

- Default: short human-readable recommendations with reasons
- `--json`: stable machine-readable payload with `query`, `intent`, `plan`, `results`, `warnings`, `source_status`, and `meta`; `doctor --json` and `packaging-smoke --json` also surface packaging probe failures under `packaging.error`, the resolved checkout root via `project_root` / `packaging.project_root`, and the root provenance via `project_root_source` / `packaging.project_root_source`

### Packaging probe-error examples

When a requested `--python` path cannot be inspected, both commands keep returning structured JSON. Key on `packaging.error` instead of treating the run as an unstructured crash.

```bash
python3 "$SKILL_DIR/hunt.py" doctor --json --python /bad/path
```

```json
{
  "packaging_python": "/bad/path",
  "packaging_python_source": "argument",
  "packaging": {
    "pip": null,
    "venv": null,
    "setuptools_build_meta": null,
    "wheel": null,
    "console_script_strategy": "blocked",
    "error": "Unable to inspect packaging modules via /bad/path: <launcher error>"
  }
}
```

```bash
python3 "$SKILL_DIR/hunt.py" packaging-smoke --json --python /bad/path
```

```json
{
  "ok": false,
  "strategy": "blocked",
  "reason": "Packaging smoke is blocked: Unable to inspect packaging modules via /bad/path: <launcher error>",
  "packaging_python": "/bad/path",
  "packaging_python_source": "argument",
  "packaging": {
    "error": "Unable to inspect packaging modules via /bad/path: <launcher error>"
  }
}
```

## Notes for agent behavior

- Prefer the main `hunt.py` entrypoint over directly composing lower-level scripts
- Use `--quick` in chat when the user wants a short answer
- Use `--json` when another tool or script will consume the output
- If the user provides a public video URL, do not search pan/torrent first; go straight to the video pipeline
- When validating installability or CI readiness, run `doctor --json --require-packaging-ready` first and then `packaging-smoke --json`; both commands now report `project_root`, `project_root_source`, `packaging.project_root`, `packaging.project_root_source`, `packaging_python`, its source, and any probe failure in `packaging.error`, so add `--python` when the packaging-capable interpreter differs from the current launcher, set `RESOURCE_HUNTER_PACKAGING_PYTHON` once so both commands reuse the same target interpreter, or use `--python auto` / `RESOURCE_HUNTER_PACKAGING_PYTHON=auto` to scan the current interpreter, active envs, PATH, and the Windows `py` launcher for a packaging-ready fallback. Add `--project-root` when CI or ops runs outside the target checkout, and add `--bootstrap-build-deps` when lean runtimes should still count as installable because they can bootstrap the checkout's declared build requirements into a disposable overlay.
- When consuming archived packaging baselines, `packaging-baseline-report` can read one baseline file, multiple explicit files, or a directory tree of downloaded CI artifacts; add `--json` for aggregate machine-readable output and `--require-contract-ok` when downstream automation should fail after printing the report if any archived artifact drifts from the expected passing-vs-blocked contract. `--github-run latest` now resolves the newest completed `resource-hunter-ci` run first, and both report/gate text output mirror the resolved run plus selected-run metadata and resolved artifact paths so ops logs stay readable without `--json`. Use `scripts/packaging_report.py` or the installed `resource-hunter-packaging-baseline-report` entrypoint when the caller wants the report flow without routing through the main CLI. For fixed-size CI matrices, prefer `scripts/packaging_gate.py ... --json --require-artifact-count <N>` so missing artifact uploads fail the gate too; `--json` now also emits a `report_type=error` summary when discovery or post-download scanning fails before a normal gate payload can be built.
- When packaging ops need matched GitHub-run evidence, prefer `resource-hunter packaging-baseline-verify`, `scripts/packaging_verify.py`, or `resource-hunter-packaging-baseline-verify` so the report and gate share one resolved download instead of racing on separate `latest` lookups. `--output-dir` now writes synchronized `report.*`, `gate.*`, `verify.*`, and `bundle-manifest.json`, while `--output-archive <path.zip>` packages those same outputs into one portable bundle for handoff or ops archival. Add `--archive-downloads` when that bundle should also embed the retained downloaded artifact tree under `download/`. Omit `--repo` when you want inferred repo fallback across `GITHUB_REPOSITORY`, git `origin`, and the current `gh` context; that fallback now covers both `--github-run latest` lookup and fixed numeric `--github-run <id>` downloads, with numeric retry history exposed via `download.download_attempts`.
- If the user explicitly wants only pan or only torrent, set `--channel pan` or `--channel torrent`

## References

- Detailed usage: `references/usage.md`
- Internal structure and JSON schema: `references/architecture.md`
- Source coverage and routing: `references/sources.md`
