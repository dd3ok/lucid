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
LUCID_WRAPPER = ROOT / "lucid.py"
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


def validate_config_schema_validation(lucid: ModuleType) -> None:
    fixture = ROOT / "fixtures" / "invalid-config"
    cases = [
        ("missing-version.json", "version must be 1"),
        ("version-bool.json", "version must be 1"),
        ("version-float.json", "version must be 1"),
        ("unknown-top-level.json", "unknown top-level config key: policy_packz"),
        ("unknown-rule.json", "unknown rules key: unsafe-context"),
        ("rule-type.json", "rules.unsafe_context must be a boolean"),
        ("surface-type.json", "surfaces.always_loaded must be a list of strings"),
        ("threshold-type.json", "thresholds.always_loaded_max_lines must be a number"),
        ("write-policy-type.json", "write_policy.auto_apply must be a boolean"),
    ]
    for config_name, expected_message in cases:
        try:
            lucid.audit(fixture, output_format="json", config_path=config_name)
        except SystemExit as exc:
            if expected_message not in str(exc):
                fail(
                    f"{config_name} error did not include expected message: "
                    f"{expected_message}"
                )
        else:
            fail(f"{config_name} was accepted")


def validate_policy_pack_loading(lucid: ModuleType) -> None:
    fixture = ROOT / "fixtures" / "policy-pack-claude"
    scan = lucid.scan(fixture, output_format="json")
    paths = {item.get("path") for item in scan.get("files", [])}
    if ".claude/skills/reviewer/SKILL.md" not in paths:
        fail("claude policy pack did not include .claude skill surface")

    invalid_fixture = ROOT / "fixtures" / "invalid-policy-pack"
    try:
        lucid.scan(invalid_fixture, output_format="json")
    except SystemExit as exc:
        if "unknown policy_pack: unknown-runtime" not in str(exc):
            fail("unknown policy pack error did not identify pack name")
    else:
        fail("unknown policy pack was accepted")


def validate_source_graph(lucid: ModuleType) -> None:
    fixture = ROOT / "fixtures" / "source-graph"
    audit = lucid.audit(fixture, output_format="json")
    source_graph = audit.get("source_graph")
    if not isinstance(source_graph, list):
        fail("audit JSON did not expose source_graph")

    by_path = {
        node.get("path"): node.get("references")
        for node in source_graph
        if isinstance(node, dict)
    }
    agents_refs = by_path.get("AGENTS.md")
    if not isinstance(agents_refs, list):
        fail("source_graph did not include AGENTS.md references")

    expected_agents = {
        ("docs/product-design.md", 3, "markdown-link"),
        ("skills/lucid/SKILL.md", 5, "inline-code"),
        ("README.md", 7, "reference-intent"),
    }
    observed_agents = {
        (item.get("target"), item.get("line"), item.get("kind"))
        for item in agents_refs
        if isinstance(item, dict)
    }
    for expected in expected_agents:
        if expected not in observed_agents:
            fail(f"source_graph missing AGENTS.md edge {expected}")
    if any(item[0] == "https://example.com/lucid" for item in observed_agents):
        fail("source_graph included external URL edge")

    product_refs = by_path.get("docs/product-design.md")
    if not isinstance(product_refs, list):
        fail("source_graph did not include docs/product-design.md references")
    if ("skills/lucid/SKILL.md", 3, "markdown-link") not in {
        (item.get("target"), item.get("line"), item.get("kind"))
        for item in product_refs
        if isinstance(item, dict)
    }:
        fail("source_graph did not resolve relative markdown link")


def validate_stale_reference_provenance(lucid: ModuleType) -> None:
    fixture = ROOT / "fixtures" / "stale-reference"
    audit = lucid.audit(fixture, output_format="json")
    stale_findings = [
        finding for finding in audit["findings"] if finding.get("rule") == "stale-reference"
    ]
    if not stale_findings:
        fail("stale-reference fixture did not produce stale-reference findings")

    expected_candidates = {"docs/missing.md", "scripts/missing.py"}
    observed_candidates: set[str] = set()
    for finding in stale_findings:
        provenance = finding.get("provenance")
        if not isinstance(provenance, dict):
            fail("stale-reference finding did not expose provenance")
        if provenance.get("deterministic") is not True:
            fail("stale-reference provenance is not marked deterministic")
        signals = provenance.get("signals")
        if not isinstance(signals, list) or len(signals) != 1:
            fail("stale-reference provenance did not expose one signal")
        signal = signals[0]
        if not isinstance(signal, dict):
            fail("stale-reference provenance signal was not an object")
        if signal.get("kind") != "missing-reference":
            fail("stale-reference provenance signal did not identify missing-reference")
        if signal.get("line") != finding.get("line_start"):
            fail("stale-reference provenance line did not match finding line")
        candidate = signal.get("candidate")
        if not isinstance(candidate, str):
            fail("stale-reference provenance candidate was not a string")
        observed_candidates.add(candidate)

    if expected_candidates != observed_candidates:
        fail("stale-reference provenance did not preserve missing reference candidates")


