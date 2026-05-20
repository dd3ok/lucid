#!/usr/bin/env python3
from __future__ import annotations

import argparse
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SKILL_DIR = ROOT / "skills" / "lucid"
DEFAULT_OUTPUT = ROOT / "dist" / "lucid-skill.zip"

EXCLUDED_NAMES = {
    ".DS_Store",
}
EXCLUDED_PARTS = {
    "__pycache__",
}
EXCLUDED_SUFFIXES = {
    ".pyc",
    ".pyo",
}


def fail(message: str) -> None:
    raise SystemExit(f"package-skill: {message}")


def safe_repo_path(path: Path) -> Path:
    resolved = path.resolve()
    root = ROOT.resolve()
    if not resolved.is_relative_to(root):
        fail(f"refusing path outside repository: {path}")
    return resolved


def validate_skill_dir(skill_dir: Path) -> Path:
    resolved = safe_repo_path(skill_dir)
    if not resolved.is_dir():
        fail(f"skill directory not found: {skill_dir}")
    if not (resolved / "SKILL.md").is_file():
        fail("skill package must contain SKILL.md at the skill root")
    return resolved


def validate_output_path(output: Path) -> Path:
    resolved = safe_repo_path(output)
    allowed = (ROOT / "dist").resolve()
    if not resolved.is_relative_to(allowed):
        fail("refusing to write package outside dist/")
    if resolved.is_dir():
        fail(f"output path is a directory: {output}")
    return resolved


def should_include(path: Path) -> bool:
    if path.name in EXCLUDED_NAMES:
        return False
    if path.suffix in EXCLUDED_SUFFIXES:
        return False
    if set(path.parts) & EXCLUDED_PARTS:
        return False
    return True


def iter_package_files(skill_dir: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(skill_dir.rglob("*")):
        if path.is_file() and should_include(path):
            files.append(path)
    return files


def assert_safe_archive_name(name: str) -> None:
    if name.startswith("/") or name.startswith("../") or "/../" in name:
        fail(f"unsafe archive path: {name}")


def package_skill(skill_dir: Path, output: Path) -> None:
    skill_dir = validate_skill_dir(skill_dir)
    output = validate_output_path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    files = iter_package_files(skill_dir)
    if not files:
        fail("no files selected for packaging")

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive_name = path.relative_to(skill_dir).as_posix()
            assert_safe_archive_name(archive_name)
            archive.write(path, archive_name)

    print(f"wrote {output.relative_to(ROOT)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Package the Lucid skill folder")
    parser.add_argument(
        "--skill-dir",
        default=str(DEFAULT_SKILL_DIR),
        help="Skill directory to package; defaults to skills/lucid",
    )
    parser.add_argument(
        "--out",
        default=str(DEFAULT_OUTPUT),
        help="Output zip path under dist/; defaults to dist/lucid-skill.zip",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    package_skill(Path(args.skill_dir), Path(args.out))


if __name__ == "__main__":
    main()
