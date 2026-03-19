# Heartbeat Checks for OpenClaw Config Repair

Use heartbeat for light, cheap health checks. Do not do invasive fixes automatically.

## Lightweight checks
- `openclaw gateway status`
- `openclaw status`
- confirm QQ Bot state stays `OK`
- confirm `~/.openclaw/exec-approvals.json` still has the intended `defaults.ask`
- watch for `config invalid`, `EEXIST`, `symlink`, `gateway aborted`

## Alert conditions
Alert only when one of these happens:
- `openclaw status` exits non-zero
- gateway is unreachable
- QQ Bot state is not `OK`
- approvals default changed away from intended value
- warning count jumps unexpectedly after a config/plugin change

## Do not do automatically in heartbeat
- do not restart gateway automatically
- do not run `plugins update --all`
- do not remove files under `dist-runtime` automatically
- do not rewrite approvals/config automatically unless explicitly requested

## Cadence guidance
- normal: every few hours or via manual heartbeat
- after config/plugin repairs: one extra heartbeat soon after the change
- after a restart: verify once, then return to quiet mode
