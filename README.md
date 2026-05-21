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

Lucid is distributed from the canonical skill folder `skills/lucid/`.
Runtime-specific installs should symlink or copy that folder; they are not
separate sources of truth.

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

## Quick Start

From a target repository:

```bash
python3 /path/to/lucid/skills/lucid/scripts/lucid.py scan --root . --format terminal
python3 /path/to/lucid/skills/lucid/scripts/lucid.py audit --root . --format terminal
python3 /path/to/lucid/skills/lucid/scripts/lucid.py plan --root . --out .lucid/plan.md
```

Lucid is read-only by default. It writes generated reports and plans only under
`.lucid/`.

Use `--config` with `scan`, `audit`, `plan`, or `verify` to load an explicit
config file inside the target repository.

Use `lucid.ignore.json` at the target repository root to suppress reviewed
false positives by `rule`, `path`, and required `reason`.

## Package

Build a distributable skill archive:

```bash
python3 scripts/package-skill.py
```

The archive is written to `dist/lucid-skill.zip` and contains the canonical
`skills/lucid/` skill contents with repo-level docs, evals, fixtures, generated
outputs, and cache files excluded.
The zip archive has `SKILL.md` at its root so compatible runtimes can install
it as a skill directory.

## Usage

Ask your agent:

```text
Audit this repo for prompt debt and stale agent-facing context.
```

For direct terminal usage, see Quick Start.

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

Release checklist: [docs/release-checklist.md](docs/release-checklist.md)

## Roadmap

See [docs/product-design.md](docs/product-design.md#roadmap) for the detailed
roadmap.

- v0.1: read-only scanner/planner
- v0.2: skill packaging, CLI wrapper, diff-only suggestions, SARIF
- v0.3: policy packs and source graph
- v1.0: stable schemas, GitHub Action productization, marketplace packaging,
  optional adapters

## Status

Lucid v0.1.0 is an initial public alpha. The current package is a read-only
scanner/planner intended for local validation before applying cleanup changes.

## License

MIT. See [LICENSE](LICENSE).
