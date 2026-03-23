# Next Action

Land the `packaging-baseline-verify` follow-up, then generate one synced evidence bundle from the latest green CI run.

- Push the follow-up commit on `resource-hunter-ci-fix-20260323-1402` after review.
- Run `python3 scripts/hunt.py packaging-baseline-verify --github-run latest --github-run-list-limit 100 --repo mnbplus/Skills --github-workflow resource-hunter-ci --output-dir <evidence-dir> --output-archive <evidence-zip> --archive-downloads --require-artifact-count 6 --json` against the published branch.
- Review `verify.txt` and `report.txt` first to confirm the grouped failure summaries and bundle manifest line up with the hosted artifact set.
- If verification drifts, use the grouped artifact labels to jump straight to the failing matrix legs and inspect their retained artifacts/logs.
