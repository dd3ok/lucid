#!/usr/bin/env python3
"""Validate Lucid skill packaging constraints."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "lucid" / "SKILL.md"
REFERENCES = ROOT / "skills" / "lucid" / "references"
LUCID_SCRIPT = ROOT / "skills" / "lucid" / "scripts" / "lucid.py"
FORBIDDEN_PHRASES = [
    "handoff-txt",
    "soul-memory",
]


def fail(message: str) -> None:
    print(f"validate-skill: {message}", file=sys.stderr)
    raise SystemExit(1)


def parse_frontmatter(text: str) -> dict[str, str]:
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        fail("missing YAML frontmatter")

    fields: dict[str, str] = {}
    current_key: str | None = None
    current_value: list[str] = []
    for raw_line in match.group(1).splitlines():
        if re.match(r"^[A-Za-z0-9_-]+:\s*", raw_line):
            if current_key is not None:
                fields[current_key] = " ".join(current_value).strip()
            key, value = raw_line.split(":", 1)
            current_key = key.strip()
            current_value = [value.strip().strip("> ")]
        elif current_key is not None:
            current_value.append(raw_line.strip())
    if current_key is not None:
        fields[current_key] = " ".join(current_value).strip()
    return fields


def main() -> int:
    if not SKILL.exists():
        fail("skills/lucid/SKILL.md is missing")
    if not LUCID_SCRIPT.exists():
        fail("skills/lucid/scripts/lucid.py is missing")

    text = SKILL.read_text(encoding="utf-8")
    fields = parse_frontmatter(text)
    if fields.get("name") != "lucid":
        fail("frontmatter name must be lucid")
    description = fields.get("description", "")
    if not description:
        fail("frontmatter description is missing")
    if len(description) > 1024:
        fail("frontmatter description exceeds 1024 characters")
    if len(text.splitlines()) > 120:
        fail("SKILL.md exceeds 120 lines")

    required_refs = [
        "context-surfaces.md",
        "memory-retention-rubric.md",
        "cleanup-actions.md",
        "source-of-truth.md",
        "negative-residue.md",
        "compatibility-safety.md",
        "rule-taxonomy.md",
        "security.md",
    ]
    for name in required_refs:
        if not (REFERENCES / name).exists():
            fail(f"missing reference {name}")

    corpus = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [SKILL, ROOT / "AGENTS.md", ROOT / "README.md"]
        if path.exists()
    ).lower()
    for phrase in FORBIDDEN_PHRASES:
        if phrase in corpus:
            fail(f"forbidden phrase found: {phrase}")

    print("validate-skill: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

