# GitHub Actions Usage

Lucid's recommended CI path is direct Python script execution after you
checkout or vendor Lucid. Keep the workflow report-only: generate SARIF,
generate a JSON plan, write a concise step summary, and upload artifacts only
when your workflow explicitly opts in.

The examples below check Lucid out under `.lucid-tool/`. If you vendor Lucid in
the target repository, replace `python3 .lucid-tool/lucid.py` with that path.
If the Lucid repository is private, use normal checkout credentials or vendor
the tool in the target repository.
Lucid skips `.lucid-tool/` during scans so the checked-out tool does not become
part of the target repository audit.

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
      - name: Checkout target repository
        uses: actions/checkout@v4

      - name: Checkout Lucid
        uses: actions/checkout@v4
        with:
          repository: dd3ok/lucid
          ref: v0.3.1
          path: .lucid-tool

      - name: Run Lucid audit
        run: |
          mkdir -p .lucid
          python3 .lucid-tool/lucid.py audit --root . --format sarif --out .lucid/audit.sarif
          python3 .lucid-tool/lucid.py plan --root . --format json --out .lucid/plan.json
          python3 .lucid-tool/lucid.py audit --root . --format terminal | tee .lucid/audit.txt

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
    sarif_file: .lucid/audit.sarif

- name: Upload Lucid artifacts
  uses: actions/upload-artifact@v4
  with:
    name: lucid
    path: |
      .lucid/audit.sarif
      .lucid/plan.json
      .lucid/audit.txt
```

## Optional Config

Use `--config` when the target repository keeps Lucid policy in a non-default
config file inside the target root:

```bash
python3 .lucid-tool/lucid.py audit --root . --config .github/lucid.config.json --format sarif --out .lucid/audit.sarif
python3 .lucid-tool/lucid.py plan --root . --config .github/lucid.config.json --format json --out .lucid/plan.json
python3 .lucid-tool/lucid.py audit --root . --config .github/lucid.config.json --format terminal
```

## Experimental Composite Action

The composite action in `action.yml` is experimental and not the primary CI surface.
The recommended CI path is the direct script workflow above. Revisit the wrapper
only if direct-script CI usage proves insufficient.

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
