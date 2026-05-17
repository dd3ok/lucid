# Source of Truth

Lucid prefers one canonical policy location.

## Rules

- Do not duplicate full policies across always-loaded files.
- Replace duplicate policy blocks with pointers.
- Prefer current positive instructions over old negative warnings.
- Do not use chat history as source of truth.
- Do not copy long reference material into always-loaded files or `SKILL.md`.

## Preferred order

1. Explicit project config
2. Current skill `SKILL.md`
3. Dedicated reference file
4. Current README section
5. Tests / evals / fixtures
6. Recent chat history only as weak evidence

