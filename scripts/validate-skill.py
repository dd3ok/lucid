#!/usr/bin/env python3
"""Validate Lucid skill packaging constraints."""

from __future__ import annotations

import contextlib
import io
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "lucid" / "SKILL.md"
REFERENCES = ROOT / "skills" / "lucid" / "references"
LUCID_SCRIPT = ROOT / "skills" / "lucid" / "scripts" / "lucid.py"
OPENAI_YAML = ROOT / "skills" / "lucid" / "agents" / "openai.yaml"
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


def frontmatter_text(text: str) -> str:
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        fail("missing YAML frontmatter")
    return match.group(1)


def validate_openclaw_metadata(fields: dict[str, str], frontmatter: str) -> None:
    raw = fields.get("metadata")
    if raw is None:
        return

    metadata_seen = False
    for raw_line in frontmatter.splitlines():
        if re.match(r"^[A-Za-z0-9_-]+:\s*", raw_line):
            key, raw_value = raw_line.split(":", 1)
            metadata_seen = key.strip() == "metadata"
            if metadata_seen and not raw_value.strip():
                fail("frontmatter metadata must be a single-line JSON object")
            continue
        if metadata_seen and raw_line.strip():
            fail("frontmatter metadata must be a single-line JSON object")

    if not raw:
        return
    try:
        metadata = json.loads(raw)
    except json.JSONDecodeError as exc:
        fail(f"frontmatter metadata must be JSON: {exc}")
    if not isinstance(metadata, dict):
        fail("frontmatter metadata must be a JSON object")

    openclaw = metadata.get("openclaw")
    if openclaw is None:
        return
    if not isinstance(openclaw, dict):
        fail("metadata.openclaw must be an object")

    requires = openclaw.get("requires", {})
    if not isinstance(requires, dict):
        fail("metadata.openclaw.requires must be an object")

    bins = requires.get("bins")
    any_bins = requires.get("anyBins")
    if bins is not None and not (
        isinstance(bins, list) and all(isinstance(item, str) for item in bins)
    ):
        fail("metadata.openclaw.requires.bins must be a string array")
    if any_bins is not None and not (
        isinstance(any_bins, list) and all(isinstance(item, str) for item in any_bins)
    ):
        fail("metadata.openclaw.requires.anyBins must be a string array")


def expect_openclaw_metadata_failure(
    fields: dict[str, str], frontmatter: str, expected: str
) -> None:
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            validate_openclaw_metadata(fields, frontmatter)
    except SystemExit:
        return
    fail(f"openclaw metadata regression was accepted: {expected}")


def validate_openclaw_metadata_regressions() -> None:
    validate_openclaw_metadata(
        {"metadata": '{"openclaw":{"requires":{"bins":["python3"]}}}'},
        'metadata: {"openclaw":{"requires":{"bins":["python3"]}}}',
    )
    validate_openclaw_metadata(
        {"metadata": '{"openclaw":{"requires":{"anyBins":["python3","python"]}}}'},
        'metadata: {"openclaw":{"requires":{"anyBins":["python3","python"]}}}',
    )
    expect_openclaw_metadata_failure(
        {"metadata": '{"openclaw":{"requires":{"bins":["python3"]}}}'},
        'metadata:\n  openclaw:\n    requires:\n      bins: ["python3"]',
        "nested YAML metadata",
    )
    expect_openclaw_metadata_failure(
        {"metadata": "{'openclaw': {'requires': {'bins': ['python3']}}}"},
        "metadata: {'openclaw': {'requires': {'bins': ['python3']}}}",
        "non-JSON metadata",
    )
    expect_openclaw_metadata_failure(
        {"metadata": '{"openclaw":{"requires":{"bins":"python3"}}}'},
        'metadata: {"openclaw":{"requires":{"bins":"python3"}}}',
        "non-array bins",
    )
    expect_openclaw_metadata_failure(
        {"metadata": '{"openclaw":{"requires":{"anyBins":[3]}}}'},
        'metadata: {"openclaw":{"requires":{"anyBins":[3]}}}',
        "non-string anyBins",
    )


def validate_lucid_openclaw_runtime_metadata(fields: dict[str, str]) -> None:
    raw = fields.get("metadata")
    if raw is None:
        fail("Lucid SKILL.md must declare OpenClaw runtime metadata")
    metadata = json.loads(raw)
    if not isinstance(metadata, dict):
        fail("Lucid OpenClaw metadata must be a JSON object")

    openclaw = metadata.get("openclaw") or {}
    if not isinstance(openclaw, dict):
        fail("Lucid OpenClaw metadata.openclaw must be an object")

    requires = openclaw.get("requires") or {}
    if not isinstance(requires, dict):
        fail("Lucid OpenClaw metadata.openclaw.requires must be an object")

    any_bins = requires.get("anyBins")
    if any_bins != ["python3", "python"]:
        fail('Lucid OpenClaw metadata must use anyBins ["python3", "python"]')
    if "bins" in requires:
        fail("Lucid OpenClaw metadata must not require only python3")


def expect_lucid_openclaw_runtime_metadata_failure(
    fields: dict[str, str], expected: str
) -> None:
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            validate_lucid_openclaw_runtime_metadata(fields)
    except SystemExit:
        return
    fail(f"Lucid OpenClaw runtime metadata regression was accepted: {expected}")


