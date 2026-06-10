#!/usr/bin/env python3
"""Validate documentation contracts that should not drift."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GITHUB_ACTIONS_DOC = ROOT / "docs" / "github-actions.md"
POLICY_PACKS_DOC = ROOT / "docs" / "policy-packs.md"
README = ROOT / "README.md"
ACTION = ROOT / "action.yml"
LUCID_SCRIPT = ROOT / "skills" / "lucid" / "scripts" / "lucid.py"

EXPERIMENTAL_ACTION_FORBIDDEN_PATTERNS = [
    (re.compile(r"\bgit\s+apply\b"), "git apply"),
    (re.compile(r"\bcurl\b"), "curl"),
    (re.compile(r"\bpip\s+install\b"), "pip install"),
    (re.compile(r"\bnpm\b"), "npm"),
    (re.compile(r"\bupload-sarif\b"), "upload-sarif"),
    (re.compile(r"\bupload-artifact\b"), "upload-artifact"),
    (re.compile(r"\bgh\b"), "gh"),
    (re.compile(r"\|\s*tee\b"), "tee pipe"),
]


def fail(message: str) -> None:
    print(f"validate-docs: {message}", file=sys.stderr)
    raise SystemExit(1)


def require_text(text: str, needle: str, label: str) -> None:
    if needle not in text:
        fail(f"{label} missing required text: {needle}")


def forbid_text(text: str, needle: str, label: str) -> None:
    if needle in text:
        fail(f"{label} contains forbidden text: {needle}")


def forbid_command(text: str, command: str, label: str) -> None:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == command or stripped.startswith(f"{command} "):
            fail(f"{label} contains forbidden command: {command}")
        if f"`{command}`" in line or f"`{command} " in line:
            fail(f"{label} contains forbidden command: {command}")


def read_lucid_version() -> str:
    if not LUCID_SCRIPT.exists():
        fail("skills/lucid/scripts/lucid.py is missing")
    text = LUCID_SCRIPT.read_text(encoding="utf-8")
    match = re.search(r"^VERSION\s*=\s*['\"]([^'\"]+)['\"]", text, re.MULTILINE)
    if not match:
        fail("skills/lucid/scripts/lucid.py is missing VERSION or has an unexpected format")
    return match.group(1)


def validate_github_actions_doc() -> None:
    if not GITHUB_ACTIONS_DOC.exists():
        fail("docs/github-actions.md is missing")

    text = GITHUB_ACTIONS_DOC.read_text(encoding="utf-8")
    version = read_lucid_version()
    required = [
        "direct Python script execution",
        "checkout or vendor Lucid",
        f"ref: v{version}",
        "mkdir -p .lucid",
        "python3 .lucid-tool/lucid.py audit --root . --format sarif --out .lucid/audit.sarif",
        "python3 .lucid-tool/lucid.py plan --root . --format json --out .lucid/plan.json",
        "python3 .lucid-tool/lucid.py audit --root . --format terminal | tee .lucid/audit.txt",
        "python3 .lucid-tool/lucid.py audit --root . --format github-actions",
        "Annotations are parsed from stdout by the GitHub Actions runner.",
        "does not call the GitHub API",
        "omit snippets and raw context",
        "$GITHUB_STEP_SUMMARY",
        "security-events: write",
        "github/codeql-action/upload-sarif",
        "actions/upload-artifact",
        "full-length commit SHAs",
        "Lucid does not apply patches",
        "run project scripts",
        "Artifact upload and SARIF upload are GitHub workflow choices",
        "The composite action in `action.yml` is experimental",
        "not the primary CI surface",
        "direct script workflow",
    ]
    for needle in required:
        require_text(text, needle, "docs/github-actions.md")

    forbidden = [
        ".github/workflows/",
        ".github/actions/",
        "git apply",
        "curl ",
        "pip install",
        "npm ",
        "uses: dd3ok/lucid@",
    ]
    for needle in forbidden:
        forbid_text(text, needle, "docs/github-actions.md")
    forbid_command(text, "gh", "docs/github-actions.md")

    minimal_start = text.find("## Minimal Report-Only Workflow")
    annotations_start = text.find("## Optional Inline Annotations")
    optional_start = text.find("## Optional Uploads")
    if (
        minimal_start == -1
        or annotations_start == -1
        or optional_start == -1
        or annotations_start < minimal_start
        or optional_start < annotations_start
    ):
        fail(
            "docs/github-actions.md is missing workflow sections "
            "or they are in the wrong order"
        )
    minimal = text[minimal_start:annotations_start]
    if "security-events: write" in minimal:
        fail("minimal GitHub Actions workflow must not require security-events: write")

    if not README.exists():
        fail("README.md is missing")
    readme = README.read_text(encoding="utf-8")
    require_text(readme, "docs/github-actions.md", "README.md")


def validate_policy_packs_doc() -> None:
    if not POLICY_PACKS_DOC.exists():
        fail("docs/policy-packs.md is missing")

    text = POLICY_PACKS_DOC.read_text(encoding="utf-8")
    normalized_text = " ".join(text.split())
    required = [
        "deterministic config overlays, not plugins",
        "cannot execute code",
        "call networks",
        "call LLMs",
        "read environment values",
        "read credential stores",
        "add new rule engines",
        "This schema is a design contract for v0.3",
        "Built-in policy packs are loaded by setting `policy_pack`",
        "Hermes",
        "Unknown pack names fail closed.",
        "Schema design.",
        "Config schema validation.",
        "Policy pack loading.",
    ]
    for needle in required:
        normalized_needle = " ".join(needle.split())
        require_text(normalized_text, normalized_needle, "docs/policy-packs.md")

    if not README.exists():
        fail("README.md is missing")
    readme = README.read_text(encoding="utf-8")
    require_text(readme, "docs/policy-packs.md", "README.md")


def validate_experimental_action_safety() -> None:
    if not ACTION.exists():
        fail("action.yml is missing")

    text = ACTION.read_text(encoding="utf-8")
    required = [
        "Experimental report-only",
        "using: composite",
        "GITHUB_WORKSPACE",
        "root must stay inside GITHUB_WORKSPACE",
        "$artifact_dir/audit.sarif",
        "$artifact_dir/plan.json",
        "$artifact_dir/audit.txt",
    ]
    for needle in required:
        require_text(text, needle, "action.yml")

    forbid_experimental_action_shell(text, "action.yml")


def forbid_experimental_action_shell(text: str, label: str) -> None:
    forbidden = [
        ".github/workflows/",
        ".github/actions/",
    ]
    for needle in forbidden:
        forbid_text(text, needle, label)
    pattern_name = forbidden_action_shell_pattern(text)
    if pattern_name is not None:
        fail(f"{label} contains forbidden action shell pattern: {pattern_name}")


def forbidden_action_shell_pattern(text: str) -> str | None:
    for pattern, name in EXPERIMENTAL_ACTION_FORBIDDEN_PATTERNS:
        if pattern.search(text):
            return name
    return None


def validate_experimental_action_safety_regressions() -> None:
    bypass_samples = [
        "run: echo ok |tee .lucid/audit.txt",
        "run: echo ok && gh pr view",
    ]
    for sample in bypass_samples:
        if forbidden_action_shell_pattern(sample) is None:
            fail(f"action.yml safety regression was not caught: {sample}")


def main() -> int:
    validate_github_actions_doc()
    validate_policy_packs_doc()
    validate_experimental_action_safety()
    validate_experimental_action_safety_regressions()
    print("validate-docs: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
