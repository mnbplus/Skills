# Status

- Date: 2026-03-23
- Task note: fixed the remaining GitHub Actions packaging-test failures on branch `resource-hunter-ci-fix-20260323-1402` after run `23424246775` exposed hosted-toolcache `setuptools`/`distutils` probe drift on Python 3.10/3.11.
- Improvement shipped: the packaging capability probe now falls back to a fresh subprocess when the current interpreter trips the hosted `setuptools._distutils_hack` assertion, so packaging smoke and wheel-install entrypoint tests keep checking real wheel and console-script behavior instead of failing on the probe itself.
- Code changes:
  - `skills/resource-hunter/src/resource_hunter/packaging_smoke.py` now keeps the fast in-process probe for normal cases, but transparently reruns the packaging-module probe in a clean subprocess when `setuptools.build_meta` resolution raises the hosted `distutils` assertion.
  - `skills/resource-hunter/tests/test_packaging.py` now derives wheel-build readiness from `packaging_smoke.packaging_status(...)` instead of a fragile direct `importlib.util.find_spec("setuptools.build_meta")` call, and adds regression coverage for the current-interpreter subprocess fallback.
- Validation:
  - `E:/DevTools/python/python.exe -m pytest tests/test_packaging.py -k 'test_run_packaging_smoke_reports_missing_project_root or test_packaging_status_falls_back_to_subprocess_for_current_python_distutils_assertion or test_resource_hunter_entrypoints_after_wheel_install' -q`
  - `E:/DevTools/python/python.exe -m pytest tests/test_packaging.py -k 'packaging_status or run_packaging_smoke_reports_missing_project_root' -q`
  - `E:/DevTools/python/python.exe -m pytest tests/test_runtime.py -k 'test_packaging_status_' -q`
  - `E:/DevTools/python/Scripts/ruff.exe check src/resource_hunter/packaging_smoke.py tests/test_packaging.py`
- Saturation: the targeted CI root cause is addressed locally; the next bottleneck is pushing the commit and confirming the GitHub-hosted 3.10/3.11 matrix reruns cleanly with the existing packaging report/gate workflow unchanged.
