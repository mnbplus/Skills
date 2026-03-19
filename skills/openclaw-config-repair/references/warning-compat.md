# Warning compatibility notes

This note is for warnings that look scary during OpenClaw repair, but are not necessarily the active outage.

## `tools.profile (coding) allowlist contains unknown entries ...`

### What it means

The configured tool profile expands to a broader logical allowlist than the current runtime/provider/model actually exposes.

Observed warning forms included:
- `tools.profile (coding) allowlist contains unknown entries (apply_patch, image, image_generate). These entries are shipped core tools but unavailable in the current runtime/provider/model/config.`
- `tools.profile (coding) allowlist contains unknown entries (apply_patch, cron, image, image_generate). These entries are shipped core tools but unavailable in the current runtime/provider/model/config.`

### Why it can happen

Per local docs, `tools.profile: "coding"` includes:
- `group:fs`
- `group:runtime`
- `group:sessions`
- `group:memory`
- `image`

But the active runtime/provider/model may not expose all implied tools at that moment.

Examples:
- `apply_patch` may be gated or unavailable in the current runtime/provider combination
- `image` / `image_generate` may be unavailable because the current runtime has no image-capable tool binding
- `cron` may be unavailable in some session/runtime contexts even if present elsewhere in the installation

### Interpretation rule

Treat this as a **compatibility warning first**, not as proof of config corruption.

Do not escalate it to the primary incident unless at least one of these is also true:
- a user-facing workflow actually depends on the missing tool and is failing because of it
- `openclaw status` or gateway startup is failing alongside the warning
- the warning appeared immediately after a tool-policy edit and correlates with new breakage

### What to do

1. Confirm whether local health is otherwise normal:
   - `openclaw gateway status`
   - `openclaw status`
2. Compare the warning against the current runtime/provider/model context.
3. If there is no matching user-visible failure, record it as non-blocking.
4. Only change tool profile/allow/deny settings if you are solving a real capability mismatch, not just silencing logs.

### What not to do

Do not:
- rewrite `tools.profile` just to remove the warning
- assume the warning caused provider request failures
- restart gateway solely to chase this warning

## Practical conclusion from this repair

In this incident, the warning was present repeatedly, but the user-facing failure pattern was dominated by repeated upstream provider errors on `codex-rokwuky/gpt-5.4` while local OpenClaw health stayed normal.

Conclusion: warning was **secondary / non-blocking**, not the root cause.
