# Changelog

## Unreleased

### Added

- `scripts/package-skill.py` for building `dist/lucid-skill.zip` from the
  canonical `skills/lucid/` folder.
- Package validation for required skill files and archive safety constraints.

## v0.1.0 - 2026-05-20

### Added

- Skill-first Lucid package under `skills/lucid/`.
- Deterministic `scan`, `audit`, `plan`, and `verify` commands.
- Context hygiene references for memory retention, cleanup actions, source of
  truth, negative residue, compatibility safety, rule taxonomy, and security.
- Behavior fixtures and eval validation for the v0.1 rule taxonomy.
- GitHub Actions validation workflow.
- Public output schema and security policy docs.
- OpenClaw skill metadata and install path documentation.
- Unsafe context scanning now detects secret-like values, private key markers,
  and hidden Unicode inside fenced code blocks.
- Conservative near-duplicate source-of-truth drift detection for repeated
  policy and workflow guidance.
- Stale reference checks now cover high-signal bare filenames such as
  `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `README.md`, `memory.md`, and
  `MEMORY.md`.

### Security

- v0.1 is read-only by default and writes generated output only under `.lucid/`.
- Unsafe context findings redact secret-like and hidden unsafe snippets before
  report rendering.
