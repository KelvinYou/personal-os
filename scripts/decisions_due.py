#!/usr/bin/env python3
"""List decisions with review_date <= today and status in {open, pushed}."""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DECISIONS_DIR = PROJECT_ROOT / "data" / "decisions"


def _parse_frontmatter(path: Path) -> dict | None:
    parts = path.read_text(encoding="utf-8").split("---", 2)
    if len(parts) < 3:
        return None
    return yaml.safe_load(parts[1]) or {}


def iter_due(today: date | None = None) -> list[tuple[Path, dict]]:
    today = today or date.today()
    due: list[tuple[Path, dict]] = []
    if not DECISIONS_DIR.is_dir():
        return due
    for p in sorted(DECISIONS_DIR.glob("*.md")):
        if p.name.startswith("."):
            continue
        meta = _parse_frontmatter(p)
        if meta is None:
            print(f"[Warning] {p.name}: no frontmatter, skipped", file=sys.stderr)
            continue
        status = meta.get("status")
        if status not in ("open", "pushed"):
            continue
        raw_review = meta.get("review_date")
        if raw_review is None:
            continue
        if isinstance(raw_review, str):
            review_date = date.fromisoformat(raw_review)
        elif isinstance(raw_review, date):
            review_date = raw_review
        else:
            continue
        if review_date <= today:
            due.append((p, meta))
    return due


def main() -> None:
    due = iter_due()
    if not due:
        print("[OK] No decisions due for review.")
        return
    print(f"[Decision Review] {len(due)} decision(s) due for review:\n")
    for path, meta in due:
        title = meta.get("id", path.stem)
        category = meta.get("category", "?")
        stakes = meta.get("stakes", "?")
        expected = meta.get("expected_outcome", "")
        review_date = meta.get("review_date", "?")
        status = meta.get("status", "open")
        print(f"  - [{status}] {title}  ({category}/{stakes})")
        print(f"    review_date: {review_date}")
        if expected:
            print(f"    expected: {expected}")
        print()


if __name__ == "__main__":
    main()