def finding_provenance_signal(finding: dict[str, object]) -> dict[str, object] | None:
    provenance = finding.get("provenance")
    if not isinstance(provenance, dict):
        return None
    if provenance.get("deterministic") is not True:
        return None
    signals = provenance.get("signals")
    if not isinstance(signals, list) or len(signals) != 1:
        return None
    signal = signals[0]
    return signal if isinstance(signal, dict) else None


def validate_source_of_truth_provenance(lucid: ModuleType) -> None:
    drift = lucid.audit(ROOT / "fixtures" / "source-of-truth-drift", output_format="json")
    drift_findings = [
        finding
        for finding in drift["findings"]
        if finding.get("rule") == "source-of-truth-drift"
    ]
    if not drift_findings:
        fail("source-of-truth-drift fixture did not produce findings")
    declaration_findings = [
        finding
        for finding in drift_findings
        if (finding_provenance_signal(finding) or {}).get("kind")
        == "source-of-truth-declaration-conflict"
    ]
    if not declaration_findings:
        fail("source-of-truth-drift provenance did not identify declaration conflict")
    for finding in declaration_findings:
        signal = finding_provenance_signal(finding)
        if signal is None:
            fail("source-of-truth-drift provenance did not expose one signal")
        if signal.get("key") != "canonical workflow":
            fail("source-of-truth-drift provenance did not preserve declaration key")
        if signal.get("value") not in {"scan-first", "summarize-first"}:
            fail("source-of-truth-drift provenance did not preserve finding value")
        if signal.get("compared_values_count") != 2:
            fail("source-of-truth-drift provenance did not count compared values")

    duplicate = lucid.audit(
        ROOT / "fixtures" / "source-of-truth-near-duplicate", output_format="json"
    )
    duplicate_findings = [
        finding
        for finding in duplicate["findings"]
        if finding.get("rule") == "source-of-truth-drift"
    ]
    if not duplicate_findings:
        fail("source-of-truth-near-duplicate fixture did not produce findings")
    duplicate_signal_findings = [
        finding
        for finding in duplicate_findings
        if (finding_provenance_signal(finding) or {}).get("kind")
        == "near-duplicate-policy-block"
    ]
    if not duplicate_signal_findings:
        fail("near-duplicate provenance did not identify policy block signal")
    expected_near_duplicate_range = (5, 7)
    for finding in duplicate_signal_findings:
        signal = finding_provenance_signal(finding)
        if signal is None:
            fail("near-duplicate source-of-truth provenance did not expose one signal")
        if signal.get("matched_path") not in {"AGENTS.md", "README.md"}:
            fail("near-duplicate provenance did not preserve matched path")
        if (
            signal.get("matched_line_start"),
            signal.get("matched_line_end"),
        ) != expected_near_duplicate_range:
            fail("near-duplicate provenance did not preserve matched line range")
        similarity = signal.get("similarity")
        if not isinstance(similarity, float) or similarity < 0.8:
            fail("near-duplicate provenance did not preserve similarity")


