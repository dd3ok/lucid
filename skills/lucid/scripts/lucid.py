#!/usr/bin/env python3
"""Lucid read-only context hygiene scanner and planner."""

from __future__ import annotations

import argparse
import datetime as dt
import difflib
import fnmatch
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any


VERSION = "0.2.2"
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
PLAN_SAFETY_NOTE = "Non-destructive. Requires user approval before editing."
PLAN_COMPATIBILITY_NOTE = {
    "why_it_looks_stale": "It uses old-looking or legacy compatibility wording.",
    "why_it_may_still_be_required": (
        "It may be part of schema, protocol, migration, or integration compatibility."
    ),
    "evidence_needed_before_removal": (
        "Confirm current consumers, migrations, protocol versions, and regression tests."
    ),
}
KNOWN_RULE_IDS = {rule.replace("_", "-") for rule in DEFAULT_CONFIG["rules"]}
CONFIG_TOP_LEVEL_KEYS = set(DEFAULT_CONFIG)
SEVERITY_SCORE_IMPACT = {
    "high": 10,
    "medium": 5,
    "low": 2,
}
MANUAL_REVIEW_SCORE_IMPACT = 3
COMPATIBILITY_RISK_SCORE_CAP = 3
PATCH_ELIGIBLE_RULES = {
    "archive-autoload",
}
SKIP_DIRS = {
    ".git",
    ".lucid",
    ".lucid-tool",
    ".local",
    ".venv",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}
HIDDEN_UNICODE_PATTERN = re.compile(r"[\u200b\u200c\u200d\ufeff]")
SK_DASH_TOKEN_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_-])sk-(?:proj-)?[A-Za-z0-9_-]{20,}(?![A-Za-z0-9_-])"
)
SK_UNDERSCORE_TOKEN_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_-])sk_[A-Za-z0-9_=-]{12,}(?![A-Za-z0-9_-])"
)
AWS_ACCESS_KEY_PATTERN = re.compile(r"AKIA[0-9A-Z]{16}")
PRIVATE_KEY_MARKER_PATTERN = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
NAMED_SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"\b(api[_-]?key|token|password|secret)\s*[:=]\s*(?:[\"'][^\"']{16,}[\"']|\S{16,})",
    re.I,
)
SECRET_OR_HIDDEN_UNSAFE_PATTERNS = [
    SK_DASH_TOKEN_PATTERN,
    SK_UNDERSCORE_TOKEN_PATTERN,
    AWS_ACCESS_KEY_PATTERN,
    PRIVATE_KEY_MARKER_PATTERN,
    NAMED_SECRET_ASSIGNMENT_PATTERN,
    HIDDEN_UNICODE_PATTERN,
]
CONTEXTUAL_UNSAFE_PATTERNS = [
    re.compile(r"\brm\s+-rf\s+[/~$]"),
]
ALL_UNSAFE_PATTERNS = SECRET_OR_HIDDEN_UNSAFE_PATTERNS + CONTEXTUAL_UNSAFE_PATTERNS
POLICY_DRIFT_TERMS = {
    "agent",
    "audit",
    "canonical",
    "cleanup",
    "context",
    "instruction",
    "memory",
    "plan",
    "policy",
    "prompt",
    "reference",
    "rule",
    "skill",
    "source",
    "truth",
    "verify",
    "workflow",
}
SKIP_NEAR_DUPLICATE_HEADINGS = {
    "changelog",
    "commands",
    "install",
    "installation",
    "quick start",
    "roadmap",
    "usage",
    "validation",
}
BARE_REFERENCE_FILENAMES = {
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    "README.md",
    "memory.md",
    "MEMORY.md",
}
BARE_REFERENCE_FILENAME_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_./-])"
    r"(?:" + "|".join(re.escape(name) for name in sorted(BARE_REFERENCE_FILENAMES)) + r")"
    r"(?![A-Za-z0-9_.-])"
)
REFERENCE_INTENT_PATTERN = re.compile(
    r"\b(read|load|open|check|review|consult|follow|see|refer(?:red|s|ring)?\s+to)\b",
    re.I,
)


def deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    result = json.loads(json.dumps(base))
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def resolve_config_path(root: Path, config_path: str | None) -> Path:
    root_resolved = root.resolve()
    candidate = Path(config_path) if config_path is not None else root_resolved / "lucid.config.json"
    if not candidate.is_absolute():
        candidate = root_resolved / candidate
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root_resolved):
        raise SystemExit(f"refusing to read config outside target root: {resolved}")
    return resolved


