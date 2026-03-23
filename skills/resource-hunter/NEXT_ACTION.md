# Next Action

Wire a downstream consumer around the new aggregate baseline-report flow.

- Add a dashboard/release job that downloads the `resource-hunter-packaging-baseline-*` artifacts and runs `resource-hunter packaging-baseline-report <downloaded artifact root> --json --require-contract-ok`.
- If a downstream job still archives standalone `doctor --json` or `packaging-smoke --json` output, pass an explicit `--project-root <requested path>` there as well for provenance consistency.
- Verify the first green GitHub Actions run uploads all three JSON files for every OS+Python matrix cell, and confirm the aggregate report sees all of them from the downloaded artifact tree.
- Keep `yt-dlp` installation deferred unless public video workflow validation becomes the next priority.
