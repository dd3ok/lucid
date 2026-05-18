# Changelog

## Unreleased

### Added

- Skill-first Lucid package under `skills/lucid/`.
- Deterministic `scan`, `audit`, `plan`, and `verify` commands.
- Context hygiene references for memory retention, cleanup actions, source of
  truth, negative residue, compatibility safety, rule taxonomy, and security.
- Behavior fixtures and eval validation for the v0.1 rule taxonomy.
- GitHub Actions validation workflow.
- Public output schema and security policy docs.
- OpenClaw skill metadata and install path documentation.

### Security

- v0.1 is read-only by default and writes generated output only under `.lucid/`.
- Unsafe context findings redact secret-like snippets before report rendering.
