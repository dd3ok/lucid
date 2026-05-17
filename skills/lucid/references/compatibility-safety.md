# Compatibility Safety

Do not remove old-looking content if it may be required for compatibility.

## Protect

- schema fields
- migration markers
- API aliases
- protocol compatibility keys
- legacy aliases used by integrations
- fixture data intentionally containing old names
- tests that prevent regression
- generated lockfiles or snapshots unless explicitly in scope

## Default action

Use `keep-with-reason` or `manual-review` when compatibility is plausible.

## Required plan note

Every compatibility-sensitive finding must explain:

- why it looks stale;
- why it may still be required;
- what evidence is needed before removal.

