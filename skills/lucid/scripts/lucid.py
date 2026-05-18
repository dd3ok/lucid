#!/usr/bin/env python3
"""Lucid read-only context hygiene scanner and planner."""

from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import json
import re
import sys
from pathlib import Path
from typing import Any


VERSION = "0.1.0"
ALLOWED_ACTIONS = {
    "remove",
    "replace-with-pointer",
    "move-to-reference",
    "move-to-validator",
    "move-to-eval",
    "keep-with-reason",
    "manual-review",
}
DEFAULT_CONFIG: dict[str, Any] = {
    "version": 1,
    "surfaces": {
        "always_loaded": [
            "AGENTS.md",
            "CLAUDE.md",
            "GEMINI.md",
            "MEMORY.md",
            "memory.md",
            "SOUL.md",
            "identity.md",
            ".cursorrules",
            ".github/copilot-instructions.md",
        ],
        "skill": [
            "skills/*/SKILL.md",
            "skills/*/references/**/*.md",
            "skills/*/examples/**/*.md",
            "skills/*/evals/**/*.md",
        ],
        "docs": [
            "README.md",
            "docs/**/*.md",
            "prompts/**/*.md",
            "templates/**/*.md",
            "examples/**/*.md",
        ],
    },
    "thresholds": {
        "always_loaded_max_lines": 120,
        "skill_md_max_lines": 120,
        "reference_max_lines": 500,
        "duplicate_similarity_min": 0.82,
    },
    "rules": {
        "stale_context": True,
        "over_specific_memory": True,
        "obsolete_identifier": True,
        "negative_residue": True,
        "source_of_truth_drift": True,
        "always_loaded_bloat": True,
        "stale_reference": True,
        "archive_autoload": True,
        "compatibility_risk": True,
        "unsafe_context": True,
    },
    "obsolete_identifiers": {
        "allow_in": [
            "fixtures/**",
            "evals/**",
            "skills/lucid/assets/default-rules.json",
        ],
        "deny_in": [
            "AGENTS.md",
            "CLAUDE.md",
            "GEMINI.md",
            "README.md",
            "skills/*/SKILL.md",
        ],
        "terms": [],
    },
    "compatibility_protected_patterns": [
        "schema",
        "migration",
        "compat",
        "legacy_alias",
        "api_version",
        "protocol",
        "backward-compatible",
    ],
    "write_policy": {
        "allowed_output_dir": ".lucid",
        "auto_apply": False,
        "allow_network": False,
        "allow_env_read": False,
    },
}
SKIP_DIRS = {
    ".git",
    ".lucid",
    ".local",
    ".venv",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}


def deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    result = json.loads(json.dumps(base))
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(root: Path) -> dict[str, Any]:
    config_path = root / "lucid.config.json"
    if not config_path.exists():
        return json.loads(json.dumps(DEFAULT_CONFIG))
    try:
        overlay = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid lucid.config.json: {exc}") from exc
    return deep_merge(DEFAULT_CONFIG, overlay)


