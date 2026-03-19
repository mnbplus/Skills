#!/usr/bin/env bash
set -euo pipefail

echo '== gateway =='
openclaw gateway status || exit 10

echo '== status =='
openclaw status || exit 11

echo '== approvals =='
python3 - <<'PY'
import json, pathlib, sys
p = pathlib.Path('/home/maniubi/.openclaw/exec-approvals.json')
if not p.exists():
    print('exec-approvals.json missing')
    sys.exit(12)
obj = json.loads(p.read_text())
ask = obj.get('defaults', {}).get('ask')
print('defaults.ask =', ask)
PY
