#!/usr/bin/env python3
"""Repository-level CLI wrapper for the canonical Lucid skill script."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Sequence


LUCID_SCRIPT = Path(__file__).resolve().parent / "skills" / "lucid" / "scripts" / "lucid.py"


def load_lucid_module() -> ModuleType:
    if not LUCID_SCRIPT.exists():
        raise SystemExit("missing skills/lucid/scripts/lucid.py")
    spec = importlib.util.spec_from_file_location("lucid_skill_script", LUCID_SCRIPT)
    if spec is None or spec.loader is None:
        raise SystemExit("cannot load skills/lucid/scripts/lucid.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv: Sequence[str] | None = None) -> int:
    module = load_lucid_module()
    return module.main(list(argv) if argv is not None else None)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
