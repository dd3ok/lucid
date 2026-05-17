#!/usr/bin/env python3
"""Validate behavior fixtures against the Lucid audit engine."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "evals" / "behavior-cases"
LUCID_SCRIPT = ROOT / "skills" / "lucid" / "scripts" / "lucid.py"
ALLOWED_ACTIONS = {
    "remove",
    "replace-with-pointer",
    "move-to-reference",
    "move-to-validator",
    "move-to-eval",
    "keep-with-reason",
    "manual-review",
}


def fail(message: str) -> None:
    print(f"validate-evals: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_lucid() -> ModuleType:
    if not LUCID_SCRIPT.exists():
        fail("skills/lucid/scripts/lucid.py is missing")
    spec = importlib.util.spec_from_file_location("lucid_skill_script", LUCID_SCRIPT)
    if spec is None or spec.loader is None:
        fail("cannot load lucid.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def has_match(findings: list[dict[str, object]], expected: dict[str, str]) -> bool:
    for finding in findings:
        if all(finding.get(key) == value for key, value in expected.items()):
            return True
    return False


def main() -> int:
    if not CASES.exists():
        fail("evals/behavior-cases is missing")
    lucid = load_lucid()

    case_paths = sorted(CASES.glob("*.json"))
    if not case_paths:
        fail("no behavior cases found")

    for case_path in case_paths:
        case = json.loads(case_path.read_text(encoding="utf-8"))
        fixture = ROOT / case["fixture"]
        if not fixture.exists():
            fail(f"{case_path.name} points to missing fixture {case['fixture']}")

        audit = lucid.audit(fixture, output_format="json")
        findings = audit["findings"]
        for finding in findings:
            action = finding.get("suggested_action")
            if action not in ALLOWED_ACTIONS:
                fail(f"{case_path.name} produced unsupported action {action}")

        for expected in case.get("expected_findings", []):
            if not has_match(findings, expected):
                fail(f"{case_path.name} missing expected finding {expected}")
        for forbidden in case.get("forbidden_findings", []):
            if has_match(findings, forbidden):
                fail(f"{case_path.name} produced forbidden finding {forbidden}")

    print("validate-evals: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

