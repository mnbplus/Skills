# Resource Hunter v2 Architecture

## Layout

- `src/resource_hunter/`: installable Python package
- `src/resource_hunter/config.py`: path and environment resolution
- `src/resource_hunter/errors.py`: shared error types
- `src/resource_hunter/intent.py`: intent parsing, alias enrichment, query graphs, source-aware budgets
- `src/resource_hunter/adapters.py`: source adapters and runtime profiles
- `src/resource_hunter/ranking.py`: ranking, validation, evidence fusion, and success-first ordering
- `src/resource_hunter/rendering.py`: text and JSON rendering exports
- `src/resource_hunter/retrieval_layers.py`: layered retrieval model and indexed discovery fallback
- `src/resource_hunter/engine.py`: main search engine
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
4. Expand source-aware query graphs and budgets
5. Route to pan/torrent pipelines
6. Query registered direct sources
7. If no confident result is found, run indexed discovery fallback
8. Normalize all results into `SearchResult`
9. Deduplicate
10. Score, validate, and fuse corroborating evidence
11. Render text output or JSON
12. Cache response and source health

## Retrieval model

### Retrieval layers
- `direct-structured-pan`
  - `2fun`, `dalipan`, `hunhepan`, `pansou.vip`
- `direct-structured-torrent`
  - `nyaa`, `animetosho`, `dmhy`, `eztv`, `tpb`, `torlock`, `yts`, `1337x`
- `community-clue`
  - `tieba`
- `indexed-discovery`
  - `search-index:ddg`, `search-index:bing`, `search-index:brave`
- `authenticated-connector`
  - reserved

### Layer roles
- `direct`: sources intended to produce immediately usable or near-usable structured results
- `clue`: sources intended to produce thread-level or follow-up hints
- `discovery`: search-engine fallback used when direct retrieval does not produce confident matches
- `auth`: reserved for future authenticated connectors

## Source adapter contract

Each adapter implements:

- `search(query, intent, limit, page, http_client) -> list[SearchResult]`
- `healthcheck(http_client) -> (ok, error)`

All adapter outputs must already be normalized into the shared `SearchResult` structure.

## Important release semantics

- `AnimeTosho`, `DMHY`, and most torrent adapters produce direct magnet-ready results
- `Bing` and `Brave` are indexed-discovery fallback providers, not the same stability class as structured direct sources
- `DaliPan` is currently a **structured token-only clue source** in runtime semantics:
  - anonymous search is confirmed via the public search API
  - final anonymous detail/url resolution is still incomplete
  - runtime therefore defaults to `dalipan://provider/eu-token` placeholders and marks them as clue/follow-up results rather than guaranteed final share URLs
  - transport hardening now keeps insecure SSL fallback limited to SSL/certificate-like failures on the public search request
  - optional detail/url follow-up can be attempted without making follow-up success a requirement for preserving search results
- `PanSearch` is now viable as a low-priority structured pan source when queried with `keyword=`:
  - `__NEXT_DATA__` and `_next/data` expose stable result payloads for current live probes
  - content cards can contain embedded canonical share URLs that normalize into direct/actionable results
  - it remains lower priority than proven direct aggregators because card structure may still drift

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

### Important search `meta` fields

- `query_attempts`
- `layer_attempts`
- `query_budgets`
- `source_query_plan`
- `retrieval_layers`
- `best_direct_results`
- `best_actionable_results`
- `best_clues`
- `success_estimate`
- `timings_ms`

### Search result notes

Each `SearchResult` can carry:

- `validation_status`
- `actionability`
- `validation_signals`
- `corroboration_count`
- `supporting_results`
- `raw`

The runtime uses these fields to separate:

- direct matches
- actionable but not fully direct matches
- clue-only results that still require manual follow-up

The preferred generic clue/follow-up fields are:

- `raw.retrieval_role=clue`
- `raw.requires_follow_up=true`
- `raw.delivery` for clue shape classification (`token_only`, `thread_clue`, `indexed_clue`)

This lets ranking and rendering rely on result semantics rather than source-name-only branching.

### Dalipan-specific note

Dalipan results currently preserve follow-up data in `raw`, including:

- `dalipan_id`
- `dalipan_eu`
- `filelist`
- `delivery=token_only`
- `retrieval_role=clue`
- `requires_follow_up=true`
- `dalipan_transport.search=verified|insecure_fallback`
- `dalipan_follow_up.detail_status`
- `dalipan_follow_up.final_url_status`

When optional follow-up is enabled, Dalipan may resolve to a direct resource, but unresolved/auth-gated follow-up must not invalidate the public search batch.

This preserves the main success-first rule:

- public search success must survive follow-up failure or follow-up disablement

PanSearch direct records preserve source-specific context in `raw`, including:

- `pansearch_id`
- `pansearch_pan`
- `pansearch_time`
- `pansearch_card_title`

## Admission and release safety guidance

To keep expansion work reviewable and low-risk, each new source should be evaluated against a fixed admission checklist:

- anonymous/public availability
- stable canonical field or honest clue-only field contract
- success / empty / error-or-drift fixture coverage
- result-local failure isolation
- synchronized updates to planner, retrieval layer metadata, source priority, and compatibility exports

Release success should also be evaluated against **validated direct** results rather than any non-clue direct-looking candidate. This is especially important for same-title different-year trap cases such as `The Merry Widow 1952`.

This makes current behavior explicit to downstream consumers.

## Top level doctor payload

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

## Packaging / installability notes

Packaging, report, gate, and verify flows remain part of the project and are still available, but they are not the focus of the current sync-prep wave. The current sync-prep effort is mainly about making the retrieval/runtime state, source matrix, and release limitations match reality.
