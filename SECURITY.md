# Security Policy

## Reporting

Please report suspected security issues privately to the repository owner through GitHub Security Advisories or a private contact channel before public disclosure.

## Scope

`resource-hunter` is intentionally limited to public, no-login, no-API-key, no-DRM workflows.

Reports are especially useful for:

- command execution risks around external binaries such as `yt-dlp` and `ffmpeg`
- unsafe URL handling
- cache and local file permission issues
- sensitive data leakage in logs or JSON output
- parser issues caused by hostile upstream payloads

## Support Expectations

Security fixes will target the latest repository state first. Older published skill revisions may not receive backports.
