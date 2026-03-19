# Provider / Control UI failure pattern

Use this note when OpenClaw *looks* broken from the UI, but local health checks are green.

## Pattern seen in this repair

Local state was healthy:
- `openclaw gateway status` succeeded
- `openclaw status` succeeded
- approvals were still `defaults.ask = off`

But logs showed repeated upstream failures from the embedded agent path:
- event: `embedded_run_agent_end`
- provider: `codex-rokwuky`
- model: `gpt-5.4`
- error: `An error occurred while processing your request...`

Observed request ids included:
- `6b4dd565-ae8d-44a8-a6dd-e7cb3bf5f653`
- `6b96bc56-456c-4303-8f25-c8b56c8fb9ea`
- `9e71dd85-ebb3-44d0-9612-79d655a5971a`
- `52d89564-639b-40c3-9313-4bbb6682f263`
- `05014c37-6665-4a3d-823d-690e09e8c81a`

There was also a related compaction failure with its own upstream request id:
- `fd5211f0-05b3-4d83-a424-6c71e73eaa85`

## Interpretation

When this pattern appears:
- do **not** assume local config corruption
- do **not** restart immediately just because the UI shows a generic error
- treat the first layer as provider instability unless local health checks disagree

## Quick triage

1. Run:
   - `openclaw gateway status`
   - `openclaw status`
2. Tail the latest log:
   - `/tmp/openclaw/openclaw-YYYY-MM-DD.log`
3. Search for:
   - request id
   - `embedded_run_agent_end`
   - `provider`
   - `responses`
   - `compaction`
4. If the same provider/model appears across multiple failures while local checks stay green, classify it as upstream/provider-side

## What to report

Report briefly:
- local OpenClaw health is normal
- failing provider/model pair
- clustered request ids proving repeated upstream failure
- whether compaction/summarization also failed from the same upstream chain

## What not to do automatically

Do not automatically:
- rewrite `openclaw.json`
- change approvals
- delete runtime artifacts
- restart gateway after a single provider error
