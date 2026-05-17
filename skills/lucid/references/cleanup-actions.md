# Cleanup Actions

Every finding must map to one action.

## remove

Delete context because it is stale, redundant, unsafe, or not useful.

Use only when the content is not compatibility-sensitive, the current source of
truth is clear, and deletion does not remove required behavior.

## replace-with-pointer

Replace duplicated policy text with a pointer to the canonical source.

Use when the same rule appears in multiple files, wording has drifted, or
always-loaded files contain too much detail.

## move-to-reference

Move useful detail out of always-loaded context.

Use when detail is still useful but is not needed on every agent turn.

## move-to-validator

Enforce a rule with script logic instead of natural-language warnings.

Use when user-facing docs preserve old names only to warn against them.

## move-to-eval

Preserve a regression case without exposing it as guidance.

Use when an old bug must not return and the old identifier should only exist
inside fixtures/evals.

## keep-with-reason

Keep content and explain why.

Use when content is compatibility-sensitive or removal could break schema,
protocol, migrations, or integrations.

## manual-review

Do not decide automatically.

Use when the source of truth is unclear, content may be sensitive, or the script
cannot safely classify it.

