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
mkdir -p ~/.agents/skills
ln -s /path/to/lucid/skills/lucid ~/.agents/skills/lucid
```

Repo-local skill:

```bash
mkdir -p .agents/skills
ln -s ../../skills/lucid .agents/skills/lucid
```

For Codex-specific audits, enable the built-in policy pack in
`lucid.config.json`:

```json
{"version": 1, "policy_pack": "codex"}
```

Then run `/skills` in Codex and confirm `lucid` appears, or invoke it as
`$lucid`.

### Hermes Agent

Default profile skill:

```bash
mkdir -p ~/.hermes/skills
ln -s /path/to/lucid/skills/lucid ~/.hermes/skills/lucid
```

Named profile skill:

```bash
mkdir -p ~/.hermes/profiles/<profile>/skills
ln -s /path/to/lucid/skills/lucid ~/.hermes/profiles/<profile>/skills/lucid
```

For Hermes-specific audits, enable the built-in policy pack in
`lucid.config.json`:

```json
{"version": 1, "policy_pack": "hermes"}
```

Hermes skill discovery may require a fresh session or gateway restart before
newly installed skills are available; verify discovery in the active
runtime/profile.

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

Native install:

```bash
openclaw skills install /path/to/lucid/skills/lucid --as lucid
openclaw skills check --json
openclaw skills list
```

Managed global skill (use `--global` only if you intentionally want Lucid
available to all OpenClaw workspaces; otherwise prefer a workspace-local
install):

```bash
openclaw skills install /path/to/lucid/skills/lucid --as lucid --global
```

Manual workspace skill:

```bash
mkdir -p /path/to/workspace/skills
ln -s /path/to/lucid/skills/lucid /path/to/workspace/skills/lucid
```

Manual managed local skill:

```bash
mkdir -p ~/.openclaw/skills
ln -s /path/to/lucid/skills/lucid ~/.openclaw/skills/lucid
```

For OpenClaw-specific audits, enable the built-in policy pack in
`lucid.config.json`:

```json
{"version": 1, "policy_pack": "openclaw"}
```

Lucid only scans files whose resolved path remains under `--root`. User/global
skill directories and symlink targets outside the target root are not included
in a repo-root audit; audit those directories separately or vendor/copy the
skill into the scanned tree.

## Quick Start

From a target repository:

The repo-level `lucid.py` wrapper is for cloned repository usage. Packaged or
runtime-installed skills should invoke `<lucid-skill-dir>/scripts/lucid.py`.

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
