# Resource Hunter

Installable Python package and OpenClaw/ClawHub skill for public pan, torrent, magnet, and public video URL discovery.

## What it does now

`resource-hunter` is currently in a success-first retrieval phase focused on real public-source usefulness inside `skills/resource-hunter`.

### Currently integrated source expansion

#### Structured pan and clue sources
- `2fun`
- `dalipan`
- `hunhepan`
- `pansou.vip`
- `tieba`

#### Structured torrent sources
- `nyaa`
- `animetosho`
- `dmhy`
- `eztv`
- `tpb`
- `torlock`
- `yts`
- `1337x`

#### Indexed discovery fallback
- `search-index:ddg`
- `search-index:bing`
- `search-index:brave`

### Retrieval layers
- `direct-structured-pan`
- `direct-structured-torrent`
- `community-clue`
- `indexed-discovery`
- `authenticated-connector` (reserved)

## Important release notes

- `AnimeTosho`, `DMHY`, `Torlock`, `DaliPan`, `search-index:bing`, and `search-index:brave` are now integrated in the runtime path
- `search-index:bing` and `search-index:brave` are best-effort fallback discovery providers, not the same stability class as structured direct adapters
- `DaliPan` currently exposes **structured clue records** from anonymous search, not guaranteed final share URLs
  - anonymous search is confirmed
  - anonymous detail/url resolution is still incomplete
  - runtime currently emits `dalipan://provider/eu-token` placeholders and marks them as clue/follow-up style output

## Validation snapshot

- `E:/DevTools/python/python.exe -m pytest tests/test_intent.py tests/test_results.py tests/test_precision.py tests/test_source_expansion.py tests/test_cli.py tests/test_runtime.py -q`
  - `95 passed, 1 skipped`
- `E:/DevTools/python/Scripts/ruff.exe check src/resource_hunter/adapters.py src/resource_hunter/intent.py src/resource_hunter/engine.py src/resource_hunter/retrieval_layers.py src/resource_hunter/core.py src/resource_hunter/precision_core.py src/resource_hunter/common.py tests/test_source_expansion.py`
  - `All checks passed!`

## Main entrypoints

- Standard entrypoints: `resource-hunter`, `python -m resource_hunter`
- Source checkout wrappers: `scripts/hunt.py`, `scripts/packaging_report.py`, `scripts/packaging_gate.py`, `scripts/packaging_verify.py`
- Legacy compatibility wrappers: `scripts/pansou.py`, `scripts/torrent.py`, `scripts/video.py`

## Common commands

```bash
python3 scripts/hunt.py search "Oppenheimer 2023" --kind movie --4k
python3 scripts/hunt.py search "Breaking Bad S01E01" --tv
python3 scripts/hunt.py search "进击的巨人 Attack on Titan" --anime --sub
python3 scripts/hunt.py search "周杰伦 无损" --music --quick
python3 scripts/hunt.py search "Adobe Photoshop 2024" --software --json
python3 scripts/hunt.py sources --probe --json
python3 scripts/hunt.py doctor --json
python3 scripts/hunt.py video probe "https://www.bilibili.com/video/BV..."
```

## Search behavior summary

- Movie: pan first, torrents as supplement
- TV: TV-capable torrents first, pan as supplement
- Anime: `nyaa -> animetosho -> dmhy -> torlock` first, pan as supplement
- Music/software/book/general: pan first
- If direct retrieval is weak, indexed discovery may run through DDG/Bing/Brave

## Result semantics

Search results are ranked and validated into practical buckets:

- `direct`
- `actionable`
- `clue`

This distinction matters for current source coverage:

- direct torrent sources often return immediately usable magnet results
- public thread and indexed-discovery sources may return clue-like results
- Dalipan is currently intentionally treated as a clue-style source in release semantics because final anonymous URL resolution is not yet complete

## Current known limits

- Public HTML/RSS sources may throttle, block, or change layout without notice
- Indexed discovery may vary by region or anti-bot behavior
- Same-title different-year film disambiguation is improved but still not perfect
- `The Merry Widow 1952` remains a known hard live case
- `PanSearch` has shown promising real payloads but is not yet integrated because content-card link extraction is still unfinished

## Packaging / installability tooling

Packaging, report, gate, and verify flows remain available for installability and CI workflows, for example:

```bash
python3 scripts/hunt.py doctor --json --require-packaging-ready
python3 scripts/hunt.py packaging-smoke --json
python3 scripts/hunt.py packaging-baseline --project-root /path/to/repo --python auto --bootstrap-build-deps --output-dir artifacts/packaging-baseline --require-expected-outcomes
python3 scripts/hunt.py packaging-baseline-report artifacts/packaging-baseline/packaging-baseline.json
python3 scripts/packaging_gate.py artifacts/downloaded-gh-artifacts --json
python3 scripts/packaging_verify.py --github-run latest --output-dir artifacts/packaging-baseline-gh-verify --require-artifact-count 6
```

## References

- Skill-focused usage: [SKILL.md](./SKILL.md)
- Detailed source matrix: [references/sources.md](./references/sources.md)
- Internal architecture: [references/architecture.md](./references/architecture.md)
- Usage notes: [references/usage.md](./references/usage.md)
