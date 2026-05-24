# Policy Packs

Policy packs are deterministic config overlays, not plugins.

They cannot execute code, call networks, call LLMs, read environment values,
read credential stores, or add new rule engines. They only tune existing Lucid
checks for runtime-specific context surfaces and path conventions.

This schema is a design contract for v0.3. It is not loaded by Lucid until
policy pack loading is implemented in a later PR.

## Goals

- Keep `SKILL.md` short.
- Avoid runtime-specific prompt essays.
- Tune existing deterministic checks without changing Lucid's safety model.
- Support Codex, Claude, Gemini, OpenClaw, and generic agent contexts.

## Non-Goals

- No plugin system.
- No executable hooks.
- No LLM judge.
- No network calls.
- No auto-apply.
- No new rule engines.

## Proposed Schema

```json
{
  "version": 1,
  "name": "generic",
  "extends": null,
  "description": "Generic agent-facing context policy overlay.",
  "surfaces": {
    "always_loaded": [
      "AGENTS.md",
      "CLAUDE.md",
      "GEMINI.md",
      "memory.md",
      "MEMORY.md"
    ],
    "skill": [
      "skills/*/SKILL.md",
      "skills/*/references/**/*.md"
    ],
    "docs": [
      "README.md",
      "docs/**/*.md",
      "prompts/**/*.md",
      "templates/**/*.md",
      "examples/**/*.md"
    ]
  },
  "stale_reference": {
    "bare_filenames": [
      "AGENTS.md",
      "CLAUDE.md",
      "GEMINI.md",
      "README.md",
      "SKILL.md",
      "memory.md",
      "MEMORY.md"
    ]
  },
  "runtime_paths": {
    "skill_install_paths": []
  },
  "compatibility": {
    "protected_patterns": []
  },
  "unsafe_context": {
    "platform_specific_hints": []
  }
}
```

## Field Notes

| Field | Purpose |
| --- | --- |
| `version` | Policy schema version. v0.3 starts with `1`. |
| `name` | Pack name such as `generic`, `codex`, `claude`, `gemini`, or `openclaw`. |
| `extends` | Optional base pack name. Runtime packs should usually extend `generic`. |
| `description` | Short human-readable summary. |
| `surfaces` | Context surface globs that tune existing scan categories. |
| `stale_reference.bare_filenames` | Runtime-specific filenames that can be valid bare references. |
| `runtime_paths.skill_install_paths` | Conventional local skill installation paths for the runtime. |
| `compatibility.protected_patterns` | Deterministic patterns that should bias findings toward manual review. |
| `unsafe_context.platform_specific_hints` | Runtime-specific unsafe-context hints without exposing raw secrets. |

## Runtime Pack Examples

`generic` should cover broad agent-facing docs, common memory files, skill
references, prompts, templates, examples, evals, and fixtures.

`codex` may tune AGENTS.md-heavy workflows, `.agents/skills` paths, and
`agents/openai.yaml` metadata awareness.

`claude` may tune `CLAUDE.md`, `.claude/skills` paths, skill references, and
example-heavy skill layouts.

`gemini` may tune `GEMINI.md`, `.gemini/skills` paths, and `.agents/skills`
alias awareness.

`openclaw` may tune workspace `skills/`, `~/.openclaw/skills`, and OpenClaw
metadata constraints.

## Safety Model

Policy packs must preserve Lucid's v0.x constraints:

- no network calls
- no LLM calls
- no environment value reads
- no credential reads
- no project script execution
- no auto-delete
- no auto-apply

Policy packs are overlays for existing deterministic checks. They do not add
runtime-specific prompt essays or executable behavior.

## Implementation Order

1. Schema design.
2. Config schema validation.
3. Policy pack loading.

Config schema validation must land before policy pack loading so unknown keys,
type mismatches, and invalid override shapes fail closed.
