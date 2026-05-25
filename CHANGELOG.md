# Changelog

## Unreleased

### Added

- Initial v0.3 policy pack schema design, documenting deterministic config
  overlays for runtime-specific context surfaces and path conventions.
- Fail-closed schema validation for `lucid.config.json` and explicit
  `--config` files.
- Built-in policy pack loading through `policy_pack` config overlays.
- Audit JSON `source_graph` output for deterministic repo-local references
  found in scanned context surfaces.
- Deterministic `provenance` signals for `stale-reference` findings.

## v0.2.2 - 2026-05-23

### Added

- GitHub Actions guide now documents action repository access requirements for
  private Lucid checkouts.

### Changed

- Shortened the Lucid skill frontmatter description to keep skill discovery
  lightweight while preserving context hygiene matching terms.
- De-scoped the composite GitHub Action wrapper as experimental and clarified
  that official CI usage is direct Python script execution after checking out
  or vendoring Lucid.
- Skipped `.lucid-tool/` during scans and restored minimal safety validation
  for the experimental action metadata.

## v0.2.1 - 2026-05-23

### Added

- GitHub Actions usage guide for report-only SARIF, JSON plan, step summary,
  and artifact upload workflows.
- Report-only GitHub composite action wrapper for SARIF, JSON plan, and step
  summary generation.
- GitHub Action wrapper root boundary guard and output-based upload examples.

## v0.2.0 - 2026-05-22

### Added

- `scripts/package-skill.py` for building `dist/lucid-skill.zip` from the
  canonical `skills/lucid/` folder.
- Package validation for required skill files and archive safety constraints.
- Repo-level `lucid.py` CLI wrapper for cloned repository usage.
- Explicit `--config` support for `scan`, `audit`, `plan`, `suggest`, and
  `verify` with target-root path constraints.
- JSON plan output via `plan --format json`.
- `lucid.ignore.json` suppressions with required review reasons.
- Diff-only patch suggestions via `suggest`.
- SARIF 2.1.0 report-only output via `audit --format sarif`.
- Deterministic debt scoring with `score_impact`, `debt_score`, and
  `suppressed_debt_score`.
- Concise terminal audit summary line.

### Security

- Scanner reports, planner reports, SARIF reports, and patch suggestions remain
  constrained to `.lucid/`.
- Skill package archives remain constrained to `dist/`.
- SARIF reports omit snippets.
- Lucid continues to avoid auto-apply, auto-delete, network calls, LLM calls,
  environment value reads, credential reads, and project script execution.

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
