#!/usr/bin/env python3
"""Create a new decision file from template."""
from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = PROJECT_ROOT / "templates" / "decision.md"
DECISIONS_DIR = PROJECT_ROOT / "data" / "decisions"

DEFAULT_REVIEW_DAYS = 30


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a new decision journal entry")
    parser.add_argument("--slug", required=True, help="Short slug for the decision (e.g. cancel-gym)")
    parser.add_argument("--date", default=None, help="Decision date (YYYY-MM-DD, default today)")
    args = parser.parse_args()

    decided = date.fromisoformat(args.date) if args.date else date.today()
    decision_id = f"{decided.isoformat()}-{args.slug}"
    filename = f"{decision_id}.md"
    out_path = DECISIONS_DIR / filename

    if out_path.exists():
        print(f"[Error] {out_path} already exists.", file=sys.stderr)
        sys.exit(1)

    DECISIONS_DIR.mkdir(parents=True, exist_ok=True)

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    review_date = decided + timedelta(days=DEFAULT_REVIEW_DAYS)

    content = template.replace("{{TITLE}}", args.slug.replace("-", " "))
    content = content.replace("{{CONTEXT}}", "")

    # Fill in known fields
    replacements = {
        "id:": f"id: {decision_id}",
        "date_decided:": f"date_decided: {decided.isoformat()}",
        "review_date:": f"review_date: {review_date.isoformat()}",
        "status:": "status: open",
    }
    for old, new in replacements.items():
        # Only replace the first occurrence of bare key (the field definition line)
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if line.startswith(old) and "#" in line:
                lines[i] = new
                break
        content = "\n".join(lines)

    out_path.write_text(content, encoding="utf-8")
    print(f"[OK] Created {out_path.relative_to(PROJECT_ROOT)}")
    print(f"     Review date: {review_date.isoformat()}")


if __name__ == "__main__":
    main()
