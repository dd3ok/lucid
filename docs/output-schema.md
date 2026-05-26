# Output Schema

Lucid emits JSON for machine-readable commands, Markdown for cleanup plans, and
unified diff text for patch suggestions. Schemas may evolve before v1.0, but
documented fields are intentionally small and stable enough for local
automation.

Rule IDs in reports use hyphen-case, such as `negative-residue`. Config keys
under `rules` use snake_case, such as `negative_residue`.

Commands that load repository config accept `--config` for an explicit config
file inside the target root. When omitted, Lucid uses `lucid.config.json` from
the target root if present.

Config files must be JSON objects with `version: 1`. Lucid fails closed on
unknown top-level keys, unknown rule keys, and type mismatches. This keeps
v0.3 policy work from silently accepting misspelled overlays as policy pack
loading evolves.

Config files may set `policy_pack` to one of Lucid's built-in deterministic
overlays: `generic`, `codex`, `claude`, `gemini`, or `openclaw`. Unknown pack
names fail closed. Policy packs tune existing config only; they do not add
executable hooks or new rule engines.

## Scan Output

Produced by:

```bash
python3 lucid.py scan --root . --format json
```

Top-level fields:

| Field | Type | Description |
| --- | --- | --- |
| `version` | string | Lucid tool version; not a separate schema version before v1.0. |
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
python3 lucid.py audit --root . --format json
```

Top-level fields:

| Field | Type | Description |
| --- | --- | --- |
| `version` | string | Lucid tool version; not a separate schema version before v1.0. |
| `root` | string | Absolute target repository root. |
| `generated_at` | string | UTC ISO-8601 timestamp. |
| `files_scanned` | number | Count of discovered context surface files. |
| `source_graph` | array | Deterministic repo-local reference graph extracted from scanned context surfaces. |
| `findings` | array | Active finding records after suppressions are applied. |
| `suppressed_findings` | array | Findings suppressed by `lucid.ignore.json`, with suppression metadata. |
| `summary` | object | Aggregated finding counts. |

Summary fields:

| Field | Type | Description |
| --- | --- | --- |
| `total` | number | Total active findings after suppressions are applied. |
| `high` | number | High severity findings. |
| `medium` | number | Medium severity findings. |
| `low` | number | Low severity findings. |
| `manual_review` | number | Findings requiring manual review. |
| `compatibility_protected` | number | `compatibility-risk` findings. |
| `suppressed` | number | Findings suppressed by `lucid.ignore.json`. |
| `debt_score` | number | Sum of active finding `score_impact` values. |
| `suppressed_debt_score` | number | Sum of suppressed finding `score_impact` values. |

Debt scores are deterministic informational metrics for comparison and
reporting. They do not fail `verify`, apply changes, or drive deletion.
Current finding weights are intentionally simple: `high` = 10, `medium` = 5,
`low` = 2, with +3 for manual-review findings. `compatibility-risk` findings
are capped at 3 because compatibility-protected content is not automatic
cleanup debt.

Terminal audit output includes a concise single-line summary before detailed
findings:

```text
Summary: active=1 debt=13 high=1 medium=0 low=0 manual_review=1 compatibility_protected=0 suppressed=0 suppressed_debt=0
```

The line mirrors audit `summary` fields and contains summary metrics only:
counts plus debt score totals. It is informational, does not change exit codes,
and is emitted only for terminal audit output, not JSON, SARIF, plan, or patch
artifacts.

## Source Graph

Audit JSON includes `source_graph`, a best-effort deterministic graph of
repo-local references found in scanned context surfaces. It records Markdown
links, inline code paths, and source-of-truth style bare filename references
that resolve to existing files inside the target root.

Source graph entries are informational evidence only. They do not create
findings, change scores, run semantic analysis, call networks, or infer
canonical truth.

Top-level node fields:

| Field | Type | Description |
| --- | --- | --- |
| `path` | string | Repository-relative source file path. |
| `references` | array | Repo-local references found in that source file. |

Reference fields:

| Field | Type | Description |
| --- | --- | --- |
| `target` | string | Repository-relative referenced file path after safe resolution. |
| `line` | number | 1-based source line where the reference appeared. |
| `kind` | string | `markdown-link`, `inline-code`, or `reference-intent`. |

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
| `score_impact` | number | Deterministic contribution to summary `debt_score`. |
| `requires_manual_review` | boolean | Whether the item needs manual review. |
| `provenance` | object | Optional deterministic evidence signals for why the finding was reported. |
| `redaction_preview` | object | Optional safe redaction metadata for `unsafe-context` findings. |
| `migration_hint` | object | Manual-only target hint for moving, replacing, keeping, or reviewing the finding. |
| `suppression` | object | Present only in `suppressed_findings`; includes the matched ignore entry. |

Allowed cleanup actions:

- `remove`
- `replace-with-pointer`
- `move-to-reference`
- `move-to-validator`
- `move-to-eval`
- `keep-with-reason`
- `manual-review`

## Provenance

Finding `provenance` records deterministic evidence, not model reasoning. It is
optional and rule-specific. Current provenance covers `stale-reference` and
`source-of-truth-drift` and `compatibility-risk` findings.

Provenance fields:

| Field | Type | Description |
| --- | --- | --- |
| `deterministic` | boolean | Always `true` for Lucid-generated provenance. |
| `signals` | array | Rule-local evidence records. |

`stale-reference` signal fields:

| Field | Type | Description |
| --- | --- | --- |
| `kind` | string | Signal kind, currently `missing-reference`. |
| `candidate` | string | Referenced local path that did not resolve. |
| `line` | number | 1-based source line where the candidate appeared. |

`source-of-truth-drift` declaration conflict signal fields:

| Field | Type | Description |
| --- | --- | --- |
| `kind` | string | Signal kind, currently `source-of-truth-declaration-conflict`. |
| `key` | string | Conflicting declaration key, such as `canonical workflow`. |
| `value` | string | Value found on the current finding line. |
| `compared_values_count` | number | Count of distinct conflicting values for the key. |

`source-of-truth-drift` near-duplicate signal fields:

| Field | Type | Description |
| --- | --- | --- |
| `kind` | string | Signal kind, currently `near-duplicate-policy-block`. |
| `matched_path` | string | Repository-relative path of the matched duplicate block. |
| `matched_line_start` | number | 1-based start line of the matched block. |
| `matched_line_end` | number | 1-based end line of the matched block. |
| `similarity` | number | Deterministic similarity score that triggered the finding. |

`compatibility-risk` signal fields:

| Field | Type | Description |
| --- | --- | --- |
| `kind` | string | Signal kind, currently `compatibility-protected-pattern`. |
| `pattern` | string | Configured compatibility-protected pattern that matched the finding line. |
| `line` | number | 1-based source line where the protected pattern appeared. |

## Migration Hints

`migration_hint` is advisory metadata derived from `suggested_action`. It does
not create, move, delete, or modify files. All migration hints are manual-only
and are intended to make cleanup plans easier to review.

Migration hint fields:

| Field | Type | Description |
| --- | --- | --- |
| `target_kind` | string | Target category such as `reference`, `validator`, `eval`, `pointer`, `keep-with-reason`, `manual-review`, or `removal`. |
| `target_area` | string | General destination area, not an exact generated path. |
| `reason` | string | Why this target category matches the finding action. |
| `manual_only` | boolean | Always `true`; Lucid does not auto-apply migrations. |

## Ignore Suppressions

When a reviewed finding should remain intentionally, place `lucid.ignore.json`
at the target repository root:

```json
{
  "version": 1,
  "suppressions": [
    {
      "rule": "stale-context",
      "path": "AGENTS.md",
      "reason": "Known duplicate retained for compatibility guidance."
    }
  ]
}
```

Suppressions match exact `rule` and repository-relative `path` values from audit
findings. `reason` is required so ignored context debt remains accountable.
Suppressed findings are removed from active `findings` and plan actions, counted
under `summary.suppressed`, and exposed in `suppressed_findings`.
`plan --audit` trusts the provided audit payload; `lucid.ignore.json` applies
when Lucid generates the audit payload.

## SARIF Output

Produced by:

```bash
python3 lucid.py audit --root . --format sarif --out .lucid/audit.sarif
```

SARIF output uses version `2.1.0` and is intended for report-only CI and code
scanning integrations. It maps active audit findings to
`runs[0].results[]`; suppressed findings are not emitted as SARIF results. The
run properties include the same summary object used by audit JSON.

SARIF results intentionally omit finding snippets. Use audit JSON or a plan
artifact when human review needs the excerpt context.

Result mapping:

| Lucid field | SARIF field |
| --- | --- |
| `rule` | `ruleId` |
| `severity` | `level` (`high` -> `error`, `medium` -> `warning`, `low` -> `note`) |
| `reason` | `message.text` |
| `path` | `locations[0].physicalLocation.artifactLocation.uri` |
| `line_start` | `locations[0].physicalLocation.region.startLine` |
| `line_end` | `locations[0].physicalLocation.region.endLine` |
| `id` | `properties.lucid_id` |
| `suggested_action` | `properties.suggested_action` |
| `score_impact` | `properties.score_impact` |

## Plan Markdown

Produced by:

```bash
python3 lucid.py plan --root . --out .lucid/plan.md
```

Markdown is the default plan format. It can also be selected explicitly with
`--format markdown`.

The generated Markdown has this structure:

```text
# Lucid Context Hygiene Plan

