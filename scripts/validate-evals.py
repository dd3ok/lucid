#!/usr/bin/env python3
"""Validate behavior fixtures against the Lucid audit engine."""

from __future__ import annotations

import contextlib
import io
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "evals" / "behavior-cases"
LUCID_SCRIPT = ROOT / "skills" / "lucid" / "scripts" / "lucid.py"
SKILL_MD = ROOT / "skills" / "lucid" / "SKILL.md"
TRIGGER_QUERIES = ROOT / "evals" / "trigger-queries.json"
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


def skill_description() -> str:
    text = SKILL_MD.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        fail("SKILL.md is missing frontmatter")
    frontmatter = text.split("---\n", 2)[1]
    lines = frontmatter.splitlines()
    collecting = False
    parts: list[str] = []
    for line in lines:
        if line.startswith("description:"):
            collecting = True
            parts.append(line.split(":", 1)[1].strip().strip("> "))
            continue
        if collecting and line.startswith((" ", "\t")):
            parts.append(line.strip())
            continue
        if collecting:
            break
    description = " ".join(parts).lower()
    if not description:
        fail("SKILL.md description is missing")
    return description


def validate_trigger_queries() -> None:
    if not TRIGGER_QUERIES.exists():
        fail("evals/trigger-queries.json is missing")
    data = json.loads(TRIGGER_QUERIES.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        fail("trigger-queries.json must be a JSON object")
    should_trigger = data.get("should_trigger", [])
    should_not_trigger = data.get("should_not_trigger", [])
    if not should_trigger or not should_not_trigger:
        fail("trigger-queries.json must define should_trigger and should_not_trigger")

    description = skill_description()
    required_trigger_terms = [
        "context hygiene",
        "prompt debt",
        "memory cleanup",
        "old instructions",
        "과거 잔재",
        "오래된 지침",
        "프롬프트 부채",
        "컨텍스트 정리",
    ]
    required_boundary_terms = [
        "ordinary readme edits",
        "general code refactors",
        "normal linting",
        "summarization",
        "creating a memory bank",
    ]
    for term in required_trigger_terms:
        if term.lower() not in description:
            fail(f"SKILL.md description missing trigger term: {term}")
    for term in required_boundary_terms:
        if term.lower() not in description:
            fail(f"SKILL.md description missing boundary term: {term}")


def validate_plan_audit_input_scope(lucid: ModuleType) -> None:
    outside_inputs = [
        str(ROOT.parent / "lucid-outside-audit.json"),
        "../lucid-outside-audit.json",
    ]
    for outside_audit in outside_inputs:
        try:
            lucid.load_audit_for_plan(ROOT, outside_audit)
        except SystemExit:
            continue
        except OSError as exc:
            fail(f"load_audit_for_plan tried to read audit input outside .lucid/: {exc}")
        fail("load_audit_for_plan accepted audit input outside .lucid/")


def validate_explicit_config_path(lucid: ModuleType) -> None:
    fixture = ROOT / "fixtures" / "unsafe-context"
    audit = lucid.audit(
        fixture,
        output_format="json",
        config_path="alt-lucid.config.json",
    )
    if has_match(audit["findings"], {"rule": "unsafe-context", "path": "AGENTS.md"}):
        fail("explicit config path did not disable unsafe_context")

    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        exit_code = lucid.main(
            [
                "audit",
                "--root",
                str(fixture),
                "--config",
                "alt-lucid.config.json",
                "--format",
                "json",
            ]
        )
    if exit_code != 0:
        fail("audit --config returned non-zero exit code")
    cli_audit = json.loads(stdout.getvalue())
    if has_match(cli_audit["findings"], {"rule": "unsafe-context", "path": "AGENTS.md"}):
        fail("audit --config did not disable unsafe_context")

    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        exit_code = lucid.main(
            [
                "plan",
                "--root",
                str(fixture),
                "--config",
                "alt-lucid.config.json",
                "--out",
                ".lucid/config-plan.md",
            ]
        )
    if exit_code != 0:
        fail("plan --config returned non-zero exit code")
    if "No findings." not in stdout.getvalue():
        fail("plan --config did not use explicit config")

    try:
        lucid.audit(fixture, output_format="json", config_path="../lucid.config.example.json")
    except SystemExit as exc:
        if "lucid.config.example.json" not in str(exc):
            fail("outside-root config error did not include resolved path")
    else:
        fail("explicit config path accepted file outside target root")

    try:
        lucid.audit(fixture, output_format="json", config_path="")
    except SystemExit:
        return
    fail("empty explicit config path fell back to default config")


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
        expected_total = case.get("expected_total_findings")
        if expected_total is not None and len(findings) != expected_total:
            fail(
                f"{case_path.name} expected {expected_total} findings, got {len(findings)}"
            )

        for expected in case.get("expected_findings", []):
            if not has_match(findings, expected):
                fail(f"{case_path.name} missing expected finding {expected}")
        for forbidden in case.get("forbidden_findings", []):
            if has_match(findings, forbidden):
                fail(f"{case_path.name} produced forbidden finding {forbidden}")
        for forbidden_snippet in case.get("forbidden_snippets", []):
            for finding in findings:
                if forbidden_snippet in str(finding.get("snippet", "")):
                    fail(f"{case_path.name} exposed forbidden snippet {forbidden_snippet}")
        expected_plan_contains = case.get("expected_plan_contains", [])
        if expected_plan_contains:
            plan = lucid.render_plan_markdown(audit)
            for expected_text in expected_plan_contains:
                if expected_text not in plan:
                    fail(f"{case_path.name} plan missing expected text {expected_text}")
        if case["name"] == "unsafe-context":
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = lucid.main(
                    [
                        "plan",
                        "--root",
                        str(fixture),
                        "--format",
                        "json",
                    ]
                )
            if exit_code != 0:
                fail("plan --format json returned non-zero exit code")
            plan_json = json.loads(stdout.getvalue())
            if plan_json.get("format") != "lucid-plan-json":
                fail("plan --format json did not emit plan JSON marker")
            if plan_json.get("summary", {}).get("total") != 1:
                fail("plan --format json did not include expected summary total")
            actions = plan_json.get("recommended_actions")
            if not isinstance(actions, list) or len(actions) != 1:
                fail("plan --format json did not include one recommended action")
            action = actions[0]
            if action.get("rule") != "unsafe-context":
                fail("plan --format json action did not preserve finding rule")
            plan_json_text = json.dumps(plan_json, ensure_ascii=False)
            if "sk_test_abcdefghijklmnopqrstuvwxyz123456" in plan_json_text:
                fail("plan --format json exposed unsafe snippet")

    validate_trigger_queries()
    validate_plan_audit_input_scope(lucid)
    validate_explicit_config_path(lucid)
    print("validate-evals: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
