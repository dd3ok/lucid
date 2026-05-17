# Negative Residue

Negative residue happens when obsolete concepts remain in user-facing context as
warnings.

## Bad

```md
Do not use OLD_IDENTIFIER.
Never create OLD_ARTIFACT.
Avoid the previous workflow.
```

## Better

```md
Use the current workflow in `skills/<skill>/SKILL.md`.
```

## Best

- User-facing docs mention only current canonical behavior.
- Validators detect obsolete identifiers in restricted surfaces.
- Fixtures preserve old identifiers only for regression tests.
- The cleanup plan explains the removal.

