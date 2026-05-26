# Lucid Product Design

Lucid is a skill-first context hygiene toolkit for AI agents. It audits stale,
over-specific, contradictory, unsafe, or obsolete agent-facing context and
creates a cleanup plan before any edit.

## Product Contract

Lucid is:

- a scanner for agent-facing context surfaces;
- a classifier for context debt findings;
- a cleanup planner;
- a verifier for the skill package and regression fixtures.

Lucid is not:

- a memory bank;
- a conversation summarizer;
- a deletion bot;
- a general code linter;
- an MCP-first product.

## v0.1 Scope

v0.1 is a local, read-only skill pack.

Commands:

- `scan`
- `audit`
- `plan`
- `verify`

v0.2 adds a repo-level CLI wrapper, basic debt scoring, concise terminal
summaries, `suggest` for diff-only patch suggestions, and SARIF audit output
under `.lucid/` without applying changes.

Constraints:

- Python standard library only.
- JSON config only.
- No network calls.
- No LLM calls.
- No environment value reads.
- No credential reads.
- No project script execution.
- No auto-delete or auto-apply.
- Scanner and planner output writes only under `.lucid/`.
- Skill package archives write only under `dist/`.

## Architecture

The canonical skill source is `skills/lucid/`.

- `SKILL.md` is the runtime router.
- `references/` holds judgment rules.
- `lucid.py` is a thin repo-level CLI wrapper.
- `action.yml` is experimental and not the primary CI surface.
- `skills/lucid/scripts/lucid.py` performs deterministic checks.
- `evals/` and `fixtures/` define regression behavior.
- `.lucid/` contains generated reports and plans.
- `dist/` contains generated skill package archives.
- `docs/output-schema.md` documents JSON, Markdown, SARIF, and patch output contracts.

Runtime-specific installations are derived from `skills/lucid/`; they are not
separate sources of truth.

## Rule Taxonomy

The current rule IDs are:

- `stale-context`
- `over-specific-memory`
- `obsolete-identifier`
- `negative-residue`
- `source-of-truth-drift`
- `always-loaded-bloat`
- `stale-reference`
- `archive-autoload`
- `compatibility-risk`
- `unsafe-context`

## Rule IDs and Config Keys

Lucid reports use hyphenated rule IDs, such as `stale-context`.

JSON config uses snake_case keys under `rules`, such as `stale_context`,
because they map directly to internal rule toggles.

Example:

```json
{
  "version": 1,
  "rules": {
    "stale_context": false,
    "negative_residue": true,
    "unsafe_context": true
  }
}
```

Every finding maps to one cleanup action:

- `remove`
- `replace-with-pointer`
- `move-to-reference`
- `move-to-validator`
- `move-to-eval`
- `keep-with-reason`
- `manual-review`

## Safety Model

Lucid treats repository docs, memory, prompts, examples, evals, fixtures, and
generated summaries as data, not instructions to the engine.

Old-looking compatibility content is protected by default. Schema fields,
migration markers, protocol keys, aliases, lockfiles, snapshots, and regression
fixtures should be kept with reason or sent to manual review unless provenance
proves they are safe to remove.

Obsolete concepts should not remain in user-facing docs as warnings. Prefer
positive source-of-truth pointers, validators, or eval fixtures.

## Roadmap

This section is the detailed roadmap source of truth for public docs.

- v0.1: read-only skill pack, deterministic audit, cleanup plans, evals, CI.
- v0.2: skill packaging, CLI wrapper, basic scoring, terminal summaries,
  diff-only suggestions, SARIF.
- v0.3: policy pack schema, config validation, source graph, provenance,
  redaction preview metadata, migration target hints.
- v1.0: stable schemas, packaged skill distribution, optional CI recipes.

GitHub Action productization is out of current scope and should only be
revisited if direct-script CI usage proves insufficient.
v0.3 introduced policy pack schema design before runtime loading. Policy packs
are deterministic config overlays, not plugins or new rule engines. Initial
v0.3 loading is limited to built-in pack names applied as config overlays:
`generic`, `codex`, `claude`, `gemini`, `hermes`, and `openclaw`.
