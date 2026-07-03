# Release Checklist

## Standard Release Validation

- [ ] `python3 -m py_compile lucid.py skills/lucid/scripts/lucid.py scripts/validate-skill.py scripts/validate-evals.py scripts/validate-no-dangerous-io.py scripts/validate-docs.py scripts/validate-package-skill.py scripts/package-skill.py`
- [ ] `python3 scripts/validate-skill.py`
- [ ] `python3 scripts/validate-no-dangerous-io.py`
- [ ] `python3 scripts/validate-evals.py`
- [ ] `python3 scripts/validate-docs.py`
- [ ] `python3 scripts/validate-package-skill.py`
- [ ] `python3 scripts/package-skill.py --target openai-hosted --out dist/openai/lucid.zip`
- [ ] `python3 lucid.py verify --root . --strict`
- [ ] `python3 lucid.py audit --root . --format terminal`
- [ ] `python3 lucid.py audit --root fixtures/unsafe-context --format sarif --out .lucid/audit.sarif`
- [ ] `python3 lucid.py plan --root fixtures/unsafe-context --format json`
- [ ] `git diff --check`
- [ ] `CHANGELOG.md` has a dated release section.
- [ ] `VERSION` in `skills/lucid/scripts/lucid.py` matches the release version.
- [ ] `metadata.openclaw.version` in `skills/lucid/SKILL.md` matches the release version.
- [ ] `LICENSE` file is present and contains the correct MIT license text.
- [ ] `README.md` status matches the release state.
- [ ] `SECURITY.md` still states the read-only, no-network, no-LLM, no env-read, and no auto-apply constraints.
- [ ] GitHub Actions docs keep direct Python script execution as the primary CI path.
- [ ] If `action.yml` remains present, it is documented as experimental and not the primary CI surface.
- [ ] No generated `.lucid/` reports or `dist/` package archives are committed.
- [ ] GitHub repository description and topics are reviewed before public release.

## Suggested GitHub Metadata

Description:

```text
Skill-first context hygiene toolkit for AI agents.
```

Topics:

```text
ai-agents
agent-skills
codex
claude-code
gemini-cli
hermes-agent
openai
chatgpt
openclaw
context-engineering
prompt-debt
context-hygiene
memory-gc
```
