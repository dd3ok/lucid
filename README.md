# Lucid

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

```bash
mkdir -p ~/.agents/skills
ln -s /path/to/lucid/skills/lucid ~/.agents/skills/lucid
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

## Roadmap

- v0.1: read-only scanner/planner
- v0.2: diff-only patch suggestions
- v0.3: policy packs and stronger source graph
- v1.0: GitHub Action, marketplace packaging, optional MCP integration
