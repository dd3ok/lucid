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

User skill:

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
ln -s /path/to/lucid/skills/lucid "${CODEX_HOME:-$HOME/.codex}/skills/lucid"
```

Some agent hosts also expose `.agents/skills` as a shared cross-agent skill
path. Treat that as a host convention, not the primary Codex home.

Repository-local skill for a cloned workspace:

```bash
mkdir -p .agents/skills
ln -s ../../skills/lucid .agents/skills/lucid
```

Reusable Codex plugin distribution is separate from this raw skill folder. If
you package Lucid as a Codex plugin, include a manifest at
`<plugin-root>/.codex-plugin/plugin.json` that points at the plugin's
`skills/` directory instead of treating
`dist/lucid-skill.zip` as a plugin archive.

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

### Hermes

```bash
mkdir -p ~/.hermes/skills/productivity
ln -s /path/to/lucid/skills/lucid ~/.hermes/skills/productivity/lucid
```

Reload skills or start a new Hermes session after installing. Prefer a copied
or symlinked skill directory for Lucid's multi-file layout; direct URL installs
are appropriate only for single-file `SKILL.md` skills.

### OpenClaw

Managed agent skill:

```bash
openclaw skills install /path/to/lucid/skills/lucid --agent mozzi --as lucid
openclaw skills info lucid --agent mozzi --json
```

Managed global skill:

```bash
openclaw skills install /path/to/lucid/skills/lucid --global --as lucid
openclaw skills info lucid --json
```

Manual workspace or `~/.openclaw/skills` symlinks also work, but managed
installs make the active `baseDir`, visibility, and requirements easier to
inspect.

## Quick Start

From a target repository:

The repo-level `lucid.py` wrapper is for cloned repository usage. Packaged or
runtime-installed skills should invoke `<lucid-skill-dir>/scripts/lucid.py`.
For OpenClaw managed installs, read `<lucid-skill-dir>` from the `baseDir`
field in `openclaw skills info lucid --agent <agent> --json`.

```bash
python3 /path/to/lucid/lucid.py scan --root . --format terminal
python3 /path/to/lucid/lucid.py audit --root . --format terminal
python3 /path/to/lucid/lucid.py plan --root . --out .lucid/plan.md
python3 /path/to/lucid/lucid.py suggest --root . --out .lucid/suggested.patch
```

Lucid is read-only by default. It writes generated reports, plans, and patch
suggestions only under `.lucid/`.

Use `--config` with `scan`, `audit`, `plan`, `suggest`, or `verify` to load an
explicit config file inside the target repository.

Use `lucid.ignore.json` at the target repository root to suppress reviewed
false positives by `rule`, `path`, and required `reason`.

## CI Reporting

Generate report-only SARIF output for code scanning or CI artifacts:

```bash
python3 /path/to/lucid/lucid.py audit --root . --format sarif --out .lucid/audit.sarif
```

Emit report-only GitHub Actions annotations for inline CI findings:

```bash
python3 /path/to/lucid/lucid.py audit --root . --format github-actions
```

GitHub Actions example: [docs/github-actions.md](docs/github-actions.md)

The recommended CI path is to checkout or vendor Lucid and run the local Python
script directly. Artifact and SARIF uploads remain explicit workflow choices.

## Package

Build a distributable skill archive:

```bash
python3 scripts/package-skill.py
```

The archive is written to `dist/lucid-skill.zip` and contains the canonical
`skills/lucid/` skill contents with repo-level docs, evals, fixtures, generated
outputs, and cache files excluded.
The zip archive has `SKILL.md` at its root. Runtimes that install from a
directory, such as OpenClaw local installs or Hermes multi-file skills, should
extract the archive first and install the extracted directory. Codex plugin
distribution requires plugin metadata and is not represented by this raw skill
archive.

## Usage

Ask your agent:

```text
Audit this repo for prompt debt and stale agent-facing context.
```

For direct terminal usage, see Quick Start.

## Design

- `SKILL.md` is a short router.
- `references/` contains judgment rules.
- `lucid.py` is a thin CLI wrapper.
- `action.yml` is experimental and not the primary CI surface.
- `skills/lucid/scripts/lucid.py` performs deterministic checks.
- `evals/fixtures` prevent regressions.
- `.lucid/plan.md` is generated before any edit.

More detail: [docs/design-rationale.md](docs/design-rationale.md)

Product contract: [docs/product-design.md](docs/product-design.md)

Output schema: [docs/output-schema.md](docs/output-schema.md)

Policy packs: [docs/policy-packs.md](docs/policy-packs.md)

GitHub Actions usage: [docs/github-actions.md](docs/github-actions.md)

Security policy: [SECURITY.md](SECURITY.md)

Release checklist: [docs/release-checklist.md](docs/release-checklist.md)

## Roadmap

See [docs/product-design.md](docs/product-design.md#roadmap) for the detailed
roadmap.

- v0.1: read-only scanner/planner
- v0.2: skill packaging, CLI wrapper, basic scoring, terminal summaries,
  diff-only suggestions, SARIF
- v0.3: policy packs, config validation, source graph, provenance, redaction
  preview metadata, migration target hints
- v1.0: stable schemas, packaged skill distribution, optional CI recipes

## Status

Lucid v0.3.1 is a public alpha. The current package is a read-only context
hygiene scanner, planner, reporter, and review-only patch suggestion tool for
local validation before applying cleanup changes.

## License

MIT. See [LICENSE](LICENSE).
