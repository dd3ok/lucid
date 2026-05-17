# Rule Taxonomy

## stale-context

- Signals: outdated wording, old/current mismatch, dated process claims.
- Default action: `manual-review`
- False-positive risk: medium
- Allowed example location: fixtures/evals

## over-specific-memory

- Signals: one-off dates, temporary details, single-session notes.
- Default action: `manual-review`
- False-positive risk: medium
- Allowed example location: fixtures/evals

## obsolete-identifier

- Signals: configured denylist terms or old identifier shapes in user-facing context.
- Default action: `move-to-validator`
- False-positive risk: medium
- Allowed example location: fixtures/evals

## negative-residue

- Signals: negative instruction plus old or deprecated concept.
- Default action: `replace-with-pointer`
- False-positive risk: low
- Allowed example location: fixtures/evals

## source-of-truth-drift

- Signals: duplicate canonical policy keys with conflicting values.
- Default action: `replace-with-pointer`
- False-positive risk: high
- Allowed example location: fixtures/evals

## always-loaded-bloat

- Signals: high line count in always-loaded instruction surfaces.
- Default action: `move-to-reference`
- False-positive risk: low
- Allowed example location: fixtures/evals

## stale-reference

- Signals: local Markdown links or backtick paths that do not exist.
- Default action: `manual-review`
- False-positive risk: medium
- Allowed example location: fixtures/evals

## archive-autoload

- Signals: instructions to always read archive, deprecated, old, or backup paths.
- Default action: `remove`
- False-positive risk: low
- Allowed example location: fixtures/evals

## compatibility-risk

- Signals: old-looking content near schema, migration, protocol, alias, or compat wording.
- Default action: `keep-with-reason`
- False-positive risk: high
- Allowed example location: any tested compatibility fixture

## unsafe-context

- Signals: secret-like literals, hidden Unicode, or dangerous shell snippets.
- Default action: `manual-review`
- False-positive risk: medium
- Allowed example location: fixtures/evals

