# Security

Lucid v0.2 is a read-only scanner, planner, reporter, and review-only patch
suggestion tool.

## Allowed

- read files inside the target repo
- write generated reports to `.lucid/`
- write skill package archives to `dist/`
- print terminal output
- emit JSON and Markdown plans
- emit SARIF reports
- emit review-only patch suggestions

## Forbidden

- network requests
- LLM calls
- reading environment variable values
- reading credential stores
- destructive shell commands
- auto-deleting files
- auto-applying patches
- writing generated reports or patch suggestions outside `.lucid/`
- writing skill package archives outside `dist/`
- executing external project scripts
