# Security Policy

Lucid v0.1 is a read-only scanner and planner for agent-facing context.

## Supported Versions

Lucid is currently in v0.1 draft development. Security fixes target the latest
`main` branch until stable releases begin.

## Security Model

Lucid must not:

- call networks
- call LLMs
- read environment values
- read credential stores
- execute project scripts
- auto-apply patches
- auto-delete files
- write outside `.lucid/`

Generated reports may include short snippets. Unsafe snippets are redacted
before JSON or Markdown rendering when Lucid detects secret-like or hidden
unsafe content.

Redaction is best-effort and only applies to values Lucid detects as
`unsafe-context` findings. Lucid is not a replacement for dedicated secret
scanning. If a real credential appears in source files or generated reports,
rotate it.

## Reporting Security Issues

Please report security issues through GitHub private vulnerability reporting if
available. If private reporting is unavailable, open a minimal public issue that
does not include secrets, credentials, exploit payloads, or sensitive data.

Do not paste real credentials into issues, pull requests, fixtures, or evals.
