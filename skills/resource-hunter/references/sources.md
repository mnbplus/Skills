# Resource Hunter Sources

## Pan sources

- `2fun`
  - Channel: `pan`
  - Priority: `1`
  - Role: primary aggregator
- `hunhepan`
  - Channel: `pan`
  - Priority: `2`
  - Role: fallback pan source
- `pansou.vip`
  - Channel: `pan`
  - Priority: `3`
  - Role: extra fallback pan source

## Torrent sources

- `nyaa`
  - Channel: `torrent`
  - Priority: `1`
  - Best for anime
- `eztv`
  - Channel: `torrent`
  - Priority: `1`
  - Best for TV episodes
- `tpb`
  - Channel: `torrent`
  - Priority: `2`
  - General fallback
- `yts`
  - Channel: `torrent`
  - Priority: `2`
  - Best for movies
- `1337x`
  - Channel: `torrent`
  - Priority: `3`
  - General supplementary source

## Default routing matrix

- Movie: `2fun -> hunhepan -> pansou.vip`, then `yts -> tpb -> 1337x`
- TV: `eztv -> tpb -> 1337x`, then pan sources
- Anime: `nyaa -> tpb -> 1337x`, then pan sources
- Music/software/book/general: pan sources first, torrent sources second
- Public video URL: no pan/torrent search; route directly to video workflow

## Health and circuit breaking

- Every active search stores a `source_status` record
- Repeated recent failures can temporarily open a circuit for that source
- `sources --probe` actively tests current reachability
- `doctor` reports cached recent source state

## Caveats

- External public sources may throttle, change formats, or break without notice
- Coverage quality varies by query and source index freshness
- `pansou.vip` endpoint shape is handled conservatively with fallbacks because the public API is unstable
