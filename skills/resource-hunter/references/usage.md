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
- `doctor` reports binaries, cache paths, and recent source/video state
- No login, no cookie injection, no DRM bypass
