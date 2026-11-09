#!/usr/bin/env python3
# flow: office
"""Agent wait on human for one week, from local Codex / Claude Code records, plus Content Lab review latency. Read-only."""
from __future__ import annotations

import argparse
from datetime import date
import json
import sys

from lib.clock import today_kl, user_timezone
from lib.config import ROOT, load_thresholds
from lib.daily_log import week_bounds
from lib.office.sources import claude_projects, codex_sessions
from lib.office.waits import content_review_markdown, content_review_week, markdown, week_waits


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", help="Any day in the target week (YYYY-MM-DD); defaults to today")
    parser.add_argument("--json", action="store_true", help="Machine-readable summary")
    args = parser.parse_args()
    cfg = load_thresholds().office
    if cfg is None:
        print("[Status: Warning] office is not configured in private thresholds; nothing to measure.")
        return 1
    monday = week_bounds(date.fromisoformat(args.date) if args.date else today_kl())
    try:
        week = week_waits(codex_sessions(), ROOT, claude_projects() if cfg.claude_enabled else None, cfg, monday, user_timezone())
    except FileNotFoundError:
        print("[Status: Critical] Neither Codex nor Claude Code records are readable for this workspace.")
        return 1
    content = content_review_week(ROOT / "data" / "posts", monday, user_timezone())
    if args.json: print(json.dumps({"monday": monday.isoformat(), **week.summary(), "content_review": content}))
    else: print("\n".join(markdown(week, cfg) + content_review_markdown(content)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
