---
name: openclaw-config-repair
description: Diagnose and repair OpenClaw local config/runtime problems. Use when approvals keep prompting despite config, gateway is up but `openclaw status` or other CLI commands fail, `dist-runtime` symlink EEXIST errors appear, plugin install metadata drifts, Control UI/model requests intermittently fail while local health looks normal, or config edits/restarts leave OpenClaw in a half-broken state.
---

# OpenClaw Config Repair

Repair OpenClaw in a disciplined order. Treat gateway health, CLI health, config validity, exec approvals, and upstream provider failures as separate layers.

## Use this skill when

- `tools.exec.ask` says `off` but exec still asks for approval
- `openclaw gateway status` works but `openclaw status` fails
- CLI errors mention `dist-runtime`, `symlink`, or `EEXIST`
- plugin install metadata drifts or `@latest` keeps triggering warnings
- Control UI reports `An error occurred while processing your request` while local gateway/runtime look healthy
- a config edit or restart leaves OpenClaw in a weird half-working state

## Boundaries

This skill is for **local OpenClaw config/runtime repair**.

Use other skills instead when the problem is primarily:
- host hardening / exposure / firewall / update posture → `healthcheck`
- device pairing / remote app connection / Tailscale / public URL → `node-connect`
- creating or restructuring a skill itself → `skill-creator`

## Core rules

- Prefer the smallest fix that restores observability.
- Do not restart after every tweak. First restore a valid config and a working `openclaw status`.
- Re-read files after editing; exact-text edits can leave duplicated fragments.
- When a behavior mismatch involves approvals, check approvals files before assuming `openclaw.json` is authoritative.
- Use `trash`/reversible cleanup if available; if not, remove the narrowest conflicting runtime artifact first.
- Distinguish **local breakage** from **upstream/provider failures** before editing config.

## Workflow

### 1) Read the live config first

Read:
- `~/.openclaw/openclaw.json`
- any nearby alternate or backup configs that may confuse debugging, such as `openclaw_clean.json`

If the issue appeared after edits, inspect the edited region directly before touching anything else.

### 2) Separate runtime health from CLI/config health

Run, in this order:
- `openclaw gateway status`
- `openclaw status`

Interpret them separately:
- gateway can be healthy while CLI/config is broken
- a successful gateway probe does **not** prove config or runtime-artifact health
- if both pass, the remaining issue may be in Control UI, provider routing, or the selected model

### 3) Approval mismatch checklist

If approvals still prompt even when config says `tools.exec.ask = off`, inspect:
- `~/.openclaw/exec-approvals.json`
- `openclaw approvals get --gateway --json`

Important: exec approvals are controlled by a separate approvals system. The effective default may be:

```json
"defaults": {
  "ask": "always"
}
```

That can override what you expected from `openclaw.json`.

### 4) Repair approvals with the real schema

Do not invent an approvals schema.

Rules:
- preserve the real top-level structure from `exec-approvals.json`
- change only the minimum field needed, usually `defaults.ask`
- `allowlist` entries are objects, not plain strings
- validate with `openclaw approvals get --gateway --json` after applying

### 5) If CLI fails with `dist-runtime` symlink `EEXIST`

Inspect the exact conflicting path first.

If the symlink is valid but rebuild logic is failing on recreation:
1. remove only the conflicting file first
2. rerun `openclaw status`
3. only broaden cleanup if the next conflict appears

Do **not** wipe all of `dist-runtime` first unless the narrow fix fails.

### 6) Config editing discipline

After any manual edit:
1. reread the modified region
2. run `openclaw status`
3. only restart if config parses and status works, or if restart is specifically needed

Watch for:
- duplicated trailing blocks
- broken JSON/JSON5 after replacements
- edits that look successful but were written back by another process

### 7) Plugin metadata drift and stale specs

Use:
- `openclaw plugins update --all`
- then re-check `openclaw status`

If drift clears but `@latest` warnings remain:
- inspect `plugins.installs` in `openclaw.json`
- pin the spec explicitly to the installed version
- verify with another `openclaw status`

### 8) Warning compatibility triage

If you see warnings such as:
- `tools.profile (coding) allowlist contains unknown entries ...`

check whether they are merely compatibility noise or part of the real outage.

Rule:
- if `openclaw gateway status` and `openclaw status` are healthy, and the user-visible failure is elsewhere, treat these warnings as secondary until proven otherwise
- do not rewrite tool policy just to silence logs
- only escalate when a missing tool is directly breaking the required workflow

See:
- `references/warning-compat.md`

