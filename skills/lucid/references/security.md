# Security

Lucid v0.1 is a scanner and planner.

## Allowed

- read files inside the target repo
- write generated reports to `.lucid/`
- print terminal output
- emit JSON and Markdown plans

## Forbidden

- network requests
- LLM calls
- reading environment variable values
- reading credential stores
- destructive shell commands
- auto-deleting files
- auto-applying patches
- writing outside `.lucid/`
- executing external project scripts

