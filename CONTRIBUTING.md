# Contributing

This repository is a multi-skill monorepo. Scope changes tightly to the skill you are modifying.

For `resource-hunter` changes:

1. Install the skill package in editable mode: `python -m pip install -e ./skills/resource-hunter[dev]`
2. Run `ruff check ./skills/resource-hunter`
3. Run `pytest ./skills/resource-hunter/tests`
4. Keep legacy script entrypoints under `skills/resource-hunter/scripts/` working
5. Keep public JSON fields additive-only unless a breaking change is explicitly approved

When changing search behavior, add or update regression coverage for:

- `Breaking Bad S01E01`
- `Oppenheimer 2023`
- `赤橙黄绿青蓝紫 1982`

