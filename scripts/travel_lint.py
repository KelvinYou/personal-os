#!/usr/bin/env python3
"""Lint data/travel/*.md for internally-checkable defects.

Exit code 0 = no ERROR findings; 1 = at least one. WARN never fails the run.
Usage: travel_lint.py [path ...]   (default: every .md under data/travel/)
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from lib.travel import lint_text  # noqa: E402

TRAVEL_DIR = PROJECT_ROOT / "data" / "travel"


def main(argv: list[str]) -> int:
    if argv:
        paths = [Path(a) for a in argv]
    elif TRAVEL_DIR.is_dir():
        paths = sorted(TRAVEL_DIR.glob("*.md"))
    else:
        print("[Status: Warning] data/travel/ not checked out — nothing to lint.")
        return 0

    if not paths:
        print("[Status: OK] No travel plans to lint.")
        return 0

    errors = warns = 0
    for path in paths:
        findings = lint_text(path.read_text(encoding="utf-8"))
        if not findings:
            print(f"[Status: OK] {path.name}: clean")
            continue
        print(f"\n{path.name}")
        for f in findings:
            print(f"  {f.format()}")
        errors += sum(1 for f in findings if f.severity == "ERROR")
        warns += sum(1 for f in findings if f.severity == "WARN")

    if errors:
        print(f"\n[Status: Critical] {errors} error(s), {warns} warning(s) "
              f"across {len(paths)} plan(s).")
        return 1
    if warns:
        print(f"\n[Status: Warning] {warns} warning(s) across {len(paths)} plan(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