## Summary

- Root:
- Files scanned:
- Findings:
- Debt score:
- Suppressed debt score:
- High severity:
- Manual review:
- Compatibility-protected:
- Suppressed:
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
- Score impact:
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

For `plan --audit`, Lucid uses the provided `.lucid/` audit payload. `--config`
only applies when `plan` generates its own audit.

## Plan JSON

Produced by:

```bash
python3 lucid.py plan --root . --format json --out .lucid/plan.json
```

When `--out` is omitted, JSON plans are written to `.lucid/plan.json`.

Top-level fields:

| Field | Type | Description |
| --- | --- | --- |
| `format` | string | Plan format marker, currently `lucid-plan-json`. |
| `version` | string | Lucid tool version copied from the audit payload. |
| `root` | string | Absolute target repository root. |
| `generated_at` | string | UTC ISO-8601 timestamp from the audit payload. |
| `files_scanned` | number | Count of discovered context surface files. |
| `summary` | object | Same summary object used by audit output. |
| `suppressed_findings` | array | Suppressed finding records copied from the audit payload. |
| `recommended_actions` | array | Machine-readable cleanup plan actions. |

Recommended action fields:

| Field | Type | Description |
| --- | --- | --- |
| `id` | string | Finding ID copied from the audit payload. |
| `rule` | string | Hyphenated rule ID. |
| `severity` | string | `high`, `medium`, or `low`. |
| `path` | string | Repository-relative path. |
| `line_start` | number | 1-based start line. |
| `line_end` | number | 1-based end line. |
| `current_snippet` | string | Short excerpt. Unsafe snippets remain redacted. |
| `reason` | string | Why the finding was reported. |
| `suggested_action` | string | One cleanup action from the allowed action set. |
| `confidence` | number | Heuristic confidence between `0` and `1`. |
| `score_impact` | number | Finding contribution to summary `debt_score`. |
| `requires_manual_review` | boolean | Whether the item needs manual review. |
| `replacement_hint` | string or null | Suggested replacement direction, if available. |
| `source_of_truth` | string or null | Canonical source pointer, if known. |
| `migration_hint` | object | Manual-only target hint copied from the audit finding. |
| `safety` | string | Non-destructive handling note. |
| `compatibility_note` | object | Present only for `compatibility-risk` findings. |

