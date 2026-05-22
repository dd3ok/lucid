#!/usr/bin/env python3
"""Validate documentation contracts that should not drift."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GITHUB_ACTIONS_DOC = ROOT / "docs" / "github-actions.md"
README = ROOT / "README.md"
ACTION = ROOT / "action.yml"


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


def validate_github_actions_doc() -> None:
    if not GITHUB_ACTIONS_DOC.exists():
        fail("docs/github-actions.md is missing")

    text = GITHUB_ACTIONS_DOC.read_text(encoding="utf-8")
    required = [
        "without a dedicated wrapper action",
        "mkdir -p .lucid",
        "python3 lucid.py audit --root . --format sarif --out .lucid/audit.sarif",
        "python3 lucid.py plan --root . --format json --out .lucid/plan.json",
        "python3 lucid.py audit --root . --format terminal | tee .lucid/audit.txt",
        "$GITHUB_STEP_SUMMARY",
        "security-events: write",
        "github/codeql-action/upload-sarif",
        "actions/upload-artifact",
        "full-length commit SHAs",
        "Lucid does not apply patches",
        "run project scripts",
        "Artifact upload and SARIF upload are GitHub workflow choices",
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
    ]
    for needle in forbidden:
        forbid_text(text, needle, "docs/github-actions.md")
    forbid_command(text, "gh", "docs/github-actions.md")

    minimal_start = text.find("## Minimal Report-Only Workflow")
    optional_start = text.find("## Optional Uploads")
    if minimal_start == -1 or optional_start == -1 or optional_start < minimal_start:
        fail(
            "docs/github-actions.md is missing workflow sections "
            "or they are in the wrong order"
        )
    minimal = text[minimal_start:optional_start]
    if "security-events: write" in minimal:
        fail("minimal GitHub Actions workflow must not require security-events: write")

    if not README.exists():
        fail("README.md is missing")
    readme = README.read_text(encoding="utf-8")
    require_text(readme, "docs/github-actions.md", "README.md")


def validate_action_wrapper() -> None:
    if not ACTION.exists():
        fail("action.yml is missing")

    text = ACTION.read_text(encoding="utf-8")
    required = [
        "using: composite",
        "python3 \"${{ github.action_path }}/lucid.py\" audit --root",
        "--format sarif --out .lucid/audit.sarif > /dev/null",
        "python3 \"${{ github.action_path }}/lucid.py\" plan --root",
        "--format json --out .lucid/plan.json > /dev/null",
        "python3 \"${{ github.action_path }}/lucid.py\" audit --root",
        "--format terminal --out .lucid/audit.txt > /dev/null",
        "$GITHUB_STEP_SUMMARY",
    ]
    for needle in required:
        require_text(text, needle, "action.yml")

    forbidden = [
        "git apply",
        "curl ",
        "pip install",
        "npm ",
        "upload-sarif",
        "upload-artifact",
        ".github/workflows/",
        ".github/actions/",
        "| tee",
    ]
    for needle in forbidden:
        forbid_text(text, needle, "action.yml")
    forbid_command(text, "gh", "action.yml")


def main() -> int:
    validate_github_actions_doc()
    validate_action_wrapper()
    print("validate-docs: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
