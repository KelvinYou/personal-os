#!/usr/bin/env python3
# flow: wealth
"""Print data/finance/history.csv as JSON — read-only, for the web dashboard's chart.

Writing is finance_edit.py's job (every mutation upserts today's row via
lib/wealth/history.py); this script only exists so the Next.js route doesn't
need its own CSV parser.

Usage:
    python3 scripts/finance_history.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.wealth import read_history  # noqa: E402


def main() -> int:
    print(json.dumps(read_history(), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
