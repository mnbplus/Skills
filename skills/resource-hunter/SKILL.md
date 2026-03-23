---
name: resource-hunter
description: Public resource hunter for movies, TV, anime, music, software, books, pan links, magnets, and public video URLs. Uses layered success-first retrieval, public HTML/RSS/no-API sources, dual text/JSON output, and yt-dlp video workflows without login, API keys, or DRM bypass.
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
- API-key-only search products when a public no-key path is required

## Current retrieval posture

This skill is currently in a success-first source-expansion phase.

### Active runtime sources
- Pan/direct-or-clue: `2fun`, `dalipan`, `hunhepan`, `pansou.vip`, `tieba`
- Torrent/direct: `nyaa`, `animetosho`, `dmhy`, `eztv`, `tpb`, `torlock`, `yts`, `1337x`
- Indexed discovery fallback: `search-index:ddg`, `search-index:bing`, `search-index:brave`

### Retrieval layers
- `direct-structured-pan`
- `direct-structured-torrent`
- `community-clue`
- `indexed-discovery`
- `authenticated-connector` (reserved)

### Important limitations
- `search-index:bing` and `search-index:brave` are best-effort HTML fallback discovery providers
- `dalipan` currently exposes **token-only clue output** from anonymous search; it is not yet a fully direct-ready final-share source in release semantics

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
- TV: TV-capable torrents first, pan as supplement
- Anime: `nyaa -> animetosho -> dmhy -> torlock` first, pan as supplement
- Music, software, book: pan first
- Public video URL: route directly to `video probe` / `video info`
- If direct retrieval is weak, indexed discovery may run through DDG/Bing/Brave

## Common commands

```bash
python3 "$SKILL_DIR/hunt.py" search "Oppenheimer 2023" --4k
python3 "$SKILL_DIR/hunt.py" search "Breaking Bad S01E01" --tv
python3 "$SKILL_DIR/hunt.py" search "进击的巨人 Attack on Titan" --anime --sub
python3 "$SKILL_DIR/hunt.py" search "周杰伦 无损" --music
python3 "$SKILL_DIR/hunt.py" search "Adobe Photoshop 2024" --software --channel pan
python3 "$SKILL_DIR/hunt.py" sources --probe --json
python3 "$SKILL_DIR/hunt.py" doctor --json
python3 "$SKILL_DIR/hunt.py" video probe "https://www.bilibili.com/video/BV..."
python3 "$SKILL_DIR/hunt.py" video download "https://youtu.be/..." balanced
```

## Output modes

- Default: short human-readable recommendations with reasons
- `--json`: stable machine-readable payload with `query`, `intent`, `plan`, `results`, `warnings`, `source_status`, and `meta`

### Current result semantics
- `direct`: intended to be immediately usable
- `actionable`: likely useful, but may still need a small amount of follow-up
- `clue`: structured or community hint that still requires manual follow-up

### Dalipan release note
When the result source is `dalipan`, current runtime output should be interpreted as:

- anonymous-search hit confirmed
- token-only structured clue preserved in JSON/text output
- not guaranteed to already be the final share URL

## Notes for agent behavior

- Prefer the main `hunt.py` entrypoint over directly composing lower-level scripts
- Use `--quick` in chat when the user wants a short answer
- Use `--json` when another tool or script will consume the output
- If the user provides a public video URL, do not search pan/torrent first; go straight to the video pipeline
- If the user explicitly wants only pan or only torrent, set `--channel pan` or `--channel torrent`
- When discussing source support, distinguish:
  - structured direct sources
  - clue/community sources
  - indexed-discovery fallback providers
- Do not oversell Dalipan as a fully direct final-link source in the current release
- Do not oversell Bing/Brave as stable structured providers; they are public HTML discovery fallback only

## Validation snapshot

- Local regression set used for current sync-prep state:
  - `95 passed, 1 skipped`
  - `ruff` all green

## References

- Detailed usage: `references/usage.md`
- Internal structure and JSON schema: `references/architecture.md`
- Source coverage and routing: `references/sources.md`