### 9) Provider / Control UI failure triage

If the UI shows:
- `An error occurred while processing your request`
- a request id from the upstream model provider
- repeated failures only on one model/provider

then check local health **before** editing config:
- `openclaw gateway status`
- `openclaw status`
- current log tail in `/tmp/openclaw/openclaw-YYYY-MM-DD.log`
- grep for the request id, `embedded_run_agent_end`, `provider`, `responses`, `compaction`

Interpretation rule:
- if gateway/status are healthy and logs show `embedded_run_agent_end` with provider/model-specific request ids, treat it as **upstream/provider instability first**, not local config corruption
- if failures occur across multiple providers/models and are accompanied by config/runtime errors, continue local repair flow

## Heartbeat / periodic checks

Use heartbeat for **lightweight detection**, not automatic risky repair.

### What heartbeat should check

Keep checks read-only unless a repair is explicitly safe and narrowly scoped.

Recommended checks:
- `openclaw gateway status`
- `openclaw status`
- the latest `/tmp/openclaw/openclaw-*.log` for fresh `Config invalid`, `EEXIST`, `Gateway aborted`, `embedded_run_agent_end`, and repeated provider request failures
- `~/.openclaw/exec-approvals.json` effective default, especially `defaults.ask`
- warning bursts such as repeated `tools.profile (coding) allowlist contains unknown entries ...`
- QQ Bot / channel readiness if that channel matters to the deployment

### Alert conditions

Heartbeat should notify when any of these appear:
- `openclaw gateway status` fails
- `openclaw status` fails
- approvals drift back to `defaults.ask != off` when the intended state is off
- new `Config invalid` / `JSON5 parse failed` / `Gateway aborted: config is invalid`
- fresh `dist-runtime` / `symlink` / `EEXIST` failures
- repeated provider errors clustered in a short time window for the same model/provider
- warning volume changes sharply compared with normal baseline

### Silent conditions

Heartbeat should stay quiet when:
- gateway and status both pass
- approvals state matches intent
- there are no new blocking config/runtime errors
- only known non-fatal warnings recur at baseline volume
- provider had a single transient upstream failure with no local degradation

### Heartbeat vs cron

Use heartbeat when:
- checks can be batched together
- slight timing drift is acceptable
- you want to reuse recent session context
- you only need to detect and report

Use cron when:
- exact timing matters
- a one-shot reminder or maintenance window is required
- the check should run in isolation
- you want a dedicated message/report independent of the main session

### Do not auto-do these from heartbeat

Heartbeat should **not** automatically:
- run `openclaw plugins update --all`
- restart gateway/runtime just because of one failed check
- delete `dist-runtime` broadly
- rewrite approvals/config files without fresh confirmation of the exact cause
- switch provider/model automatically in a production setup unless the human explicitly asked for failover behavior

### Suggested heartbeat reference

If you need a checklist, read:
- `references/heartbeat-checks.md`

## Lessons captured from a real repair

### Approval prompts despite config

Root cause:
- `~/.openclaw/exec-approvals.json`

Problem:
```json
"defaults": {
  "ask": "always"
}
```

Repair:
```json
"defaults": {
  "ask": "off"
}
```

### `openclaw status` failing while gateway worked

Root cause:
- `dist-runtime/extensions/acpx/skills/acp-router/SKILL.md`

The symlink itself was valid. The failure came from rebuild logic hitting `EEXIST` while trying to recreate it. Removing the conflicting symlink restored `openclaw status`.

### Provider-side request failures can mimic local breakage

Observed pattern:
- local gateway healthy
- local status healthy
- logs show `embedded_run_agent_end`
- error contains upstream request ids from `codex-rokwuky/gpt-5.4`

Lesson:
- do not keep editing local config when the evidence points to provider instability
- capture request ids and separate provider incidents from local repair work

### Restart timing lesson

Bad pattern:
- edit config
- restart immediately
- lose observability and stack new errors

Better pattern:
1. fix config
2. confirm config parses
3. restore `openclaw status`
4. restart only after the repair chain is stable

## Good end-state checklist

- `openclaw gateway status` succeeds
- `openclaw status` succeeds
- effective approvals match intent
- `openclaw.json` parses cleanly
- no blocking `dist-runtime` symlink conflict remains
- plugin install metadata is coherent
- heartbeat checks are defined and limited to safe read-only detection by default
- provider failures are documented separately from local config faults

## References

If you need official wording or schema clues, read:
- `references/docs-map.md`
- `references/heartbeat-checks.md`
- `references/provider-failures.md`
- `references/warning-compat.md`
