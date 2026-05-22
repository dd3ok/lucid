# Design Rationale

Lucid is built as a skill-first repository because agent-facing context cleanup
depends on progressive disclosure.

The always-loaded entry point should stay short. Detailed judgment belongs in
references, deterministic checks belong in scripts, and regression examples
belong in eval fixtures.

## Core Choices

- `skills/lucid/SKILL.md` is the canonical workflow entry point.
- `skills/lucid/references/` holds retention, cleanup, safety, and taxonomy
  criteria.
- `skills/lucid/scripts/lucid.py` provides read-only scanning, auditing,
  planning, reporting, review-only patch suggestions, and verification.
- `evals/behavior-cases` and `fixtures` define behavior before implementation
  changes.
- `.lucid/` is the generated report and plan directory.
- `dist/` is used only for explicit skill package archives.

## v0.x Boundaries

Lucid v0.x is intentionally conservative. It does not call networks, call LLMs,
read environment variable values, read credential stores, execute project
scripts, delete files, apply patches, or write generated reports or patch
suggestions outside `.lucid/`.

JSON config is used because the Python standard library can parse JSON without
an extra dependency.

## Product Principle

Lucid should reduce context debt instead of creating new prompt debt. Old names
and past mistakes should be enforced through validators or evals, not repeated
as durable user-facing warnings.
