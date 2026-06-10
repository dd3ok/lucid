#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import contextlib
import io
import sys
import zipfile
from types import ModuleType
from pathlib import Path
from collections.abc import Callable


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


def validate_openai_hosted_fixed_root(package_module: ModuleType) -> None:
    staged_skill = ROOT / ".lucid" / "package-validation" / "staged-lucid"
    staged_skill.mkdir(parents=True, exist_ok=True)
    for entry in REQUIRED_ENTRIES:
        target = staged_skill / entry
        target.parent.mkdir(parents=True, exist_ok=True)
        if entry == "SKILL.md":
            target.write_text("---\nname: lucid\n---\n", encoding="utf-8")
        else:
            target.write_text(f"{entry}\n", encoding="utf-8")
    output = ROOT / "dist" / "openai" / "staged-lucid.zip"
    package_module.package_skill(staged_skill, output, target="openai-hosted")
    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
        for name in names:
            validate_member(name, package_root="lucid")
    validate_openai_hosted_archive(names)
    expected_names = {f"lucid/{entry}" for entry in REQUIRED_ENTRIES}
    if names != expected_names:
        fail("openai-hosted staged archive included unexpected entries")
    if "lucid/SKILL.md" not in names:
        fail("openai-hosted target did not use fixed lucid/ top-level folder")
    if "staged-lucid/SKILL.md" in names:
        fail("openai-hosted target used source directory name as top-level folder")


def validate_package_cli(
    package_module: ModuleType,
    args: list[str],
    output: Path,
    *,
    package_root: str | None,
    archive_validator: Callable[[set[str]], None],
) -> None:
    original_argv = sys.argv[:]
    sys.argv = [str(PACKAGE_SCRIPT), *args]
    stdout = io.StringIO()
    previous_mtime_ns = output.stat().st_mtime_ns if output.exists() else None
    try:
        with contextlib.redirect_stdout(stdout):
            package_module.main()
    except Exception as exc:
        fail(
            "package-skill CLI openai-hosted target failed: "
            + f"{type(exc).__name__}: {exc}"
        )
    finally:
        sys.argv = original_argv
    expected_output = str(output.relative_to(ROOT))
    if expected_output not in stdout.getvalue():
        fail(f"package-skill CLI did not report output path {expected_output}")
    if not output.exists():
        fail(f"package-skill CLI did not create {output.relative_to(ROOT)}")
    if (
        previous_mtime_ns is not None
        and output.stat().st_mtime_ns <= previous_mtime_ns
    ):
        fail(f"package-skill CLI did not refresh {output.relative_to(ROOT)}")
    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
        for name in names:
            validate_member(name, package_root=package_root)
        archive_validator(names)


def validate_archive_byte_parity() -> None:
    with zipfile.ZipFile(DIST_ZIP) as raw_archive, zipfile.ZipFile(
        OPENAI_HOSTED_ZIP
    ) as hosted_archive:
        for entry in REQUIRED_ENTRIES:
            source_bytes = (ROOT / "skills" / "lucid" / entry).read_bytes()
            raw_bytes = raw_archive.read(entry)
            hosted_bytes = hosted_archive.read(f"lucid/{entry}")
            if raw_bytes != source_bytes:
                fail(f"raw-local archive changed bytes for {entry}")
            if hosted_bytes != source_bytes:
                fail(f"openai-hosted archive changed bytes for {entry}")


def main() -> None:
    if not PACKAGE_SCRIPT.exists():
        fail("scripts/package-skill.py missing")

    package_module = load_package_module()
    validate_package_filters(package_module)
    validate_openai_hosted_fixed_root(package_module)
    validate_package_cli(
        package_module,
        [],
        DIST_ZIP,
        package_root=None,
        archive_validator=validate_raw_local_archive,
    )
    validate_package_cli(
        package_module,
        ["--target", "openai-hosted", "--out", str(OPENAI_HOSTED_ZIP)],
        OPENAI_HOSTED_ZIP,
        package_root="lucid",
        archive_validator=validate_openai_hosted_archive,
    )
    validate_archive_byte_parity()
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
    print("validate-package-skill: ok")


if __name__ == "__main__":
    main()