def validate_ignore_suppressions(lucid: ModuleType) -> None:
    fixture = ROOT / "fixtures" / "ignore-suppressions"
    audit = lucid.audit(fixture, output_format="json")
    if has_match(audit["findings"], {"rule": "stale-context", "path": "AGENTS.md"}):
        fail("lucid.ignore.json did not suppress stale-context finding")
    if audit.get("summary", {}).get("suppressed") != 1:
        fail("lucid.ignore.json did not count suppressed finding")
    suppressed = audit.get("suppressed_findings")
    if not isinstance(suppressed, list) or len(suppressed) != 1:
        fail("lucid.ignore.json did not expose one suppressed finding")
    suppression = suppressed[0].get("suppression", {})
    if suppression.get("reason") != (
        "Fixture keeps one known stale-context example to validate suppression behavior."
    ):
        fail("lucid.ignore.json did not preserve suppression reason")

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
        fail("plan --format json with lucid.ignore.json returned non-zero exit code")
    plan_json = json.loads(stdout.getvalue())
    if plan_json.get("summary", {}).get("suppressed") != 1:
        fail("plan --format json did not preserve suppressed count")
    plan_suppressed = plan_json.get("suppressed_findings")
    if not isinstance(plan_suppressed, list) or len(plan_suppressed) != 1:
        fail("plan --format json did not expose suppressed finding")
    if plan_json.get("recommended_actions") != []:
        fail("plan --format json recommended a suppressed finding")

    invalid_fixture = ROOT / "fixtures" / "invalid-ignore"
    try:
        lucid.audit(invalid_fixture, output_format="json")
    except SystemExit as exc:
        if "suppression 1 reason must be a non-empty string" not in str(exc):
            fail("invalid lucid.ignore.json error did not identify missing reason")
    else:
        fail("invalid lucid.ignore.json was accepted")

    invalid_version_fixtures = [
        ROOT / "fixtures" / "invalid-ignore-version-bool",
        ROOT / "fixtures" / "invalid-ignore-version-float",
    ]
    for invalid_version_fixture in invalid_version_fixtures:
        try:
            lucid.audit(invalid_version_fixture, output_format="json")
        except SystemExit as exc:
            if "lucid.ignore.json version must be 1" not in str(exc):
                fail(
                    f"{invalid_version_fixture.name} error did not identify "
                    "invalid version"
                )
        else:
            fail(f"{invalid_version_fixture.name} lucid.ignore.json was accepted")

    duplicate_fixture = ROOT / "fixtures" / "duplicate-ignore"
    try:
        lucid.audit(duplicate_fixture, output_format="json")
    except SystemExit as exc:
        if "duplicates rule/path" not in str(exc):
            fail("duplicate lucid.ignore.json error did not identify duplicate rule/path")
    else:
        fail("duplicate lucid.ignore.json was accepted")


def validate_diff_suggestions(lucid: ModuleType) -> None:
    fixture = ROOT / "fixtures" / "archive-autoload"
    agents = fixture / "AGENTS.md"
    before = agents.read_text(encoding="utf-8")

    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        exit_code = lucid.main(
            [
                "suggest",
                "--root",
                str(fixture),
            ]
        )
    if exit_code != 0:
        fail("suggest returned non-zero exit code")
    patch = stdout.getvalue()
    if "diff --git a/AGENTS.md b/AGENTS.md" not in patch:
        fail("suggest did not emit a git-style patch header")
    if "-Always read archive/ before every task." not in patch:
        fail("suggest did not include expected removed line")
    if agents.read_text(encoding="utf-8") != before:
        fail("suggest modified the target file")

    patch_file = fixture / ".lucid" / "suggested.patch"
    if not patch_file.exists():
        fail("suggest did not write .lucid/suggested.patch")
    if patch_file.read_text(encoding="utf-8") != patch:
        fail("suggested.patch did not match stdout patch")


