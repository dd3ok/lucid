# Security Policy

Lucid v0.3 is a read-only scanner, planner, reporter, and review-only patch
suggestion tool for agent-facing context.

## Supported Versions

Lucid v0.3.x is a public alpha. Security fixes target the latest v0.3.x release
and the `main` branch.

## Security Model

Lucid must not:

- call networks
- call LLMs
- read environment values
- read credential stores
- execute project scripts
- auto-apply patches
- auto-delete files
- write scanner/planner reports, SARIF reports, or patch suggestions outside `.lucid/`
- write skill package archives outside `dist/`

The experimental GitHub composite action wrapper is not the primary CI path.
When used, it only wraps local Lucid commands and may write GitHub
runner-provided `GITHUB_OUTPUT` or `GITHUB_STEP_SUMMARY` files. The Lucid Python
runtime still does not read repository environment values, secrets, or
credential stores.

Generated JSON and Markdown reports may include short snippets. Unsafe snippets
are redacted before JSON or Markdown rendering when Lucid detects secret-like
or hidden unsafe content. SARIF reports omit snippets.

Redaction is best-effort and only applies to values Lucid detects as
`unsafe-context` findings. Lucid is not a replacement for dedicated secret
scanning. If a real credential appears in source files or generated reports,
rotate it.

## Reporting Security Issues

Please report security issues through GitHub private vulnerability reporting if
available. If private reporting is unavailable, open a minimal public issue that
does not include secrets, credentials, exploit payloads, or sensitive data.

Do not paste real credentials into issues, pull requests, fixtures, or evals.