def relpath(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def has_glob_magic(pattern: str) -> bool:
    return any(char in pattern for char in "*?[")


def is_skipped(path: Path, root: Path) -> bool:
    try:
        parts = path.resolve().relative_to(root.resolve()).parts
    except ValueError:
        return True
    return any(part in SKIP_DIRS for part in parts)


def matches_any(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)


def rule_enabled(config: dict[str, Any], key: str) -> bool:
    return bool((config.get("rules") or {}).get(key, True))


def read_text_safely(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None
    except OSError:
        return None


def estimate_tokens(text: str) -> int:
    return max(1, int(len(text) / 4))


def discover_context_surfaces(root: Path, config: dict[str, Any]) -> list[dict[str, Any]]:
    found: dict[Path, str] = {}
    surfaces = config["surfaces"]
    for category, patterns in surfaces.items():
        for pattern in patterns:
            if has_glob_magic(pattern):
                candidates = root.glob(pattern)
            else:
                candidates = [root / pattern]
            for candidate in candidates:
                if candidate.is_file() and not is_skipped(candidate, root):
                    found.setdefault(candidate, category)

    files: list[dict[str, Any]] = []
    for path, category in sorted(found.items(), key=lambda item: relpath(item[0], root)):
        text = read_text_safely(path)
        if text is None:
            continue
        files.append(
            {
                "path": relpath(path, root),
                "category": category,
                "lines": len(text.splitlines()),
                "estimated_tokens": estimate_tokens(text),
                "bytes": path.stat().st_size,
            }
        )
    return files


def scan(root: Path | str, output_format: str = "json") -> dict[str, Any]:
    root_path = Path(root).resolve()
    config = load_config(root_path)
    files = discover_context_surfaces(root_path, config)
    return {
        "version": VERSION,
        "root": str(root_path),
        "files_scanned": len(files),
        "files": files,
    }


def in_code_fence(line: str, state: dict[str, bool]) -> bool:
    stripped = line.strip()
    if stripped.startswith("```") or stripped.startswith("~~~"):
        state["inside"] = not state["inside"]
        return True
    return state["inside"]


def line_snippet(line: str) -> str:
    return line.strip()[:240]


def redact_unsafe_snippet(line: str) -> str:
    redacted = line.strip()
    redacted = re.sub(
        r"(?<![A-Za-z0-9_-])sk-(?:proj-)?[A-Za-z0-9_-]{20,}(?![A-Za-z0-9_-])",
        "[redacted]",
        redacted,
    )
    redacted = re.sub(
        r"(?<![A-Za-z0-9_-])sk_[A-Za-z0-9_=-]{12,}(?![A-Za-z0-9_-])",
        "[redacted]",
        redacted,
    )
    redacted = re.sub(r"AKIA[0-9A-Z]{16}", "[redacted]", redacted)
    redacted = re.sub(
        r"(api[_-]?key|token|password|secret)(\s*[:=]\s*)([\"'])(.{8,}?)\3",
        r"\1\2\3[redacted]\3",
        redacted,
        flags=re.I,
    )
    redacted = re.sub(
        r"(api[_-]?key|token|password|secret)(\s*[:=]\s*)\S{8,}",
        r"\1\2[redacted]",
        redacted,
        flags=re.I,
    )
    if "PRIVATE KEY-----" in redacted:
        return "[redacted private key]"
    return redacted[:240]


def make_finding(
    *,
    rule: str,
    severity: str,
    path: str,
    line_start: int,
    line_end: int,
    snippet: str,
    reason: str,
    suggested_action: str,
    confidence: float,
    requires_manual_review: bool = False,
    replacement_hint: str | None = None,
    source_of_truth: str | None = None,
) -> dict[str, Any]:
    if suggested_action not in ALLOWED_ACTIONS:
        raise ValueError(f"unsupported action: {suggested_action}")
    return {
        "id": "",
        "rule": rule,
        "severity": severity,
        "path": path,
        "line_start": line_start,
        "line_end": line_end,
        "snippet": snippet,
        "reason": reason,
        "suggested_action": suggested_action,
        "replacement_hint": replacement_hint,
        "source_of_truth": source_of_truth,
        "confidence": confidence,
        "requires_manual_review": requires_manual_review,
    }


def rule_always_loaded_bloat(
    file_info: dict[str, Any], config: dict[str, Any]
) -> list[dict[str, Any]]:
    if file_info["category"] != "always_loaded":
        return []
    max_lines = int(config["thresholds"].get("always_loaded_max_lines", 120))
    if file_info["lines"] <= max_lines:
        return []
    return [
        make_finding(
            rule="always-loaded-bloat",
            severity="medium",
            path=file_info["path"],
            line_start=max_lines + 1,
            line_end=file_info["lines"],
            snippet=f"{file_info['lines']} lines in always-loaded context",
            reason="Always-loaded context exceeds the configured line threshold.",
            suggested_action="move-to-reference",
            confidence=0.9,
            replacement_hint="Move durable detail into references and keep only pointers.",
        )
    ]


def rule_negative_residue(path: str, lines: list[str]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    negative = re.compile(
        r"\b(do not|don't|never|avoid|stop using|must not\s+(use|create|generate|write|call|run))\b|"
        r"금지|하지 말|쓰지 말|사용하지 말|생성하지 말",
        re.I,
    )
    old = re.compile(
        r"OLD_[A-Z0-9_]+|"
        r"\b(previous|old|deprecated|obsolete|legacy)\s+"
        r"(workflow|flow|artifact|file|identifier|command|process)\b|"
        r"이전\s*(방식|워크플로우|파일|명령)|"
        r"예전\s*(방식|워크플로우|파일|명령)",
        re.I,
    )
    fence = {"inside": False}
    for index, line in enumerate(lines, start=1):
        if in_code_fence(line, fence):
            continue
        if negative.search(line) and old.search(line):
            findings.append(
                make_finding(
                    rule="negative-residue",
                    severity="medium",
                    path=path,
                    line_start=index,
                    line_end=index,
                    snippet=line_snippet(line),
                    reason="Obsolete concept is preserved in user-facing context as a warning.",
                    suggested_action="replace-with-pointer",
                    confidence=0.82,
                    replacement_hint="Point to the current source of truth instead.",
                )
            )
    return findings


def rule_obsolete_identifier(
    path: str, lines: list[str], config: dict[str, Any]
) -> list[dict[str, Any]]:
    obsolete = config.get("obsolete_identifiers") or {}
    allow_in = obsolete.get("allow_in") or []
    deny_in = obsolete.get("deny_in") or []
    terms = list(obsolete.get("terms") or [])
    if matches_any(path, allow_in):
        return []
    configured = [re.escape(term) for term in terms]
    if matches_any(path, deny_in):
        configured.append(r"OLD_[A-Z0-9_]+")
    if not configured:
        return []
    pattern = re.compile("|".join(configured))
    findings: list[dict[str, Any]] = []
    fence = {"inside": False}
    for index, line in enumerate(lines, start=1):
        if in_code_fence(line, fence):
            continue
        if pattern.search(line):
            findings.append(
                make_finding(
                    rule="obsolete-identifier",
                    severity="medium",
                    path=path,
                    line_start=index,
                    line_end=index,
                    snippet=line_snippet(line),
                    reason="Old-looking identifier appears in agent-facing context.",
                    suggested_action="move-to-validator",
                    confidence=0.72,
                    replacement_hint="Keep old identifiers in validators or eval fixtures, not guidance.",
                )
            )
    return findings


def rule_compatibility_risk(
    path: str, lines: list[str], config: dict[str, Any]
) -> list[dict[str, Any]]:
    old = re.compile(r"\b(old|legacy|deprecated|backward-compatible)\b", re.I)
    protected = re.compile(
        "|".join(re.escape(term) for term in config["compatibility_protected_patterns"]),
        re.I,
    )
    concrete = re.compile(
        r"\blegacy_alias\b|\bapi_version\b|`[^`]*(?:old|legacy|deprecated)[^`]*`|"
        r"\brequired\b.*\bbackward-compatible\b",
        re.I,
    )
    findings: list[dict[str, Any]] = []
    fence = {"inside": False}
    for index, line in enumerate(lines, start=1):
        if in_code_fence(line, fence):
            continue
        if old.search(line) and protected.search(line) and concrete.search(line):
            findings.append(
                make_finding(
                    rule="compatibility-risk",
                    severity="medium",
                    path=path,
                    line_start=index,
                    line_end=index,
                    snippet=line_snippet(line),
                    reason="Old-looking content may be required for compatibility.",
                    suggested_action="keep-with-reason",
                    confidence=0.78,
                    requires_manual_review=True,
                    replacement_hint="Confirm integrations before removing this content.",
                )
            )
    return findings


def rule_stale_context(path: str, lines: list[str]) -> list[dict[str, Any]]:
    pattern = re.compile(
        r"\b(outdated instruction|stale instruction|deprecated instruction|obsolete instruction|"
        r"previous workflow|old workflow)\b",
        re.I,
    )
    findings: list[dict[str, Any]] = []
    fence = {"inside": False}
    for index, line in enumerate(lines, start=1):
        if in_code_fence(line, fence):
            continue
        if pattern.search(line):
            findings.append(
                make_finding(
                    rule="stale-context",
                    severity="medium",
                    path=path,
                    line_start=index,
                    line_end=index,
                    snippet=line_snippet(line),
                    reason="Instruction appears stale and may conflict with current source of truth.",
                    suggested_action="manual-review",
                    confidence=0.65,
                    requires_manual_review=True,
                )
            )
    return findings


def rule_over_specific_memory(path: str, lines: list[str]) -> list[dict[str, Any]]:
    if Path(path).name.lower() not in {"memory.md", "memory.txt", "memories.md"}:
        return []
    pattern = re.compile(
        r"\b(20\d{2}-\d{2}-\d{2}|yesterday|today|temporary|scratch|for that chat|single chat|one-off)\b",
        re.I,
    )
    findings: list[dict[str, Any]] = []
    for index, line in enumerate(lines, start=1):
        if pattern.search(line):
            findings.append(
                make_finding(
                    rule="over-specific-memory",
                    severity="medium",
                    path=path,
                    line_start=index,
                    line_end=index,
                    snippet=line_snippet(line),
                    reason="Memory looks one-off, temporary, or too specific for durable retention.",
                    suggested_action="manual-review",
                    confidence=0.76,
                    requires_manual_review=True,
                    replacement_hint="Apply the memory retention rubric before keeping it.",
                )
            )
    return findings


def candidate_reference_paths(line: str) -> list[str]:
    paths: list[str] = []
    for match in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", line):
        paths.append(match.group(1).split("#", 1)[0])
    for match in re.finditer(r"`([^`]+\.(?:md|txt|json|yaml|yml|py|sh))`", line):
        paths.append(match.group(1))
    return paths


def should_check_reference(candidate: str) -> bool:
    if not candidate:
        return False
    if candidate.startswith(("python ", "python3 ", "python -m ", "python3 -m ")):
        return False
    if re.match(r"^[a-z][a-z0-9+.-]*:", candidate, re.I):
        return False
    if candidate.startswith(("#", "~", "/", "<")):
        return False
    if candidate.startswith(".lucid/"):
        return False
    if any(char in candidate for char in "*?[]"):
        return False
    if "/" not in candidate and not candidate.startswith("."):
        return False
    return True


def reference_exists(root: Path, file_path: Path, candidate: str) -> bool:
    local = (file_path.parent / candidate).resolve()
    repo = (root / candidate).resolve()
    return local.exists() or repo.exists()


def rule_stale_reference(root: Path, path: str, lines: list[str]) -> list[dict[str, Any]]:
    if path.endswith("references/context-surfaces.md"):
        return []
    findings: list[dict[str, Any]] = []
    file_path = root / path
    fence = {"inside": False}
    for index, line in enumerate(lines, start=1):
        if in_code_fence(line, fence):
            continue
        for candidate in candidate_reference_paths(line):
            if should_check_reference(candidate) and not reference_exists(root, file_path, candidate):
                findings.append(
                    make_finding(
                        rule="stale-reference",
                        severity="low",
                        path=path,
                        line_start=index,
                        line_end=index,
                        snippet=line_snippet(line),
                        reason=f"Referenced local path does not exist: {candidate}",
                        suggested_action="manual-review",
                        confidence=0.7,
                        requires_manual_review=True,
                    )
                )
    return findings


def rule_archive_autoload(path: str, lines: list[str]) -> list[dict[str, Any]]:
    pattern = re.compile(
        r"\b(always|must|every task|before every task).*\b(read|load|include).*\b(archive|deprecated|old|backup)s?/|"
        r"\b(read|load|include).*\b(archive|deprecated|old|backup)s?/.*\b(always|every task)\b",
        re.I,
    )
    findings: list[dict[str, Any]] = []
    fence = {"inside": False}
    for index, line in enumerate(lines, start=1):
        if in_code_fence(line, fence):
            continue
        if pattern.search(line):
            findings.append(
                make_finding(
                    rule="archive-autoload",
                    severity="medium",
                    path=path,
                    line_start=index,
                    line_end=index,
                    snippet=line_snippet(line),
                    reason="Archive or deprecated content is being loaded by default.",
                    suggested_action="remove",
                    confidence=0.85,
                    replacement_hint="Load archives only on explicit request or from eval fixtures.",
                )
            )
    return findings


def rule_unsafe_context(path: str, lines: list[str]) -> list[dict[str, Any]]:
    patterns = [
        re.compile(r"(?<![A-Za-z0-9_-])sk-(?:proj-)?[A-Za-z0-9_-]{20,}(?![A-Za-z0-9_-])"),
        re.compile(r"(?<![A-Za-z0-9_-])sk_[A-Za-z0-9_=-]{12,}(?![A-Za-z0-9_-])"),
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
        re.compile(r"\b(api[_-]?key|token|password|secret)\s*[:=]\s*[\"'][^\"']{16,}[\"']", re.I),
        re.compile(r"[\u200b\u200c\u200d\ufeff]"),
        re.compile(r"\brm\s+-rf\s+[/~$]"),
    ]
    findings: list[dict[str, Any]] = []
    fence = {"inside": False}
    for index, line in enumerate(lines, start=1):
        if in_code_fence(line, fence):
            continue
        if any(pattern.search(line) for pattern in patterns):
            findings.append(
                make_finding(
                    rule="unsafe-context",
                    severity="high",
                    path=path,
                    line_start=index,
                    line_end=index,
                    snippet=redact_unsafe_snippet(line),
                    reason="Context contains secret-like, hidden, or dangerous content.",
                    suggested_action="manual-review",
                    confidence=0.82,
                    requires_manual_review=True,
                    replacement_hint="Remove sensitive values and rotate credentials if real.",
                )
            )
    return findings


def rule_source_of_truth_drift(file_texts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    entries: dict[str, list[tuple[str, int, str]]] = {}
    pattern = re.compile(r"^\s*(canonical workflow|current workflow|source of truth)\s*:\s*(.+?)\s*$", re.I)
    validation_commands: dict[str, list[tuple[int, str]]] = {}
    for file_text in file_texts:
        fence = {"inside": False}
        in_validation_section = False
        in_command_block = False
        for index, line in enumerate(file_text["text"].splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                in_validation_section = "validation" in stripped.lower()
            if in_validation_section:
                if stripped.startswith("```"):
                    language = stripped.strip("`").lower()
                    in_command_block = not in_command_block and language in {"bash", "sh", "shell", ""}
                command_line = stripped
                if command_line.startswith(("-", "*")):
                    command_line = command_line[1:].strip()
                command_match = None
                if in_command_block or stripped.startswith(("-", "*")):
                    command_match = re.match(
                        r"python3\s+scripts/[A-Za-z0-9_.-]*(?:validate|check)[A-Za-z0-9_.-]*\.py\b",
                        command_line,
                    )
                if command_match:
                    validation_commands.setdefault(file_text["path"], []).append(
                        (index, command_match.group(0))
                    )
            if in_code_fence(line, fence):
                continue
            match = pattern.match(line)
            if not match:
                continue
            key = match.group(1).strip().lower()
            value = match.group(2).strip()
            entries.setdefault(key, []).append((file_text["path"], index, value))

    command_sets = {
        path: tuple(command for _, command in commands)
        for path, commands in validation_commands.items()
        if commands
    }
    if len(command_sets) >= 2 and len(set(command_sets.values())) > 1:
        for path, commands in validation_commands.items():
            if not commands:
                continue
            entries.setdefault("validation command set", []).append(
                (path, commands[0][0], " && ".join(command for _, command in commands))
            )

    findings: list[dict[str, Any]] = []
    for key, values in entries.items():
        if len({path for path, _, _ in values}) < 2:
            continue
        distinct = {value.lower() for _, _, value in values}
        if len(distinct) < 2:
            continue
        for path, index, value in values:
            findings.append(
                make_finding(
                    rule="source-of-truth-drift",
                    severity="medium",
                    path=path,
                    line_start=index,
                    line_end=index,
                    snippet=f"{key}: {value}",
                    reason="Multiple source-of-truth declarations disagree.",
                    suggested_action="replace-with-pointer",
                    confidence=0.8,
                    requires_manual_review=True,
                    replacement_hint="Keep one canonical statement and replace duplicates with pointers.",
                )
            )
    return findings


def audit(root: Path | str, output_format: str = "json") -> dict[str, Any]:
    root_path = Path(root).resolve()
    config = load_config(root_path)
    scan_result = scan(root_path, output_format=output_format)
    findings: list[dict[str, Any]] = []
    file_texts: list[dict[str, Any]] = []

    for file_info in scan_result["files"]:
        path = root_path / file_info["path"]
        text = read_text_safely(path)
        if text is None:
            continue
        lines = text.splitlines()
        file_texts.append({"path": file_info["path"], "text": text})

        if rule_enabled(config, "always_loaded_bloat"):
            findings.extend(rule_always_loaded_bloat(file_info, config))
        if rule_enabled(config, "compatibility_risk"):
            findings.extend(rule_compatibility_risk(file_info["path"], lines, config))
        if rule_enabled(config, "negative_residue"):
            findings.extend(rule_negative_residue(file_info["path"], lines))
        if rule_enabled(config, "obsolete_identifier"):
            findings.extend(rule_obsolete_identifier(file_info["path"], lines, config))
        if rule_enabled(config, "stale_context"):
            findings.extend(rule_stale_context(file_info["path"], lines))
        if rule_enabled(config, "over_specific_memory"):
            findings.extend(rule_over_specific_memory(file_info["path"], lines))
        if rule_enabled(config, "stale_reference"):
            findings.extend(rule_stale_reference(root_path, file_info["path"], lines))
        if rule_enabled(config, "archive_autoload"):
            findings.extend(rule_archive_autoload(file_info["path"], lines))
        if rule_enabled(config, "unsafe_context"):
            findings.extend(rule_unsafe_context(file_info["path"], lines))

    if rule_enabled(config, "source_of_truth_drift"):
        findings.extend(rule_source_of_truth_drift(file_texts))
    findings.sort(key=lambda item: (item["path"], item["line_start"], item["rule"]))
    for index, finding in enumerate(findings, start=1):
        finding["id"] = f"LUCID-{index:04d}"

    return {
        "version": VERSION,
        "root": str(root_path),
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "files_scanned": scan_result["files_scanned"],
        "findings": findings,
        "summary": summarize_findings(findings),
    }


def summarize_findings(findings: list[dict[str, Any]]) -> dict[str, int]:
    summary = {
        "total": len(findings),
        "high": 0,
        "medium": 0,
        "low": 0,
        "manual_review": 0,
        "compatibility_protected": 0,
    }
    for finding in findings:
        severity = str(finding["severity"])
        if severity in summary:
            summary[severity] += 1
        if finding["requires_manual_review"]:
            summary["manual_review"] += 1
        if finding["rule"] == "compatibility-risk":
            summary["compatibility_protected"] += 1
    return summary


def render_terminal_scan(result: dict[str, Any]) -> str:
    lines = [
        "Lucid scan",
        f"Root: {result['root']}",
        f"Files scanned: {result['files_scanned']}",
        "",
    ]
    for file_info in result["files"]:
        lines.append(
            f"- {file_info['path']} ({file_info['category']}, "
            f"{file_info['lines']} lines, ~{file_info['estimated_tokens']} tokens)"
        )
    return "\n".join(lines)


def render_terminal_audit(result: dict[str, Any]) -> str:
    lines = [
        "Lucid audit",
        f"Root: {result['root']}",
        f"Files scanned: {result['files_scanned']}",
        f"Findings: {result['summary']['total']}",
        "",
    ]
    for finding in result["findings"]:
        lines.append(
            f"- {finding['id']} {finding['rule']} {finding['severity']} "
            f"{finding['path']}:{finding['line_start']} -> {finding['suggested_action']}"
        )
        lines.append(f"  {finding['reason']}")
    return "\n".join(lines)


def render_plan_markdown(audit_result: dict[str, Any]) -> str:
    summary = audit_result["summary"]
    lines = [
        "# Lucid Context Hygiene Plan",
        "",
        "## Summary",
        "",
        f"- Root: `{audit_result['root']}`",
        f"- Files scanned: {audit_result['files_scanned']}",
        f"- Findings: {summary['total']}",
        f"- High severity: {summary['high']}",
        f"- Manual review: {summary['manual_review']}",
        f"- Compatibility-protected: {summary['compatibility_protected']}",
        f"- Generated at: {audit_result['generated_at']}",
        "",
        "## Recommended Actions",
        "",
    ]
    if not audit_result["findings"]:
        lines.append("No findings.")
        lines.append("")
        return "\n".join(lines)

    for finding in audit_result["findings"]:
        title = finding["reason"].rstrip(".")
        lines.extend(
            [
                f"### {finding['id']} - {title}",
                "",
                f"- Rule: `{finding['rule']}`",
                f"- Severity: `{finding['severity']}`",
                f"- Path: `{finding['path']}`",
                f"- Lines: {finding['line_start']}-{finding['line_end']}",
                "- Current snippet:",
                "",
                "```text",
                str(finding["snippet"]),
                "```",
                "",
                f"- Suggested action: `{finding['suggested_action']}`",
                f"- Confidence: {finding['confidence']:.2f}",
                f"- Manual review: {str(finding['requires_manual_review']).lower()}",
            ]
        )
        if finding.get("replacement_hint"):
            lines.append(f"- Replacement hint: {finding['replacement_hint']}")
        if finding.get("source_of_truth"):
            lines.append(f"- Source of truth: {finding['source_of_truth']}")
        if finding["rule"] == "compatibility-risk":
            lines.extend(
                [
                    "- Compatibility note:",
                    "  - Why it looks stale: It uses old-looking or legacy compatibility wording.",
                    "  - Why it may still be required: It may be part of schema, protocol, migration, or integration compatibility.",
                    "  - Evidence needed before removal: Confirm current consumers, migrations, protocol versions, and regression tests.",
                ]
            )
        lines.extend(
            [
                "- Safety: Non-destructive. Requires user approval before editing.",
                "",
            ]
        )
    return "\n".join(lines)


def safe_write_lucid_output(root: Path, out: str, content: str) -> Path:
    root_resolved = root.resolve()
    allowed_dir = (root_resolved / ".lucid").resolve()
    out_path = Path(out)
    if not out_path.is_absolute():
        out_path = root_resolved / out_path
    out_resolved = out_path.resolve()
    if not out_resolved.is_relative_to(allowed_dir):
        raise SystemExit("refusing to write outside .lucid/")
    allowed_dir.mkdir(parents=True, exist_ok=True)
    out_resolved.parent.mkdir(parents=True, exist_ok=True)
    out_resolved.write_text(content, encoding="utf-8")
    return out_resolved


def safe_read_lucid_input(root: Path, candidate: str) -> Path:
    root_resolved = root.resolve()
    allowed_dir = (root_resolved / ".lucid").resolve()
    input_path = Path(candidate)
    if not input_path.is_absolute():
        input_path = root_resolved / input_path
    input_resolved = input_path.resolve()
    if not input_resolved.is_relative_to(allowed_dir):
        raise SystemExit("refusing to read audit input outside .lucid/")
    return input_resolved


def render_json(result: dict[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def load_audit_for_plan(root: Path, audit_path: str | None) -> dict[str, Any]:
    if audit_path is None:
        return audit(root, output_format="json")
    path = safe_read_lucid_input(root, audit_path)
    return json.loads(path.read_text(encoding="utf-8"))


def verify(root: Path | str, strict: bool = False) -> dict[str, Any]:
    root_path = Path(root).resolve()
    audit_result = audit(root_path, output_format="json")
    errors: list[str] = []

    skill = root_path / "skills" / "lucid" / "SKILL.md"
    agents = root_path / "AGENTS.md"
    script = root_path / "skills" / "lucid" / "scripts" / "lucid.py"
    if not skill.exists():
        errors.append("missing skills/lucid/SKILL.md")
    if not script.exists():
        errors.append("missing skills/lucid/scripts/lucid.py")
    if agents.exists() and len(agents.read_text(encoding="utf-8").splitlines()) > 80:
        errors.append("AGENTS.md exceeds 80 lines")
    if skill.exists() and len(skill.read_text(encoding="utf-8").splitlines()) > 120:
        errors.append("skills/lucid/SKILL.md exceeds 120 lines")

    for finding in audit_result["findings"]:
        if finding["suggested_action"] not in ALLOWED_ACTIONS:
            errors.append(f"{finding['id']} uses unsupported action {finding['suggested_action']}")
        if strict and finding["severity"] == "high" and not matches_any(
            finding["path"], ["fixtures/**", "evals/**"]
        ):
            errors.append(f"{finding['id']} high severity finding requires review")

    return {
        "ok": not errors,
        "strict": strict,
        "errors": errors,
        "audit_summary": audit_result["summary"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lucid.py")
    parser.add_argument("--version", action="version", version=f"lucid {VERSION}")
    subcommands = parser.add_subparsers(dest="command", required=True)

    scan_parser = subcommands.add_parser("scan", help="List agent-facing context surfaces")
    scan_parser.add_argument("--root", default=".")
    scan_parser.add_argument("--format", choices=["json", "terminal"], default="terminal")
    scan_parser.add_argument("--out")

    audit_parser = subcommands.add_parser("audit", help="Audit context hygiene findings")
    audit_parser.add_argument("--root", default=".")
    audit_parser.add_argument("--format", choices=["json", "terminal"], default="terminal")
    audit_parser.add_argument("--out")

    plan_parser = subcommands.add_parser("plan", help="Render a cleanup plan")
    plan_parser.add_argument("--root", default=".")
    plan_parser.add_argument("--audit")
    plan_parser.add_argument("--out", default=".lucid/plan.md")

    verify_parser = subcommands.add_parser("verify", help="Verify Lucid package constraints")
    verify_parser.add_argument("--root", default=".")
    verify_parser.add_argument("--strict", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve()

    if args.command == "scan":
        result = scan(root, output_format=args.format)
        content = render_json(result) if args.format == "json" else render_terminal_scan(result)
        if args.out:
            safe_write_lucid_output(root, args.out, content)
        print(content, end="" if content.endswith("\n") else "\n")
        return 0

    if args.command == "audit":
        result = audit(root, output_format=args.format)
        content = render_json(result) if args.format == "json" else render_terminal_audit(result)
        if args.out:
            safe_write_lucid_output(root, args.out, content)
        print(content, end="" if content.endswith("\n") else "\n")
        return 0

    if args.command == "plan":
        audit_result = load_audit_for_plan(root, args.audit)
        content = render_plan_markdown(audit_result)
        safe_write_lucid_output(root, args.out, content)
        print(content, end="" if content.endswith("\n") else "\n")
        return 0

    if args.command == "verify":
        result = verify(root, strict=args.strict)
        print(render_json(result), end="")
        return 0 if result["ok"] else 1

    raise SystemExit(f"unknown command {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