def validate_lucid_openclaw_runtime_metadata_regressions() -> None:
    expect_lucid_openclaw_runtime_metadata_failure(
        {"metadata": "null"},
        "metadata null",
    )
    expect_lucid_openclaw_runtime_metadata_failure(
        {"metadata": '{"openclaw":null}'},
        "openclaw null",
    )
    expect_lucid_openclaw_runtime_metadata_failure(
        {"metadata": '{"openclaw":{"requires":null}}'},
        "requires null",
    )


def validate_description_quality(description: str) -> None:
    if len(description) > 420:
        fail("frontmatter description exceeds Lucid 420 character trigger budget")
    mojibake_markers = ["�", "怨", "吏", "?ㅻ", "?붿"]
    if any(marker in description for marker in mojibake_markers):
        fail("frontmatter description contains mojibake markers")
    required_start = (
        "Audits stale, unsafe, contradictory, or bloated agent-facing context "
        "and produces cleanup plans."
    )
    if not description.startswith(required_start):
        fail("frontmatter description must front-load Lucid's core trigger")
    required_terms = [
        "prompt debt",
        "프롬프트 부채",
        "컨텍스트 정리",
        "obsolete agent instructions",
        "memory cleanup",
        "source-of-truth drift",
        "skill descriptions",
        "Do not use",
        "general code refactors",
    ]
    for term in required_terms:
        if term not in description:
            fail(f"frontmatter description missing trigger/boundary term: {term}")


def validate_openai_yaml() -> None:
    if not OPENAI_YAML.exists():
        fail("skills/lucid/agents/openai.yaml is missing")
    lines = OPENAI_YAML.read_text(encoding="utf-8").splitlines()
    required = {
        "display_name",
        "short_description",
        "default_prompt",
    }
    for line in lines:
        if not line.startswith(" ") and ":" in line:
            key = line.split(":", 1)[0].strip()
            if key in required:
                fail(f"agents/openai.yaml has flat {key}; use interface.{key}")
    if not any(line.rstrip() == "interface:" for line in lines):
        fail("agents/openai.yaml must define interface metadata")
    values: dict[str, str] = {}
    inside_interface = False
    for line in lines:
        if line.rstrip() == "interface:":
            inside_interface = True
            continue
        if inside_interface:
            if line and not line.startswith(" "):
                inside_interface = False
                continue
            stripped = line.strip()
            if ":" in stripped:
                key, raw_value = stripped.split(":", 1)
                key = key.strip()
                if key in required:
                    raw_value = raw_value.strip()
                    if not (
                        len(raw_value) >= 2
                        and raw_value.startswith('"')
                        and raw_value.endswith('"')
                    ):
                        fail(f"agents/openai.yaml interface.{key} must be double-quoted")
                    values[key] = raw_value[1:-1]
    missing = sorted(required - values.keys())
    if missing:
        fail(f"agents/openai.yaml missing interface fields: {', '.join(missing)}")
    short_description = values["short_description"]
    if not 25 <= len(short_description) <= 64:
        fail("agents/openai.yaml interface.short_description must be 25-64 chars")
    lowered_short_description = short_description.lower()
    if "context" not in lowered_short_description or not (
        "cleanup" in lowered_short_description or "prompt debt" in lowered_short_description
    ):
        fail(
            "agents/openai.yaml interface.short_description must mention "
            "context and cleanup or prompt debt"
        )
    if "$lucid" not in values["default_prompt"]:
        fail("agents/openai.yaml interface.default_prompt must mention $lucid")


def read_lucid_script_version() -> str:
    text = LUCID_SCRIPT.read_text(encoding="utf-8")
    match = re.search(r"^VERSION\s*=\s*['\"]([^'\"]+)['\"]", text, re.MULTILINE)
    if not match:
        fail("skills/lucid/scripts/lucid.py is missing VERSION or has an unexpected format")
    return match.group(1)


def main() -> int:
    if not SKILL.exists():
        fail("skills/lucid/SKILL.md is missing")
    if not LUCID_SCRIPT.exists():
        fail("skills/lucid/scripts/lucid.py is missing")

    text = SKILL.read_text(encoding="utf-8")
    fields = parse_frontmatter(text)
    frontmatter = frontmatter_text(text)
    if fields.get("name") != "lucid":
        fail("frontmatter name must be lucid")
    script_version = read_lucid_script_version()
    if fields.get("version") != script_version:
        fail(
            f"frontmatter version ({fields.get('version')}) must match "
            f"skills/lucid/scripts/lucid.py VERSION ({script_version})"
        )
    description = fields.get("description", "")
    if not description:
        fail("frontmatter description is missing")
    if len(description) > 1024:
        fail("frontmatter description exceeds 1024 characters")
    validate_description_quality(description)
    if len(text.splitlines()) > 120:
        fail("SKILL.md exceeds 120 lines")
    validate_openclaw_metadata(fields, frontmatter)
    validate_openclaw_metadata_regressions()
    validate_lucid_openclaw_runtime_metadata(fields)
    validate_lucid_openclaw_runtime_metadata_regressions()
    validate_openai_yaml()

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