def validate_sarif_output(lucid: ModuleType) -> None:
    fixture = ROOT / "fixtures" / "unsafe-context"

    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        exit_code = lucid.main(
            [
                "audit",
                "--root",
                str(fixture),
                "--format",
                "sarif",
                "--out",
                ".lucid/audit.sarif",
            ]
        )
    if exit_code != 0:
        fail("audit --format sarif returned non-zero exit code")

    sarif = json.loads(stdout.getvalue())
    if sarif.get("version") != "2.1.0":
        fail("audit --format sarif did not emit SARIF 2.1.0")
    if sarif.get("$schema") != "https://json.schemastore.org/sarif-2.1.0.json":
        fail("audit --format sarif did not include the SARIF schema URI")

    runs = sarif.get("runs")
    if not isinstance(runs, list) or len(runs) != 1:
        fail("audit --format sarif did not emit exactly one run")
    run = runs[0]
    results = run.get("results")
    if not isinstance(results, list) or len(results) != 1:
        fail("audit --format sarif did not emit one active result")
    result = results[0]
    if result.get("ruleId") != "unsafe-context":
        fail("audit --format sarif did not preserve the rule id")
    if result.get("level") != "error":
        fail("audit --format sarif did not map high severity to error")
    rules = run.get("tool", {}).get("driver", {}).get("rules", [])
    rule_ids = {rule.get("id") for rule in rules}
    if set(lucid.KNOWN_RULE_IDS) != rule_ids:
        fail("audit --format sarif did not expose all known rules in tool metadata")

    location = result.get("locations", [{}])[0].get("physicalLocation", {})
    artifact_uri = location.get("artifactLocation", {}).get("uri")
    region = location.get("region", {})
    if artifact_uri != "AGENTS.md":
        fail("audit --format sarif did not use a repo-relative artifact URI")
    if region.get("startLine") != 3 or region.get("endLine") != 3:
        fail("audit --format sarif did not preserve finding line range")

    serialized = json.dumps(sarif, ensure_ascii=False)
    if "sk_test_abcdefghijklmnopqrstuvwxyz123456" in serialized:
        fail("audit --format sarif exposed unsafe snippet")

    sarif_file = fixture / ".lucid" / "audit.sarif"
    if not sarif_file.exists():
        fail("audit --format sarif did not write .lucid/audit.sarif")
    if sarif_file.read_text(encoding="utf-8") != stdout.getvalue():
        fail("audit.sarif did not match stdout SARIF")

    suppressed_fixture = ROOT / "fixtures" / "ignore-suppressions"
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        exit_code = lucid.main(
            [
                "audit",
                "--root",
                str(suppressed_fixture),
                "--format",
                "sarif",
            ]
        )
    if exit_code != 0:
        fail("audit --format sarif returned non-zero exit code for suppressions")
    suppressed_sarif = json.loads(stdout.getvalue())
    suppressed_run = suppressed_sarif.get("runs", [{}])[0]
    if suppressed_run.get("results") != []:
        fail("audit --format sarif emitted suppressed findings as active results")
    summary = suppressed_run.get("properties", {}).get("summary", {})
    if summary.get("total") != 0 or summary.get("suppressed") != 1:
        fail("audit --format sarif did not preserve suppression summary")


def assert_scoring_consistent(audit: dict[str, object], label: str) -> None:
    findings = audit.get("findings")
    suppressed_findings = audit.get("suppressed_findings")
    summary = audit.get("summary")
    if not isinstance(findings, list) or not isinstance(suppressed_findings, list):
        fail(f"{label} audit did not expose finding lists")
    if not isinstance(summary, dict):
        fail(f"{label} audit did not expose summary")

    active_score = 0
    for finding in findings:
        score = finding.get("score_impact") if isinstance(finding, dict) else None
        if not isinstance(score, int) or score < 0:
            fail(f"{label} active finding is missing non-negative score_impact")
        active_score += score

    suppressed_score = 0
    for finding in suppressed_findings:
        score = finding.get("score_impact") if isinstance(finding, dict) else None
        if not isinstance(score, int) or score < 0:
            fail(f"{label} suppressed finding is missing non-negative score_impact")
        suppressed_score += score

    if summary.get("debt_score") != active_score:
        fail(f"{label} summary.debt_score did not match active findings")
    if summary.get("suppressed_debt_score") != suppressed_score:
        fail(f"{label} summary.suppressed_debt_score did not match suppressed findings")


