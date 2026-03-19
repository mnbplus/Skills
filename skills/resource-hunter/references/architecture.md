# Resource Hunter v2 Architecture

## Layout

- `scripts/hunt.py`: primary CLI entrypoint
- `scripts/pansou.py`: legacy pan wrapper
- `scripts/torrent.py`: legacy torrent wrapper
- `scripts/video.py`: legacy video wrapper
- `scripts/resource_hunter/models.py`: public data models
- `scripts/resource_hunter/common.py`: parsing, normalization, and filesystem helpers
- `scripts/resource_hunter/cache.py`: SQLite-backed cache and manifest storage
- `scripts/resource_hunter/core.py`: search intent parsing, planning, adapters, scoring, formatting
- `scripts/resource_hunter/video_core.py`: yt-dlp workflow and manifest handling
- `scripts/resource_hunter/cli.py`: unified CLI surface

## Search flow

1. Parse query into `SearchIntent`
2. Build a `SearchPlan`
3. Route to pan/torrent/video pipeline
4. Query source adapters with fallback query variants
5. Normalize all results into `SearchResult`
6. Deduplicate
7. Score and sort
8. Render text output or JSON
9. Cache response and source health

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
