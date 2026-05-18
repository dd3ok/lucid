# Output Schema

Lucid v0.1 emits JSON for machine-readable commands and Markdown for cleanup
plans. Schemas may evolve before v1.0, but v0.1 fields are intentionally small
and stable enough for local automation.

Rule IDs in reports use hyphen-case, such as `negative-residue`. Config keys
under `rules` use snake_case, such as `negative_residue`.

## Scan Output

Produced by:

```bash
python3 skills/lucid/scripts/lucid.py scan --root . --format json
```

Top-level fields:

| Field | Type | Description |
| --- | --- | --- |
| `version` | string | Lucid tool version; not a separate schema version in v0.1. |
| `root` | string | Absolute target repository root. |
| `files_scanned` | number | Count of discovered context surface files. |
| `files` | array | File metadata records. |

File metadata:

| Field | Type | Description |
| --- | --- | --- |
| `path` | string | Repository-relative path. |
| `category` | string | Surface category, such as `always_loaded`, `skill`, or `docs`. |
| `lines` | number | Line count. |
| `estimated_tokens` | number | Rough character-count token estimate. |
| `bytes` | number | File size in bytes. |

## Audit Output

Produced by:

```bash
python3 skills/lucid/scripts/lucid.py audit --root . --format json
```

Top-level fields:

| Field | Type | Description |
| --- | --- | --- |
| `version` | string | Lucid tool version; not a separate schema version in v0.1. |
| `root` | string | Absolute target repository root. |
| `generated_at` | string | UTC ISO-8601 timestamp. |
| `files_scanned` | number | Count of discovered context surface files. |
| `findings` | array | Finding records. |
| `summary` | object | Aggregated finding counts. |

Summary fields:

| Field | Type | Description |
| --- | --- | --- |
| `total` | number | Total findings. |
| `high` | number | High severity findings. |
| `medium` | number | Medium severity findings. |
| `low` | number | Low severity findings. |
| `manual_review` | number | Findings requiring manual review. |
| `compatibility_protected` | number | `compatibility-risk` findings. |

## Finding

Every audit finding uses this shape:

| Field | Type | Description |
| --- | --- | --- |
| `id` | string | Stable ID within one audit run, such as `LUCID-0001`. |
| `rule` | string | Hyphenated rule ID. |
| `severity` | string | `high`, `medium`, or `low`. |
| `path` | string | Repository-relative path. |
| `line_start` | number | 1-based start line. |
| `line_end` | number | 1-based end line. |
| `snippet` | string | Short excerpt. Unsafe snippets may be redacted. |
| `reason` | string | Why the finding was reported. |
| `suggested_action` | string | One cleanup action from the allowed action set. |
| `replacement_hint` | string or null | Suggested replacement direction, if available. |
| `source_of_truth` | string or null | Canonical source pointer, if known. |
| `confidence` | number | Heuristic confidence between `0` and `1`. |
| `requires_manual_review` | boolean | Whether the item needs manual review. |

Allowed cleanup actions:

- `remove`
- `replace-with-pointer`
- `move-to-reference`
- `move-to-validator`
- `move-to-eval`
- `keep-with-reason`
- `manual-review`

## Plan Markdown

Produced by:

```bash
python3 skills/lucid/scripts/lucid.py plan --root . --out .lucid/plan.md
```

The generated Markdown has this structure:

```text
# Lucid Context Hygiene Plan

## Summary

- Root:
- Files scanned:
- Findings:
- High severity:
- Manual review:
- Compatibility-protected:
- Generated at:

## Recommended Actions

### LUCID-0001 - Finding reason

- Rule:
- Severity:
- Path:
- Lines:
- Current snippet:
- Suggested action:
- Confidence:
- Manual review:
- Replacement hint:
- Source of truth:
- Compatibility note:
- Safety:
```

`Compatibility note` appears only for `compatibility-risk` findings. If there
are no findings, the plan says `No findings.`

`Replacement hint` and `Source of truth` appear only when available.

`plan --audit` accepts audit input only from `.lucid/` inside the target root.
This prevents accidental reads of unrelated local files.

## Verify Output

Produced by:

```bash
python3 skills/lucid/scripts/lucid.py verify --root . --strict
```

Fields:

| Field | Type | Description |
| --- | --- | --- |
| `ok` | boolean | Whether verification passed. |
| `strict` | boolean | Whether strict verification was requested. |
| `errors` | array | Verification error strings. |
| `audit_summary` | object | Same summary object used by audit output. |

## Redaction

Lucid may redact detected `unsafe-context` snippets before JSON or Markdown
rendering. Redaction is conservative and best-effort; it is intended to reduce
accidental echoing of secret-like values, not to replace dedicated secret
scanning.

Examples of redacted values include:

- `sk-...`
- `sk-proj-...`
- `sk_...`
- AWS access key-like literals
- named `api_key`, `token`, `password`, or `secret` assignments
- private key blocks