## Suggest Patch

Produced by:

```bash
python3 lucid.py suggest --root . --out .lucid/suggested.patch
```

When `--out` is omitted, patch suggestions are written to
`.lucid/suggested.patch`.

`suggest` emits unified diff text only. It does not apply the patch or modify
target files. The first implementation only includes low-risk `remove` actions
that do not require manual review; other findings remain in the plan for human
review.

`suggest --audit` accepts audit input only from `.lucid/` inside the target
root, matching `plan --audit`.

## Verify Output

Produced by:

```bash
python3 lucid.py verify --root . --strict
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

`unsafe-context` findings may include `redaction_preview` metadata. This
metadata describes redaction status only; it must not include raw values,
prefixes, suffixes, exact secret lengths, samples, or surrounding context.

`redaction_preview` fields:

| Field | Type | Description |
| --- | --- | --- |
| `detected_kinds` | array | Stable labels for detected unsafe content kinds, such as `named-secret-assignment`. |
| `redaction_applied` | boolean | Whether Lucid redacted the reported snippet. |
| `raw_value_exposed` | boolean | Whether a raw secret-like value is exposed by Lucid output; expected to be `false` for redacted secret-like findings. |

Examples of redacted values include:

- `sk-...`
- `sk-proj-...`
- `sk_...`
- AWS access key-like literals
- named `api_key`, `token`, `password`, or `secret` assignments
- private key blocks
- hidden Unicode markers such as zero-width characters
