#!/usr/bin/env python3
"""Sync a week's timetable sidecar into Google Calendar.

Reads data/reports/YYYY-w##-calendar.yaml (the structured sidecar coach-planner writes
alongside the human-readable timetable) and upserts it as Google Calendar events, scoped
so re-running after an edit never duplicates (see scripts/lib/gcal.py docstring).

Usage:
    make sync-calendar                        # latest *-calendar.yaml in data/reports/
    make sync-calendar WEEK=2026-w31          # specific week
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import gcal  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = ROOT / "data" / "reports"

REQUIRED_EVENT_KEYS = {"date", "start", "end", "title"}


def _resolve_path(week: str | None) -> Path:
    if week:
        p = REPORTS_DIR / f"{week}-calendar.yaml"
        if not p.exists():
            sys.exit(f"[Status: Critical] 找不到 {p.relative_to(ROOT)}")
        return p
    candidates = sorted(REPORTS_DIR.glob("*-calendar.yaml"))
    if not candidates:
        sys.exit(f"[Status: Critical] {REPORTS_DIR.relative_to(ROOT)} 下没有任何 *-calendar.yaml")
    return candidates[-1]


def _load(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    for key in ("week", "timezone", "events"):
        if key not in data:
            sys.exit(f"[Status: Critical] {path.name} 缺少必需字段 `{key}`")
    for i, e in enumerate(data["events"]):
        missing = REQUIRED_EVENT_KEYS - e.keys()
        if missing:
            sys.exit(f"[Status: Critical] {path.name} 第 {i+1} 个 event 缺少字段: {missing}")
    return data


def main() -> None:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser()
    parser.add_argument("--week", help="e.g. 2026-w31 (default: latest calendar.yaml)")
    args = parser.parse_args()

    path = _resolve_path(args.week)
    data = _load(path)
    week_tag = data["week"]
    timezone = data["timezone"]
    events = data["events"]
    calendar_id = data.get("calendar_id") or os.environ.get("GOOGLE_CALENDAR_ID", "primary")

    print(f"[Status: OK] 读取 {path.relative_to(ROOT)} — {len(events)} 个事件,week={week_tag},tz={timezone}")
    deleted, inserted = gcal.sync_week(week_tag, events, timezone, calendar_id)
    print(f"[Status: OK] 已清除旧事件 {deleted} 个,写入新事件 {inserted} 个 → calendar_id={calendar_id}")


if __name__ == "__main__":
    main()
