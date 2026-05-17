#!/usr/bin/env python3
"""Reject network, env, subprocess, and destructive IO in Lucid scripts."""

from __future__ import annotations

import ast
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGETS = [
    ROOT / "skills" / "lucid" / "scripts" / "lucid.py",
    ROOT / "scripts" / "validate-skill.py",
    ROOT / "scripts" / "validate-evals.py",
]

FORBIDDEN_IMPORT_PREFIXES = (
    "urllib",
    "requests",
    "http",
    "socket",
    "subprocess",
)
FORBIDDEN_CALL_NAMES = {
    "eval",
    "exec",
    "compile",
}
FORBIDDEN_METHODS = {
    "remove",
    "unlink",
    "rmtree",
    "rmdir",
    "removedirs",
    "system",
    "popen",
    "getenv",
}


def fail(message: str) -> None:
    print(f"validate-no-dangerous-io: {message}", file=sys.stderr)
    raise SystemExit(1)


def dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = dotted_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return ""


def validate_file(path: Path) -> None:
    if not path.exists():
        fail(f"missing target {path.relative_to(ROOT)}")
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith(FORBIDDEN_IMPORT_PREFIXES):
                    fail(f"{path.relative_to(ROOT)} imports {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module.startswith(FORBIDDEN_IMPORT_PREFIXES):
                fail(f"{path.relative_to(ROOT)} imports from {module}")
        elif isinstance(node, ast.Attribute):
            if dotted_name(node) == "os.environ":
                fail(f"{path.relative_to(ROOT)} reads os.environ")
        elif isinstance(node, ast.Call):
            name = dotted_name(node.func)
            leaf = name.rsplit(".", 1)[-1]
            if name in FORBIDDEN_CALL_NAMES or leaf in FORBIDDEN_METHODS:
                fail(f"{path.relative_to(ROOT)} calls {name}")


def main() -> int:
    for target in TARGETS:
        validate_file(target)
    print("validate-no-dangerous-io: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

