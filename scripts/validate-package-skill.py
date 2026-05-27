#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import zipfile
from types import ModuleType
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_SCRIPT = ROOT / "scripts" / "package-skill.py"
DIST_ZIP = ROOT / "dist" / "lucid-skill.zip"
OPENAI_HOSTED_ZIP = ROOT / "dist" / "openai" / "lucid.zip"

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


def validate_member(name: str, package_root: str | None = None) -> None:
    if name.startswith("/") or name.startswith("../") or "/../" in name:
        fail(f"archive contains unsafe path: {name}")
    relative_name = name
    if package_root is not None:
        root = package_root.rstrip("/")
        prefix = f"{root}/"
        normalized_name = name.rstrip("/")
        if normalized_name == root:
            return
        if not name.startswith(prefix):
            fail(f"archive contains path outside package root: {name}")
        relative_name = name[len(prefix) :]
    if any(relative_name.startswith(prefix) for prefix in FORBIDDEN_PREFIXES):
        fail(f"archive contains forbidden path: {name}")
    parts = set(Path(relative_name).parts)
    if parts & FORBIDDEN_PARTS:
        fail(f"archive contains forbidden cache path: {name}")
    if relative_name.endswith("/"):
        return
    if relative_name.endswith((".pyc", ".pyo")):
        fail(f"archive contains compiled Python artifact: {name}")
    if relative_name.endswith(".DS_Store"):
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


def validate_package_filters(package_module: ModuleType) -> None:
    validation_root = ROOT / ".lucid" / "package-validation"
    parent_cache_skill = validation_root / "__pycache__" / "skill"
    parent_cache_skill.mkdir(parents=True, exist_ok=True)
    (parent_cache_skill / "SKILL.md").write_text("---\nname: test\n---\n", encoding="utf-8")
    outside_file = validation_root / "outside.txt"
    outside_file.write_text("outside\n", encoding="utf-8")

    selected = {
        path.relative_to(parent_cache_skill).as_posix()
        for path in package_module.iter_package_files(parent_cache_skill)
    }
    if "SKILL.md" not in selected:
        fail("iter_package_files excluded file because of absolute parent path")

    if package_module.should_include(Path("__pycache__") / "x.py"):
        fail("should_include accepted __pycache__ relative path")
    if not package_module.should_include(Path("references") / "security.md"):
        fail("should_include rejected normal reference path")

    link_path = parent_cache_skill / "outside-link.txt"
    if not link_path.exists():
        try:
            link_path.symlink_to(outside_file)
        except OSError:
            return
    if link_path.is_symlink():
        selected = {
            path.relative_to(parent_cache_skill).as_posix()
            for path in package_module.iter_package_files(parent_cache_skill)
        }
        if "outside-link.txt" in selected:
            fail("iter_package_files accepted symlinked file")


def validate_raw_local_archive(names: set[str]) -> None:
    missing = sorted(REQUIRED_ENTRIES - names)
    if missing:
        fail(f"raw-local archive missing required entries: {', '.join(missing)}")
    if "lucid/SKILL.md" in names:
        fail("raw-local archive unexpectedly contains lucid/SKILL.md")


def validate_openai_hosted_archive(names: set[str]) -> None:
    top_level = {Path(name).parts[0] for name in names if Path(name).parts}
    if top_level != {"lucid"}:
        fail(
            "openai-hosted archive must contain exactly one top-level folder: "
            + ", ".join(sorted(top_level))
        )
    required = {f"lucid/{entry}" for entry in REQUIRED_ENTRIES}
    missing = sorted(required - names)
    if missing:
        fail(f"openai-hosted archive missing required entries: {', '.join(missing)}")
    if "SKILL.md" in names:
        fail("openai-hosted archive must not place SKILL.md at archive root")


def main() -> None:
    if not PACKAGE_SCRIPT.exists():
        fail("scripts/package-skill.py missing")

    package_module = load_package_module()
    validate_package_filters(package_module)
    expect_failure(
        "forbidden path under openai-hosted package root",
        lambda: validate_member("lucid/docs/extra.md", package_root="lucid"),
    )
    expect_failure(
        "forbidden directory under openai-hosted package root",
        lambda: validate_member("lucid/docs/", package_root="lucid"),
    )
    expect_failure(
        "path outside openai-hosted package root",
        lambda: validate_member("outside/file.md", package_root="lucid"),
    )
    expect_failure(
        "directory outside openai-hosted package root",
        lambda: validate_member("outside/", package_root="lucid"),
    )
    if package_module.default_output_for("raw-local") != DIST_ZIP:
        fail("raw-local default output path changed unexpectedly")
    if package_module.default_output_for("openai-hosted") != OPENAI_HOSTED_ZIP:
        fail("openai-hosted default output path changed unexpectedly")
    expect_failure(
        "unknown package target",
        lambda: package_module.package_skill(
            package_module.DEFAULT_SKILL_DIR,
            DIST_ZIP,
            target="unknown",
        ),
    )
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
    package_module.package_skill(
        package_module.DEFAULT_SKILL_DIR,
        OPENAI_HOSTED_ZIP,
        target="openai-hosted",
    )

    if not DIST_ZIP.exists():
        fail("dist/lucid-skill.zip was not created")
    if not OPENAI_HOSTED_ZIP.exists():
        fail("dist/openai/lucid.zip was not created")

    with zipfile.ZipFile(DIST_ZIP) as archive:
        names = set(archive.namelist())
        for name in names:
            validate_member(name)
        validate_raw_local_archive(names)

    with zipfile.ZipFile(OPENAI_HOSTED_ZIP) as archive:
        names = set(archive.namelist())
        for name in names:
            validate_member(name, package_root="lucid")
        validate_openai_hosted_archive(names)

    print("validate-package-skill: ok")


if __name__ == "__main__":
    main()
