# OpenClaw Config Repair References

Read these only when needed.

## Approvals and exec behavior
- `/home/maniubi/openclaw/docs/cli/approvals.md`
- `/home/maniubi/openclaw/docs/tools/exec-approvals.md`
- `/home/maniubi/openclaw/docs/web/control-ui.md`
- `/home/maniubi/openclaw/docs/gateway/sandbox-vs-tool-policy-vs-elevated.md`

## Config and gateway
- `/home/maniubi/openclaw/docs/gateway/configuration-reference.md`
- `/home/maniubi/openclaw/docs/cli/gateway.md`
- `/home/maniubi/openclaw/docs/cli/status.md`

## When to read what
- If approval prompts do not match `openclaw.json`, read the approvals docs first.
- If gateway is healthy but CLI commands fail, read status/gateway docs and inspect `dist-runtime` conflicts.
- If a config field seems ignored, compare configuration reference vs approvals/tool-policy docs before editing.
