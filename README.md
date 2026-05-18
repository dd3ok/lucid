# Lucid

[![validate](https://github.com/dd3ok/lucid/actions/workflows/validate.yml/badge.svg)](https://github.com/dd3ok/lucid/actions/workflows/validate.yml)

Skill-first context hygiene toolkit for AI agents.

Lucid helps agents audit and plan cleanup for stale, over-specific,
contradictory, unsafe, or obsolete agent-facing context.

## Why

Agents do not need more memory by default. They need cleaner, smaller, current,
source-of-truth aligned context.

## What Lucid Is Not

- Not a memory bank
- Not a conversation summarizer
- Not a deletion bot
- Not a general documentation writer
- Not a code refactoring tool

## Install

Lucid is distributed from the canonical skill folder:

`skills/lucid/`

### Codex

```bash
mkdir -p ~/.agents/skills
ln -s /path/to/lucid/skills/lucid ~/.agents/skills/lucid
```

### Claude Code

```bash
mkdir -p ~/.claude/skills
ln -s /path/to/lucid/skills/lucid ~/.claude/skills/lucid
```

### Gemini CLI

User skill:

```bash
mkdir -p ~/.gemini/skills
ln -s /path/to/lucid/skills/lucid ~/.gemini/skills/lucid
```

Cross-agent alias:

```bash
mkdir -p ~/.agents/skills
ln -s /path/to/lucid/skills/lucid ~/.agents/skills/lucid
```

### OpenClaw

Workspace skill:

```bash
mkdir -p /path/to/workspace/skills
ln -s /path/to/lucid/skills/lucid /path/to/workspace/skills/lucid
```

Managed local skill:

```bash
mkdir -p ~/.openclaw/skills
ln -s /path/to/lucid/skills/lucid ~/.openclaw/skills/lucid
```

## Usage

Ask your agent:

```text
Audit this repo for prompt debt and stale agent-facing context.
```

Or run the bundled script directly:

```bash
python3 skills/lucid/scripts/lucid.py scan --root . --format terminal
python3 skills/lucid/scripts/lucid.py audit --root . --format terminal
python3 skills/lucid/scripts/lucid.py plan --root . --out .lucid/plan.md
python3 skills/lucid/scripts/lucid.py verify --root . --strict
```

## Design

- `SKILL.md` is a short router.
- `references/` contains judgment rules.
- `skills/lucid/scripts/lucid.py` performs deterministic checks.
- `evals/fixtures` prevent regressions.
- `.lucid/plan.md` is generated before any edit.

More detail: [docs/design-rationale.md](docs/design-rationale.md)

Product contract: [docs/product-design.md](docs/product-design.md)

Output schema: [docs/output-schema.md](docs/output-schema.md)

Security policy: [SECURITY.md](SECURITY.md)

## Roadmap

See [docs/product-design.md](docs/product-design.md#roadmap) for the detailed
roadmap.

- v0.1: read-only scanner/planner
- v0.2: CLI wrapper and diff-only suggestions
- v0.3: policy packs and source graph
- v1.0: stable packaging and optional adapters

## Status

Lucid is in v0.1 draft development. The current package is a read-only
scanner/planner intended for local validation before public release.
