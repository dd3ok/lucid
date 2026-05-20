#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import zipfile
from types import ModuleType
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_SCRIPT = ROOT / "scripts" / "package-skill.py"
DIST_ZIP = ROOT / "dist" / "lucid-skill.zip"

REQUIRED_ENTRIES = {
    "SKILL.md",
    "scripts/lucid.py",
    "agents/openai.yaml",
    "assets/default-rules.json",
    "references/cleanup-actions.md",
    "references/compatibility-safety.md",
    "references/context-surfaces.md",
    "references/memory-retention-rubric.md",
    "references/negative-residue.md",
    "references/rule-taxonomy.md",
    "references/security.md",
    "references/source-of-truth.md",
}

FORBIDDEN_PREFIXES = (
    ".github/",
    ".lucid/",
    "dist/",
    "docs/",
    "evals/",
    "fixtures/",
)

FORBIDDEN_PARTS = {
    "__pycache__",
}


def fail(message: str) -> None:
    raise SystemExit(f"validate-package-skill: {message}")


def validate_member(name: str) -> None:
    if name.startswith("/") or name.startswith("../") or "/../" in name:
        fail(f"archive contains unsafe path: {name}")
    if name.endswith("/"):
        return
    if any(name.startswith(prefix) for prefix in FORBIDDEN_PREFIXES):
        fail(f"archive contains forbidden path: {name}")
    parts = set(Path(name).parts)
    if parts & FORBIDDEN_PARTS:
        fail(f"archive contains forbidden cache path: {name}")
    if name.endswith((".pyc", ".pyo")):
        fail(f"archive contains compiled Python artifact: {name}")
    if name.endswith(".DS_Store"):
        fail(f"archive contains platform metadata: {name}")


def load_package_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("package_skill", PACKAGE_SCRIPT)
    if spec is None or spec.loader is None:
        fail("could not load scripts/package-skill.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_failure(description: str, func: object) -> None:
    try:
        func()
    except SystemExit:
        return
    fail(f"expected failure for {description}")


def main() -> None:
    if not PACKAGE_SCRIPT.exists():
        fail("scripts/package-skill.py missing")

    package_module = load_package_module()
    expect_failure(
        "output outside dist/",
        lambda: package_module.package_skill(
            package_module.DEFAULT_SKILL_DIR,
            ROOT / ".lucid" / "lucid-skill.zip",
        ),
    )
    expect_failure(
        "skill directory outside repository",
        lambda: package_module.package_skill(
            ROOT.parent,
            DIST_ZIP,
        ),
    )
    package_module.package_skill(package_module.DEFAULT_SKILL_DIR, DIST_ZIP)

    if not DIST_ZIP.exists():
        fail("dist/lucid-skill.zip was not created")

    with zipfile.ZipFile(DIST_ZIP) as archive:
        names = set(archive.namelist())
        for name in names:
            validate_member(name)
        missing = sorted(REQUIRED_ENTRIES - names)
        if missing:
            fail(f"archive missing required entries: {', '.join(missing)}")

    print("validate-package-skill: ok")


if __name__ == "__main__":
    main()
