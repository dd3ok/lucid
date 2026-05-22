# GitHub Actions Usage

Lucid can run in GitHub Actions through its composite action wrapper or directly
without a dedicated wrapper action. Keep the workflow report-only: generate
SARIF, generate a JSON plan, write a concise step summary, and upload artifacts
only when your workflow explicitly opts in.

For direct command workflows, this guide assumes the target repository has
`lucid.py` at its root or vendors Lucid at a known path. If Lucid lives
elsewhere, replace `python3 lucid.py` with that path.

## Composite Action Wrapper

Use the wrapper when the workflow can reference this repository as an action.
The action runs Lucid from the action checkout, writes reports under `.lucid/`,
suppresses report body stdout in the workflow log, and does not upload SARIF or
artifacts by itself.
The `root` input is constrained so the root must stay inside `GITHUB_WORKSPACE`.

```yaml
name: lucid

on:
  pull_request:
  workflow_dispatch:

permissions:
  contents: read

jobs:
  lucid:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run Lucid
        id: lucid
        uses: dd3ok/lucid@main
        with:
          root: .
```

For production workflows, pin the action reference to a release tag or
full-length commit SHA according to your organization's policy.

The wrapper exposes generated paths as action outputs: `sarif`, `plan-json`,
and `terminal-audit`.

## Minimal Report-Only Workflow

```yaml
name: lucid

on:
  pull_request:
  workflow_dispatch:

permissions:
  contents: read

jobs:
  lucid:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run Lucid audit
        run: |
          mkdir -p .lucid
          python3 lucid.py audit --root . --format sarif --out .lucid/audit.sarif
          python3 lucid.py plan --root . --format json --out .lucid/plan.json
          python3 lucid.py audit --root . --format terminal | tee .lucid/audit.txt

      - name: Write Lucid summary
        run: |
          {
            echo "## Lucid"
            grep '^Summary:' .lucid/audit.txt || true
            echo ""
            echo "- SARIF: .lucid/audit.sarif"
            echo "- Plan JSON: .lucid/plan.json"
          } >> "$GITHUB_STEP_SUMMARY"
```

## Optional Uploads

Upload SARIF and Lucid artifacts only when the repository explicitly wants those
GitHub-side integrations:

For production workflows, consider pinning third-party actions such as
`actions/checkout`, `github/codeql-action/upload-sarif`, and
`actions/upload-artifact` to full-length commit SHAs according to your
organization's GitHub Actions policy.

```yaml
# Add at workflow or job level if uploading SARIF:
permissions:
  contents: read
  security-events: write
```

```yaml
- name: Upload SARIF
  uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: ${{ steps.lucid.outputs.sarif }}

- name: Upload Lucid artifacts
  uses: actions/upload-artifact@v4
  with:
    name: lucid
    path: |
      ${{ steps.lucid.outputs.sarif }}
      ${{ steps.lucid.outputs['plan-json'] }}
      ${{ steps.lucid.outputs['terminal-audit'] }}
```

## Optional Config

Use `--config` when the target repository keeps Lucid policy in a non-default
config file inside the target root:

```bash
python3 lucid.py audit --root . --config .github/lucid.config.json --format sarif --out .lucid/audit.sarif
python3 lucid.py plan --root . --config .github/lucid.config.json --format json --out .lucid/plan.json
python3 lucid.py audit --root . --config .github/lucid.config.json --format terminal
```

## Safety Notes

- Lucid does not apply patches, delete files, run project scripts, call LLMs,
  read environment values, or read credential stores.
- Generated reports and patch suggestions stay under `.lucid/`.
- SARIF reports intentionally omit snippets. Use `.lucid/plan.json` or terminal
  output for human review context.
- `lucid.ignore.json` suppressions remove reviewed findings from active SARIF
  results while preserving suppressed counts in summaries.
- Artifact upload and SARIF upload are GitHub workflow choices, not Lucid
  runtime behavior.
