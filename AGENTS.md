# AGENTS.md

## Purpose

This repo builds Lucid, a skill-first context hygiene toolkit for agent-facing
systems.

Lucid audits stale, over-specific, contradictory, unsafe, or obsolete context
and creates a cleanup plan before any edit.

## Source of Truth

- Skill workflow: `skills/lucid/SKILL.md`
- Context surfaces: `skills/lucid/references/context-surfaces.md`
- Memory retention: `skills/lucid/references/memory-retention-rubric.md`
- Cleanup actions: `skills/lucid/references/cleanup-actions.md`
- Negative residue: `skills/lucid/references/negative-residue.md`
- Compatibility safety: `skills/lucid/references/compatibility-safety.md`
- Rule taxonomy: `skills/lucid/references/rule-taxonomy.md`
- Security model: `skills/lucid/references/security.md`
- Product contract and roadmap: `docs/product-design.md`
- Script behavior: `skills/lucid/scripts/lucid.py`

## Rules

- Keep always-loaded context short.
- Do not encode one-off incidents as durable project rules.
- Do not expose obsolete identifiers in user-facing docs except fixtures/evals.
- Prefer validator/eval enforcement over natural-language warnings.
- Lucid scripts are read-only by default.
- Do not add auto-apply behavior in v0.x.
- Do not add network, LLM, env-read, credential-read, or destructive behavior.

## Validation

```bash
python3 scripts/validate-skill.py
python3 scripts/validate-no-dangerous-io.py
python3 scripts/validate-evals.py
python3 scripts/validate-package-skill.py
python3 skills/lucid/scripts/lucid.py verify --root . --strict
```
