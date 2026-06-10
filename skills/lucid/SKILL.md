---
name: lucid
description: >
  Audits stale, unsafe, contradictory, or bloated agent-facing context and
  produces cleanup plans. Use for prompt debt, obsolete agent instructions,
  memory cleanup, source-of-truth drift, AGENTS.md-style docs, and skill
  descriptions, 프롬프트 부채, and 컨텍스트 정리. Do not use for ordinary
  README edits, general code refactors, linting, summarization, or creating a
  memory bank.
version: 0.4.0
metadata: {"openclaw":{"requires":{"anyBins":["python3","python"]}}}
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

5. Optionally generate a review-only patch suggestion:

   ```bash
   python3 <lucid-skill-dir>/scripts/lucid.py suggest --root . --audit .lucid/audit.json --out .lucid/suggested.patch
   ```

6. Classify every item as one of:

   ```text
   remove
   replace-with-pointer
   move-to-reference
   move-to-validator
   move-to-eval
   keep-with-reason
   manual-review
   ```

7. Do not edit or delete files unless the user explicitly asks to apply the plan.

8. After approved edits, run:

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

Before memory cleanup, old-looking compatibility-field removal, or
negative-warning cleanup, read `references/memory-retention-rubric.md`,
`references/compatibility-safety.md`, or `references/negative-residue.md`,
respectively.
