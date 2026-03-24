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
python3 scripts/hunt.py search "进击的巨人 Attack on Titan" --anime --sub
python3 scripts/hunt.py search "三体 epub" --book --channel pan
python3 scripts/hunt.py search "周杰伦 无损" --music --quick
python3 scripts/hunt.py search "Adobe Photoshop 2024" --software --json
```

## Current retrieval behavior

- Movie: pan first, torrents as supplement
- TV: TV-capable torrents first, pan as supplement
- Anime: prefer `nyaa -> animetosho -> dmhy -> torlock`, then pan sources
- Music/software/book/general: pan first
- When direct retrieval does not surface a confident result, indexed discovery fallback may run through `search-index:ddg`, `search-index:bing`, and `search-index:brave`

## Important result semantics

- `direct`: intended to be immediately usable
- `actionable`: likely useful but may still need small follow-up
- `clue`: pointer or structured hint that still requires manual follow-up

### Follow-up semantics

The runtime now treats follow-up requirements through shared result semantics instead of source-name-only special cases.

- `raw.retrieval_role=clue` marks a clue-oriented result
- `raw.requires_follow_up=true` marks a result that must not be promoted to direct/actionable just because it carries a password
- `raw.delivery` refines clue delivery shape:
  - `token_only`: token placeholder such as `dalipan://provider/eu-token`
  - `thread_clue`: thread-level clue that requires opening a post/thread
  - `indexed_clue`: search-index clue that requires opening the indexed page

### Dalipan-specific note

Dalipan is currently integrated as a **public anonymous search clue source**.

- Anonymous search is confirmed via the public search API
- Final anonymous `detail/url` resolution is still incomplete
- Runtime currently outputs Dalipan records as `dalipan://provider/eu-token`
- Treat those as structured clue records, not guaranteed final share URLs

### PanSearch-specific note

PanSearch can now be queried through the public search page using `keyword=`.

- `q=` can render an empty result state even when real results exist
- current runtime uses `__NEXT_DATA__` first, with `_next/data` as a fallback
- only embedded canonical share URLs are normalized into runtime results
- if a card has no stable canonical share field, it is skipped instead of padded with weak clue-only output

### Dalipan hardening note

Dalipan follow-up is now treated as an **optional enhancement**, not a hot-path requirement.

- public anonymous search remains the primary supported path
- insecure transport fallback is only attempted for SSL/certificate-like failures on the public search request
- anonymous `detail/url` follow-up can be enabled internally, but auth-gated or unresolved follow-up stays clue-only
- search success is preserved even when detail/url follow-up is disabled or restricted

### Bing / Brave note

`search-index:bing` and `search-index:brave` are best-effort indexed-discovery fallbacks.

- They are useful for recall
- They are not the same stability class as structured direct adapters
- HTML layout, throttling, or regional differences may affect them

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

## Legacy wrappers

These remain available for one compatibility cycle:

```bash
python3 scripts/pansou.py "Oppenheimer 2023" --max 5
python3 scripts/torrent.py "Breaking Bad S01E01" --tv --limit 8
python3 scripts/video.py info "https://youtu.be/..."
```

## Source and health inspection

```bash
python3 scripts/hunt.py sources
python3 scripts/hunt.py sources --probe --json
python3 scripts/hunt.py doctor --json
```

Notes:

- `sources --probe` actively probes registered pan/torrent adapters
- indexed discovery providers are shown through retrieval-layer metadata, but they should still be understood as fallback providers

## Packaging smoke

Packaging/report/gate/verify commands are still supported for installability and CI workflows.

Common examples:

```bash
python3 scripts/hunt.py doctor --json --require-packaging-ready
python3 scripts/hunt.py packaging-smoke --json
python3 scripts/hunt.py packaging-baseline --project-root /path/to/repo --python auto --bootstrap-build-deps --output-dir artifacts/packaging-baseline --require-expected-outcomes
python3 scripts/hunt.py packaging-baseline-report artifacts/packaging-baseline/packaging-baseline.json
python3 scripts/packaging_report.py --json artifacts/downloaded-gh-artifacts
python3 scripts/packaging_gate.py artifacts/downloaded-gh-artifacts --json
python3 scripts/packaging_verify.py --github-run latest --output-dir artifacts/packaging-baseline-gh-verify --require-artifact-count 6
```

## Operational notes

- The engine caches recent normalized responses and source health in SQLite
- Public HTML/RSS sources may throttle, block, or change structure without notice
- Hard cases such as same-title different-year films are improved but not fully solved yet
- `The Merry Widow 1952` remains a known difficult live case

## Source admission checklist

Before a newly probed source should be integrated into runtime, it should satisfy all of the following:

1. **Constraint fit**
   - public and anonymous
   - no login / cookie / private key
   - no official API dependency
2. **Usable output contract**
   - either a stable canonical share/magnet field
   - or an honest clue shape expressed through `raw.retrieval_role`, `raw.requires_follow_up`, and `raw.delivery`
3. **Fixture baseline**
   - at least one success sample
   - one empty/no-result sample when practical
   - one blocked/drift/error sample when practical
4. **Failure isolation**
   - single detail-page / follow-up failure must not fail the whole source batch
5. **Planning registration**
   - source family, budgets, retrieval-layer metadata, and compatibility exports are updated together
6. **Release gate evidence**
   - changed source has a limited live probe
   - docs are updated to reflect actual runtime semantics rather than intended future behavior

## Release gate notes for changed sources

For every changed source before release:

- rerun the focused source/intent/results regression tests
- rerun `ruff check skills/resource-hunter`
- confirm text/JSON output does not overstate `direct` vs `actionable` vs `clue`
- verify `scripts/hunt.py`, `core.py`, and `precision_core.py` compatibility still holds