def require_config_object(value: Any, label: str, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SystemExit(f"invalid {label}: {path} must be an object")
    return value


def require_config_string_list(value: Any, label: str, path: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise SystemExit(f"invalid {label}: {path} must be a list of strings")
    return value


def validate_known_config_keys(
    data: dict[str, Any], label: str, path: str, known_keys: set[str]
) -> None:
    for key in sorted(set(data) - known_keys):
        if path:
            raise SystemExit(f"invalid {label}: unknown {path} key: {key}")
        raise SystemExit(f"invalid {label}: unknown top-level config key: {key}")


def validate_string_list_mapping(
    value: Any, label: str, path: str, known_keys: set[str]
) -> None:
    mapping = require_config_object(value, label, path)
    validate_known_config_keys(mapping, label, path, known_keys)
    for key, items in mapping.items():
        require_config_string_list(items, label, f"{path}.{key}")


def validate_thresholds(value: Any, label: str) -> None:
    thresholds = require_config_object(value, label, "thresholds")
    validate_known_config_keys(
        thresholds, label, "thresholds", set(DEFAULT_CONFIG["thresholds"])
    )
    for key, threshold in thresholds.items():
        if not isinstance(threshold, (int, float)) or isinstance(threshold, bool):
            raise SystemExit(f"invalid {label}: thresholds.{key} must be a number")


def validate_rules(value: Any, label: str) -> None:
    rules = require_config_object(value, label, "rules")
    validate_known_config_keys(rules, label, "rules", set(DEFAULT_CONFIG["rules"]))
    for key, enabled in rules.items():
        if not isinstance(enabled, bool):
            raise SystemExit(f"invalid {label}: rules.{key} must be a boolean")


def validate_write_policy(value: Any, label: str) -> None:
    write_policy = require_config_object(value, label, "write_policy")
    validate_known_config_keys(
        write_policy, label, "write_policy", set(DEFAULT_CONFIG["write_policy"])
    )
    for key, setting in write_policy.items():
        if key == "allowed_output_dir":
            if not isinstance(setting, str) or not setting:
                raise SystemExit(
                    f"invalid {label}: write_policy.allowed_output_dir "
                    "must be a non-empty string"
                )
            continue
        if not isinstance(setting, bool):
            raise SystemExit(f"invalid {label}: write_policy.{key} must be a boolean")


def validate_config_overlay(overlay: Any, label: str) -> dict[str, Any]:
    config = require_config_object(overlay, label, "config")
    validate_known_config_keys(config, label, "", CONFIG_TOP_LEVEL_KEYS)
    version = config.get("version")
    if type(version) is not int or version != 1:
        raise SystemExit(f"invalid {label}: version must be 1")

    if "surfaces" in config:
        validate_string_list_mapping(
            config["surfaces"], label, "surfaces", set(DEFAULT_CONFIG["surfaces"])
        )
    if "thresholds" in config:
        validate_thresholds(config["thresholds"], label)
    if "rules" in config:
        validate_rules(config["rules"], label)
    if "obsolete_identifiers" in config:
        validate_string_list_mapping(
            config["obsolete_identifiers"],
            label,
            "obsolete_identifiers",
            set(DEFAULT_CONFIG["obsolete_identifiers"]),
        )
    if "compatibility_protected_patterns" in config:
        require_config_string_list(
            config["compatibility_protected_patterns"],
            label,
            "compatibility_protected_patterns",
        )
    if "write_policy" in config:
        validate_write_policy(config["write_policy"], label)

    return config


def load_config(root: Path, config_path: str | None = None) -> dict[str, Any]:
    config_file = resolve_config_path(root, config_path)
    if config_path is not None and not config_file.exists():
        raise SystemExit(f"config file not found: {config_path}")
    if not config_file.exists():
        return json.loads(json.dumps(DEFAULT_CONFIG))
    if not config_file.is_file():
        raise SystemExit(f"config path is not a file: {config_path or 'lucid.config.json'}")
    try:
        overlay = json.loads(config_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        label = config_path or "lucid.config.json"
        raise SystemExit(f"invalid {label}: {exc}") from exc
    label = config_path or "lucid.config.json"
    validate_config_overlay(overlay, label)
    return deep_merge(DEFAULT_CONFIG, overlay)


def load_ignore_suppressions(root: Path) -> list[dict[str, str]]:
    ignore_file = root.resolve() / "lucid.ignore.json"
    if not ignore_file.exists():
        return []
    if not ignore_file.is_file():
        raise SystemExit("lucid.ignore.json path is not a file")
    try:
        data = json.loads(ignore_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid lucid.ignore.json: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit("lucid.ignore.json must be a JSON object")
    if data.get("version") != 1:
        raise SystemExit("lucid.ignore.json version must be 1")
    suppressions = data.get("suppressions", [])
    if not isinstance(suppressions, list):
        raise SystemExit("lucid.ignore.json suppressions must be a list")

    validated: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for index, suppression in enumerate(suppressions, start=1):
        if not isinstance(suppression, dict):
            raise SystemExit(f"lucid.ignore.json suppression {index} must be an object")
        rule = suppression.get("rule")
        path = suppression.get("path")
        reason = suppression.get("reason")
        if not isinstance(rule, str) or not rule.strip():
            raise SystemExit(
                f"lucid.ignore.json suppression {index} rule must be a non-empty string"
            )
        rule = rule.strip()
        if rule not in KNOWN_RULE_IDS:
            raise SystemExit(f"lucid.ignore.json suppression {index} has unknown rule: {rule}")
        if not isinstance(path, str) or not path.strip():
            raise SystemExit(
                f"lucid.ignore.json suppression {index} path must be a non-empty string"
            )
        if not isinstance(reason, str) or not reason.strip():
            raise SystemExit(
                f"lucid.ignore.json suppression {index} reason must be a non-empty string"
            )
        normalized_path = normalize_repo_path(
            path.strip(), f"lucid.ignore.json suppression {index} path"
        )
        key = (rule, normalized_path)
        if key in seen:
            raise SystemExit(
                f"lucid.ignore.json suppression {index} duplicates rule/path: "
                f"{rule} {normalized_path}"
            )
        seen.add(key)
        validated.append(
            {
                "rule": rule,
                "path": normalized_path,
                "reason": reason.strip(),
            }
        )
    return validated


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


def normalize_repo_path(path: str, label: str) -> str:
    normalized = path.replace("\\", "/")
    candidate = PurePosixPath(normalized)
    if (
        not normalized
        or candidate.is_absolute()
        or candidate.as_posix() == "."
        or ".." in candidate.parts
    ):
        raise SystemExit(f"{label} must be a repository-relative path: {path}")
    return candidate.as_posix()


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


def scan(
    root: Path | str,
    output_format: str = "json",
    config_path: str | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root_path = Path(root).resolve()
    if config is None:
        config = load_config(root_path, config_path)
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
    redacted = HIDDEN_UNICODE_PATTERN.sub("[hidden-unicode]", redacted)
    redacted = SK_DASH_TOKEN_PATTERN.sub("[redacted]", redacted)
    redacted = SK_UNDERSCORE_TOKEN_PATTERN.sub("[redacted]", redacted)
    redacted = AWS_ACCESS_KEY_PATTERN.sub("[redacted]", redacted)
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


def unique_preserve_order(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def is_bare_reference_filename(candidate: str) -> bool:
    return (
        "/" not in candidate
        and not candidate.startswith(".")
        and candidate in BARE_REFERENCE_FILENAMES
    )


def candidate_reference_paths(line: str) -> list[str]:
    paths: list[str] = []
    has_reference_intent = bool(REFERENCE_INTENT_PATTERN.search(line))
    for match in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", line):
        target_parts = match.group(1).strip().split(None, 1)
        if target_parts:
            paths.append(target_parts[0].split("#", 1)[0])
    for match in re.finditer(r"`([^`]+\.(?:md|txt|json|yaml|yml|py|sh))`", line):
        candidate = match.group(1)
        if is_bare_reference_filename(candidate) and not has_reference_intent:
            continue
        paths.append(candidate)
    if has_reference_intent:
        for match in BARE_REFERENCE_FILENAME_PATTERN.finditer(line):
            paths.append(match.group(0))
    return unique_preserve_order(paths)


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
    if (
        "/" not in candidate
        and not candidate.startswith(".")
        and not is_bare_reference_filename(candidate)
    ):
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
    findings: list[dict[str, Any]] = []
    fence = {"inside": False}
    for index, line in enumerate(lines, start=1):
        inside_fence = in_code_fence(line, fence)
        patterns = SECRET_OR_HIDDEN_UNSAFE_PATTERNS if inside_fence else ALL_UNSAFE_PATTERNS
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


def normalize_policy_text(text: str) -> str:
    normalized = text.lower()
    normalized = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 \2", normalized)
    normalized = normalized.replace("`", "")
    normalized = re.sub(r"[*_>#|]+", " ", normalized)
    normalized = re.sub(r"[^a-z0-9_./-]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def word_shingles(text: str, n: int = 5) -> set[tuple[str, ...]]:
    words = text.split()
    if len(words) < n:
        return set()
    return {tuple(words[index : index + n]) for index in range(len(words) - n + 1)}


def jaccard_similarity(left: set[tuple[str, ...]], right: set[tuple[str, ...]]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def is_skipped_near_duplicate_heading(heading: str) -> bool:
    normalized = heading.strip().lower().lstrip("#").strip()
    return any(term in normalized for term in SKIP_NEAR_DUPLICATE_HEADINGS)


def is_policy_like_block(normalized: str) -> bool:
    words = normalized.split()
    if len(words) < 25:
        return False
    terms = {word.strip("./-") for word in words}
    return len(terms & POLICY_DRIFT_TERMS) >= 2


def should_skip_policy_block(lines: list[str], heading: str) -> bool:
    if is_skipped_near_duplicate_heading(heading):
        return True
    meaningful = [line.strip() for line in lines if line.strip()]
    if not meaningful:
        return True
    list_like = sum(
        1
        for line in meaningful
        if line.startswith(("-", "*", "|"))
        or re.match(r"^\d+[.)]\s+", line)
    )
    if list_like and list_like >= max(1, int(len(meaningful) * 0.5)):
        return True
    return all(
        line.startswith(("python ", "python3 ", "$ ", "./"))
        or re.match(r"^[A-Za-z0-9_-]+=.+", line)
        for line in meaningful
    )


def extract_policy_blocks(path: str, text: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    heading = ""
    pending: list[tuple[int, str]] = []
    fence = {"inside": False}

    def flush() -> None:
        if not pending:
            return
        line_start = pending[0][0]
        line_end = pending[-1][0]
        block_lines = [line for _, line in pending]
        block_text = "\n".join(block_lines).strip()
        pending.clear()
        if should_skip_policy_block(block_lines, heading):
            return
        normalized = normalize_policy_text(block_text)
        if not is_policy_like_block(normalized):
            return
        shingles = word_shingles(normalized, 5)
        blocks.append(
            {
                "path": path,
                "line_start": line_start,
                "line_end": line_end,
                "text": block_text,
                "shingles": shingles,
            }
        )

    for index, line in enumerate(text.splitlines(), start=1):
        if in_code_fence(line, fence):
            flush()
            continue
        stripped = line.strip()
        if stripped.startswith("#"):
            flush()
            heading = stripped.lstrip("#").strip()
            continue
        if not stripped:
            flush()
            continue
        pending.append((index, line))
    flush()
    return blocks


def rule_near_duplicate_source_of_truth_drift(
    file_texts: list[dict[str, Any]], config: dict[str, Any]
) -> list[dict[str, Any]]:
    threshold_raw = (config.get("thresholds") or {}).get(
        "duplicate_similarity_min", 0.82
    )
    try:
        threshold = max(0.0, min(1.0, float(threshold_raw)))
    except (TypeError, ValueError):
        threshold = 0.82
    blocks: list[dict[str, Any]] = []
    for file_text in file_texts:
        blocks.extend(extract_policy_blocks(file_text["path"], file_text["text"]))

    best_matches: dict[tuple[str, int, int], tuple[float, dict[str, Any]]] = {}
    for left_index, left in enumerate(blocks):
        for right in blocks[left_index + 1 :]:
            if left["path"] == right["path"]:
                continue
            score = jaccard_similarity(left["shingles"], right["shingles"])
            if score < threshold:
                continue
            left_key = (left["path"], left["line_start"], left["line_end"])
            right_key = (right["path"], right["line_start"], right["line_end"])
            if score > best_matches.get(left_key, (0.0, {}))[0]:
                best_matches[left_key] = (score, right)
            if score > best_matches.get(right_key, (0.0, {}))[0]:
                best_matches[right_key] = (score, left)

    findings: list[dict[str, Any]] = []
    by_key = {
        (block["path"], block["line_start"], block["line_end"]): block
        for block in blocks
    }
    for key in sorted(best_matches):
        block = by_key[key]
        score, other = best_matches[key]
        findings.append(
            make_finding(
                rule="source-of-truth-drift",
                severity="medium",
                path=block["path"],
                line_start=block["line_start"],
                line_end=block["line_end"],
                snippet=line_snippet(block["text"]),
                reason="Similar source-of-truth or workflow guidance appears in multiple places.",
                suggested_action="replace-with-pointer",
                confidence=round(score, 2),
                requires_manual_review=True,
                replacement_hint="Choose the canonical source, then replace duplicate policy text with pointers.",
                source_of_truth=(
                    f"candidate duplicate: {other['path']}:"
                    f"{other['line_start']}-{other['line_end']}"
                ),
            )
        )
    return findings


def rule_source_of_truth_drift(
    file_texts: list[dict[str, Any]], config: dict[str, Any]
) -> list[dict[str, Any]]:
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
    findings.extend(rule_near_duplicate_source_of_truth_drift(file_texts, config))
    return findings


def apply_suppressions(
    findings: list[dict[str, Any]], suppressions: list[dict[str, str]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not suppressions:
        return findings, []

    suppression_lookup = {(item["rule"], item["path"]): item for item in suppressions}
    active: list[dict[str, Any]] = []
    suppressed: list[dict[str, Any]] = []
    for finding in findings:
        suppression = suppression_lookup.get((finding["rule"], finding["path"]))
        if suppression is None:
            active.append(finding)
            continue
        suppressed_finding = dict(finding)
        suppressed_finding["suppression"] = dict(suppression)
        suppressed.append(suppressed_finding)
    return active, suppressed


def audit(
    root: Path | str,
    output_format: str = "json",
    config_path: str | None = None,
) -> dict[str, Any]:
    root_path = Path(root).resolve()
    config = load_config(root_path, config_path)
    suppressions = load_ignore_suppressions(root_path)
    scan_result = scan(root_path, output_format=output_format, config=config)
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
        findings.extend(rule_source_of_truth_drift(file_texts, config))
    findings.sort(key=lambda item: (item["path"], item["line_start"], item["rule"]))
    for index, finding in enumerate(findings, start=1):
        finding["id"] = f"LUCID-{index:04d}"
        finding["score_impact"] = finding_score_impact(finding)
    active_findings, suppressed_findings = apply_suppressions(findings, suppressions)

    return {
        "version": VERSION,
        "root": str(root_path),
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "files_scanned": scan_result["files_scanned"],
        "findings": active_findings,
        "suppressed_findings": suppressed_findings,
        "summary": summarize_findings(active_findings, suppressed_findings),
    }


def finding_score_impact(finding: dict[str, Any]) -> int:
    score = SEVERITY_SCORE_IMPACT.get(str(finding["severity"]), 0)
    if finding["requires_manual_review"]:
        score += MANUAL_REVIEW_SCORE_IMPACT
    if finding["rule"] == "compatibility-risk":
        return min(score, COMPATIBILITY_RISK_SCORE_CAP)
    return score


def ensure_scoring_fields(audit_result: dict[str, Any]) -> dict[str, Any]:
    findings = audit_result.get("findings", [])
    suppressed_findings = audit_result.get("suppressed_findings", [])
    summary = audit_result.setdefault("summary", {})

    findings_have_scores = all(
        isinstance(finding, dict) and "score_impact" in finding for finding in findings
    )
    suppressed_have_scores = all(
        isinstance(finding, dict) and "score_impact" in finding
        for finding in suppressed_findings
    )
    summary_has_scores = "debt_score" in summary and "suppressed_debt_score" in summary
    if findings_have_scores and suppressed_have_scores and summary_has_scores:
        return audit_result

    for finding in findings:
        if isinstance(finding, dict) and "score_impact" not in finding:
            finding["score_impact"] = finding_score_impact(finding)
    for finding in suppressed_findings:
        if isinstance(finding, dict) and "score_impact" not in finding:
            finding["score_impact"] = finding_score_impact(finding)

    if "debt_score" not in summary:
        summary["debt_score"] = sum(
            int(finding.get("score_impact", 0))
            for finding in findings
            if isinstance(finding, dict)
        )
    if "suppressed_debt_score" not in summary:
        summary["suppressed_debt_score"] = sum(
            int(finding.get("score_impact", 0))
            for finding in suppressed_findings
            if isinstance(finding, dict)
        )
    return audit_result


def summarize_findings(
    findings: list[dict[str, Any]], suppressed_findings: list[dict[str, Any]] | None = None
) -> dict[str, int]:
    summary = {
        "total": len(findings),
        "high": 0,
        "medium": 0,
        "low": 0,
        "manual_review": 0,
        "compatibility_protected": 0,
        "suppressed": len(suppressed_findings or []),
        "debt_score": 0,
        "suppressed_debt_score": 0,
    }
    for finding in findings:
        severity = str(finding["severity"])
        if severity in summary:
            summary[severity] += 1
        if finding["requires_manual_review"]:
            summary["manual_review"] += 1
        if finding["rule"] == "compatibility-risk":
            summary["compatibility_protected"] += 1
        summary["debt_score"] += int(finding.get("score_impact", 0))
    for finding in suppressed_findings or []:
        summary["suppressed_debt_score"] += int(finding.get("score_impact", 0))
    return summary


def render_concise_summary(summary: dict[str, Any]) -> str:
    return (
        f"Summary: active={summary.get('total', 0)} "
        f"debt={summary.get('debt_score', 0)} "
        f"high={summary.get('high', 0)} "
        f"medium={summary.get('medium', 0)} "
        f"low={summary.get('low', 0)} "
        f"manual_review={summary.get('manual_review', 0)} "
        f"compatibility_protected={summary.get('compatibility_protected', 0)} "
        f"suppressed={summary.get('suppressed', 0)} "
        f"suppressed_debt={summary.get('suppressed_debt_score', 0)}"
    )


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
    result = ensure_scoring_fields(result)
    summary = result["summary"]
    lines = [
        "Lucid audit",
        f"Root: {result['root']}",
        f"Files scanned: {result['files_scanned']}",
        render_concise_summary(summary),
        f"Findings: {summary['total']}",
        f"Debt score: {summary['debt_score']}",
    ]
    if summary.get("suppressed", 0):
        lines.append(f"Suppressed: {summary['suppressed']}")
        lines.append(f"Suppressed debt score: {summary['suppressed_debt_score']}")
    lines.append("")
    for finding in result["findings"]:
        lines.append(
            f"- {finding['id']} {finding['rule']} {finding['severity']} "
            f"{finding['path']}:{finding['line_start']} -> {finding['suggested_action']}"
        )
        lines.append(f"  {finding['reason']}")
    return "\n".join(lines)


def render_plan_markdown(audit_result: dict[str, Any]) -> str:
    audit_result = ensure_scoring_fields(audit_result)
    summary = audit_result["summary"]
    lines = [
        "# Lucid Context Hygiene Plan",
        "",
        "## Summary",
        "",
        f"- Root: `{audit_result['root']}`",
        f"- Files scanned: {audit_result['files_scanned']}",
        f"- Findings: {summary['total']}",
        f"- Debt score: {summary['debt_score']}",
        f"- Suppressed debt score: {summary.get('suppressed_debt_score', 0)}",
        f"- High severity: {summary['high']}",
        f"- Manual review: {summary['manual_review']}",
        f"- Compatibility-protected: {summary['compatibility_protected']}",
        f"- Suppressed: {summary.get('suppressed', 0)}",
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
                f"- Score impact: {finding['score_impact']}",
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
                    f"  - Why it looks stale: {PLAN_COMPATIBILITY_NOTE['why_it_looks_stale']}",
                    f"  - Why it may still be required: {PLAN_COMPATIBILITY_NOTE['why_it_may_still_be_required']}",
                    f"  - Evidence needed before removal: {PLAN_COMPATIBILITY_NOTE['evidence_needed_before_removal']}",
                ]
            )
        lines.extend(
            [
                f"- Safety: {PLAN_SAFETY_NOTE}",
                "",
            ]
        )
    return "\n".join(lines)


def render_plan_json(audit_result: dict[str, Any]) -> str:
    audit_result = ensure_scoring_fields(audit_result)
    actions: list[dict[str, Any]] = []
    for finding in audit_result["findings"]:
        action = {
            "id": finding["id"],
            "rule": finding["rule"],
            "severity": finding["severity"],
            "path": finding["path"],
            "line_start": finding["line_start"],
            "line_end": finding["line_end"],
            "current_snippet": finding["snippet"],
            "reason": finding["reason"],
            "suggested_action": finding["suggested_action"],
            "confidence": finding["confidence"],
            "score_impact": finding["score_impact"],
            "requires_manual_review": finding["requires_manual_review"],
            "replacement_hint": finding.get("replacement_hint"),
            "source_of_truth": finding.get("source_of_truth"),
            "safety": PLAN_SAFETY_NOTE,
        }
        if finding["rule"] == "compatibility-risk":
            action["compatibility_note"] = dict(PLAN_COMPATIBILITY_NOTE)
        actions.append(action)

    plan = {
        "format": "lucid-plan-json",
        "version": audit_result["version"],
        "root": audit_result["root"],
        "generated_at": audit_result["generated_at"],
        "files_scanned": audit_result["files_scanned"],
        "summary": audit_result["summary"],
        "suppressed_findings": audit_result.get("suppressed_findings", []),
        "recommended_actions": actions,
    }
    return render_json(plan)


def sarif_level(severity: str) -> str:
    if severity == "high":
        return "error"
    if severity == "medium":
        return "warning"
    return "note"


def render_sarif(audit_result: dict[str, Any]) -> str:
    audit_result = ensure_scoring_fields(audit_result)
    findings = audit_result["findings"]
    rules = [
        {
            "id": rule_id,
            "name": rule_id,
            "shortDescription": {"text": rule_id},
        }
        for rule_id in sorted(KNOWN_RULE_IDS)
    ]
    results: list[dict[str, Any]] = []
    for finding in findings:
        results.append(
            {
                "ruleId": finding["rule"],
                "level": sarif_level(finding["severity"]),
                "message": {"text": finding["reason"]},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": finding["path"]},
                            "region": {
                                "startLine": finding["line_start"],
                                "endLine": finding["line_end"],
                            },
                        }
                    }
                ],
                "properties": {
                    "lucid_id": finding["id"],
                    "severity": finding["severity"],
                    "suggested_action": finding["suggested_action"],
                    "requires_manual_review": finding["requires_manual_review"],
                    "confidence": finding["confidence"],
                    "score_impact": finding["score_impact"],
                    "replacement_hint": finding.get("replacement_hint"),
                    "source_of_truth": finding.get("source_of_truth"),
                },
            }
        )

    sarif = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "Lucid",
                        "semanticVersion": VERSION,
                        "rules": rules,
                    }
                },
                "results": results,
                "properties": {
                    "summary": audit_result["summary"],
                },
            }
        ],
    }
    return render_json(sarif)


def is_patch_eligible(finding: dict[str, Any]) -> bool:
    return (
        finding["rule"] in PATCH_ELIGIBLE_RULES
        and finding["suggested_action"] == "remove"
        and not finding["requires_manual_review"]
        and finding["line_start"] >= 1
        and finding["line_start"] <= finding["line_end"]
    )


def safe_patch_target(root: Path, path: str) -> Path:
    normalized = normalize_repo_path(path, "finding path")
    target = (root.resolve() / normalized).resolve()
    if not target.is_relative_to(root.resolve()):
        raise SystemExit(f"refusing to suggest patch outside target root: {path}")
    if not target.is_file():
        raise SystemExit(f"cannot suggest patch for missing file: {path}")
    return target


def delete_ranges(lines: list[str], ranges: list[tuple[int, int]]) -> list[str]:
    deleted_indexes: set[int] = set()
    for start, end in ranges:
        deleted_indexes.update(range(start - 1, end))
    return [line for index, line in enumerate(lines) if index not in deleted_indexes]


def valid_line_ranges(ranges: list[tuple[int, int]], line_count: int) -> bool:
    return all(1 <= start <= end <= line_count for start, end in ranges)


def render_suggest_patch(root: Path, audit_result: dict[str, Any]) -> str:
    ranges_by_path: dict[str, list[tuple[int, int]]] = {}
    for finding in audit_result["findings"]:
        if not is_patch_eligible(finding):
            continue
        ranges_by_path.setdefault(finding["path"], []).append(
            (finding["line_start"], finding["line_end"])
        )

    patch_chunks: list[str] = []
    for path in sorted(ranges_by_path):
        target = safe_patch_target(root, path)
        text = read_text_safely(target)
        if text is None:
            continue
        original_lines = text.splitlines()
        ranges = ranges_by_path[path]
        if not valid_line_ranges(ranges, len(original_lines)):
            continue
        suggested_lines = delete_ranges(original_lines, ranges)
        if suggested_lines == original_lines:
            continue
        diff_lines = list(
            difflib.unified_diff(
                original_lines,
                suggested_lines,
                fromfile=f"a/{path}",
                tofile=f"b/{path}",
                lineterm="",
            )
        )
        if not diff_lines:
            continue
        patch_chunks.append(f"diff --git a/{path} b/{path}\n" + "\n".join(diff_lines))
    return ("\n".join(patch_chunks) + "\n") if patch_chunks else ""


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


def load_audit_for_plan(
    root: Path, audit_path: str | None, config_path: str | None = None
) -> dict[str, Any]:
    if audit_path is None:
        return audit(root, output_format="json", config_path=config_path)
    path = safe_read_lucid_input(root, audit_path)
    return json.loads(path.read_text(encoding="utf-8"))


def verify(
    root: Path | str,
    strict: bool = False,
    config_path: str | None = None,
) -> dict[str, Any]:
    root_path = Path(root).resolve()
    audit_result = audit(root_path, output_format="json", config_path=config_path)
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
    scan_parser.add_argument("--config")
    scan_parser.add_argument("--format", choices=["json", "terminal"], default="terminal")
    scan_parser.add_argument("--out")

    audit_parser = subcommands.add_parser("audit", help="Audit context hygiene findings")
    audit_parser.add_argument("--root", default=".")
    audit_parser.add_argument("--config")
    audit_parser.add_argument("--format", choices=["json", "terminal", "sarif"], default="terminal")
    audit_parser.add_argument("--out")

    plan_parser = subcommands.add_parser("plan", help="Render a cleanup plan")
    plan_parser.add_argument("--root", default=".")
    plan_parser.add_argument("--config")
    plan_parser.add_argument("--audit")
    plan_parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    plan_parser.add_argument("--out")

    suggest_parser = subcommands.add_parser("suggest", help="Render diff-only suggestions")
    suggest_parser.add_argument("--root", default=".")
    suggest_parser.add_argument("--config")
    suggest_parser.add_argument("--audit")
    suggest_parser.add_argument("--out")

    verify_parser = subcommands.add_parser("verify", help="Verify Lucid package constraints")
    verify_parser.add_argument("--root", default=".")
    verify_parser.add_argument("--config")
    verify_parser.add_argument("--strict", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve()

    if args.command == "scan":
        result = scan(root, output_format=args.format, config_path=args.config)
        content = render_json(result) if args.format == "json" else render_terminal_scan(result)
        if args.out:
            safe_write_lucid_output(root, args.out, content)
        print(content, end="" if content.endswith("\n") else "\n")
        return 0

    if args.command == "audit":
        result = audit(root, output_format=args.format, config_path=args.config)
        if args.format == "json":
            content = render_json(result)
        elif args.format == "sarif":
            content = render_sarif(result)
        else:
            content = render_terminal_audit(result)
        if args.out:
            safe_write_lucid_output(root, args.out, content)
        print(content, end="" if content.endswith("\n") else "\n")
        return 0

    if args.command == "plan":
        audit_result = load_audit_for_plan(root, args.audit, config_path=args.config)
        content = (
            render_plan_json(audit_result)
            if args.format == "json"
            else render_plan_markdown(audit_result)
        )
        default_out = ".lucid/plan.json" if args.format == "json" else ".lucid/plan.md"
        safe_write_lucid_output(root, args.out or default_out, content)
        print(content, end="" if content.endswith("\n") else "\n")
        return 0

    if args.command == "suggest":
        audit_result = load_audit_for_plan(root, args.audit, config_path=args.config)
        content = render_suggest_patch(root, audit_result)
        safe_write_lucid_output(root, args.out or ".lucid/suggested.patch", content)
        print(content, end="" if content.endswith("\n") else "\n")
        return 0

    if args.command == "verify":
        result = verify(root, strict=args.strict, config_path=args.config)
        print(render_json(result), end="")
        return 0 if result["ok"] else 1

    raise SystemExit(f"unknown command {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
