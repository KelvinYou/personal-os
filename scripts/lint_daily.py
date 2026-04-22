#!/usr/bin/env python3
"""Lint data/daily/*.md frontmatter against the pydantic schema.

Exit code 0 = all pass; 1 = at least one file failed validation.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from lib.daily_log import DAILY_DIR, load_safe  # noqa: E402


def main() -> int:
    failures: list[str] = []
    for fp in sorted(DAILY_DIR.glob("*.md")):
        _, err = load_safe(fp)
        if err:
            failures.append(err)

    if failures:
        for line in failures:
            print(f"[ERROR] {line}")
        print(f"\n{len(failures)} file(s) failed schema validation.")
        return 1
    print(f"[Status: OK] All {len(list(DAILY_DIR.glob('*.md')))} daily logs pass schema validation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