def validate_debt_scoring(lucid: ModuleType) -> None:
    clean = lucid.audit(ROOT / "fixtures" / "clean-project", output_format="json")
    assert_scoring_consistent(clean, "clean-project")
    if clean["summary"]["debt_score"] != 0 or clean["summary"]["suppressed_debt_score"] != 0:
        fail("clean-project did not have zero debt scores")

    unsafe = lucid.audit(ROOT / "fixtures" / "unsafe-context", output_format="json")
    assert_scoring_consistent(unsafe, "unsafe-context")
    if unsafe["findings"][0].get("score_impact") != 13:
        fail("unsafe-context did not get expected high manual-review score")
    if unsafe["summary"]["debt_score"] != 13:
        fail("unsafe-context did not include expected debt_score")

    terminal_audit = lucid.render_terminal_audit(unsafe)
    if "Debt score: 13" not in terminal_audit:
        fail("terminal audit did not include debt score")
    expected_summary = (
        "Summary: active=1 debt=13 high=1 medium=0 low=0 manual_review=1 "
        "compatibility_protected=0 suppressed=0 suppressed_debt=0"
    )
    if expected_summary not in terminal_audit:
        fail("terminal audit did not include concise score summary")
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        exit_code = lucid.main(["audit", "--root", str(ROOT / "fixtures" / "unsafe-context")])
    if exit_code != 0:
        fail("audit terminal summary returned non-zero exit code")
    if expected_summary not in stdout.getvalue():
        fail("audit default terminal output did not include concise summary")

    compatibility = lucid.audit(
        ROOT / "fixtures" / "compatibility-safety", output_format="json"
    )
    assert_scoring_consistent(compatibility, "compatibility-safety")
    if compatibility["findings"][0].get("score_impact") != 3:
        fail("compatibility-risk score was not capped")

    suppressed = lucid.audit(ROOT / "fixtures" / "ignore-suppressions", output_format="json")
    assert_scoring_consistent(suppressed, "ignore-suppressions")
    if suppressed["summary"]["debt_score"] != 0:
        fail("suppressed finding counted as active debt")
    if suppressed["summary"]["suppressed_debt_score"] != 8:
        fail("suppressed finding did not preserve suppressed_debt_score")
    suppressed_terminal = lucid.render_terminal_audit(suppressed)
    expected_suppressed_summary = (
        "Summary: active=0 debt=0 high=0 medium=0 low=0 manual_review=0 "
        "compatibility_protected=0 suppressed=1 suppressed_debt=8"
    )
    if expected_suppressed_summary not in suppressed_terminal:
        fail("terminal audit did not summarize suppressed debt")

    markdown_plan = lucid.render_plan_markdown(unsafe)
    if "- Debt score: 13" not in markdown_plan:
        fail("markdown plan did not include debt score")
    if "- Score impact: 13" not in markdown_plan:
        fail("markdown plan did not include finding score impact")

    legacy_audit = json.loads(json.dumps(unsafe))
    legacy_audit["summary"].pop("debt_score", None)
    legacy_audit["summary"].pop("suppressed_debt_score", None)
    for finding in legacy_audit["findings"]:
        finding.pop("score_impact", None)
    legacy_plan = lucid.render_plan_markdown(legacy_audit)
    if "- Debt score: 13" not in legacy_plan:
        fail("legacy audit payload did not get scoring fields for plan rendering")

    plan_json = json.loads(lucid.render_plan_json(unsafe))
    if plan_json["recommended_actions"][0].get("score_impact") != 13:
        fail("plan JSON did not preserve score impact")

    sarif = json.loads(lucid.render_sarif(unsafe))
    result_properties = sarif["runs"][0]["results"][0]["properties"]
    if result_properties.get("score_impact") != 13:
        fail("SARIF did not preserve score impact")


def validate_cli_wrapper() -> None:
    if not LUCID_WRAPPER.exists():
        fail("lucid.py CLI wrapper is missing")
    spec = importlib.util.spec_from_file_location("lucid_cli_wrapper", LUCID_WRAPPER)
    if spec is None or spec.loader is None:
        fail("cannot load lucid.py CLI wrapper")
    wrapper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wrapper)

    fixture = ROOT / "fixtures" / "archive-autoload"
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        exit_code = wrapper.main(["scan", "--root", str(fixture), "--format", "json"])
    if exit_code != 0:
        fail("lucid.py wrapper returned non-zero exit code")
    scan_json = json.loads(stdout.getvalue())
    if scan_json.get("files_scanned") != 1:
        fail("lucid.py wrapper did not delegate scan output")
    paths = [item.get("path") for item in scan_json.get("files", [])]
    if paths != ["AGENTS.md"]:
        fail("lucid.py wrapper did not preserve delegated scan files")


def validate_ci_tool_checkout_is_skipped(lucid: ModuleType) -> None:
    if not lucid.is_skipped(ROOT / ".lucid-tool" / "AGENTS.md", ROOT):
        fail(".lucid-tool checkout directory was not skipped")


def main() -> int:
    if not CASES.exists():
        fail("evals/behavior-cases is missing")
    lucid = load_lucid()
    validate_ci_tool_checkout_is_skipped(lucid)

    case_paths = sorted(CASES.glob("*.json"))
    if not case_paths:
        fail("no behavior cases found")

    for case_path in case_paths:
        case = json.loads(case_path.read_text(encoding="utf-8"))
        fixture = ROOT / case["fixture"]
        if not fixture.exists():
            fail(f"{case_path.name} points to missing fixture {case['fixture']}")

        audit = lucid.audit(fixture, output_format="json")
        assert_scoring_consistent(audit, case["name"])
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
    validate_config_schema_validation(lucid)
    validate_policy_pack_loading(lucid)
    validate_source_graph(lucid)
    validate_stale_reference_provenance(lucid)
    validate_source_of_truth_provenance(lucid)
    validate_ignore_suppressions(lucid)
    validate_diff_suggestions(lucid)
    validate_sarif_output(lucid)
    validate_debt_scoring(lucid)
    validate_cli_wrapper()
    print("validate-evals: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
