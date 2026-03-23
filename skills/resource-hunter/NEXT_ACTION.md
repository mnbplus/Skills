# Next Action

Push the CI probe-fallback fix and rerun the hosted matrix.

- Push the new commit on `resource-hunter-ci-fix-20260323-1402` so GitHub Actions reruns the existing workflow against the hosted Python 3.10 and 3.11 jobs that failed in run `23424246775`.
- Watch the `test` matrix plus the existing packaging baseline report and gate jobs to confirm the probe no longer trips on hosted `setuptools._distutils_hack` behavior.
- If any hosted job still fails, capture the exact failing matrix cell and compare its installed `setuptools`/`pip` versions before changing the packaging workflow contract.
- Keep the aggregate packaging report/gate flow unchanged unless a new post-push run shows a separate regression.
