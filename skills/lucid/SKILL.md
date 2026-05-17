---
name: lucid
description: >
  Audit and plan cleanup for agent-facing context debt: stale instructions,
  over-specific memory, obsolete identifiers, negative residue,
  source-of-truth drift, always-loaded bloat, stale references, compatibility
  risks, and unsafe context across AGENTS.md, CLAUDE.md, GEMINI.md, memory
  files, identity files, SKILL.md, references, docs, prompts, templates,
  examples, evals, and fixtures. Use for context hygiene, prompt debt,
  memory cleanup, old instructions, 과거 잔재, 오래된 지침, 프롬프트 부채,
  컨텍스트 정리. Do not use for ordinary README edits, general code
  refactors, normal linting, summarization, or creating a memory bank.
version: 0.1.0
---

# Lucid

Lucid audits agent-facing context debt and creates a cleanup plan.

Use the bundled script for objective checks. Do not rely on chat memory alone
to decide what is safe to remove.

## Workflow

1. Resolve this skill directory.
2. Run scan from the target repository root:

   ```bash
   python3 <lucid-skill-dir>/scripts/lucid.py scan --root . --format json
   ```

3. Run audit:

   ```bash
   python3 <lucid-skill-dir>/scripts/lucid.py audit --root . --format json --out .lucid/audit.json
   ```

4. Create a cleanup plan:

   ```bash
   python3 <lucid-skill-dir>/scripts/lucid.py plan --root . --audit .lucid/audit.json --out .lucid/plan.md
   ```

5. Classify every item as one of:

   ```text
   remove
   replace-with-pointer
   move-to-reference
   move-to-validator
   move-to-eval
   keep-with-reason
   manual-review
   ```

6. Do not edit or delete files unless the user explicitly asks to apply the plan.

7. After approved edits, run:

   ```bash
   python3 <lucid-skill-dir>/scripts/lucid.py verify --root . --strict
   ```

## Safety

Lucid is read-only by default.

Do not delete tracked files wholesale. Do not remove schema, migration, alias,
marker, protocol, or compatibility fields just because they look old.

Do not preserve obsolete names in user-facing context merely to forbid them.
Prefer source-of-truth pointers, validators, or evals over natural-language
warnings.

Read `references/memory-retention-rubric.md` before recommending memory changes.
Read `references/compatibility-safety.md` before recommending removal of old-looking fields.
Read `references/negative-residue.md` before handling negative warnings.

