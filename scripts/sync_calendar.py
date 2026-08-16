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
from datetime import date
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


PROTOCOL_PATH = ROOT / "data" / "protocol" / "standard_week.yaml"
REQUIRED_ANCHOR_KEYS = {"days", "start", "end", "title"}
VALID_DAYS = {"MO", "TU", "WE", "TH", "FR", "SA", "SU"}


def _load_protocol(path: Path) -> dict:
    if not path.exists():
        sys.exit(f"[Status: Critical] 找不到 {path.relative_to(ROOT)}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    for key in ("timezone", "start_date", "anchors"):
        if key not in data:
            sys.exit(f"[Status: Critical] {path.name} 缺少必需字段 `{key}`")
    seen: set[str] = set()
    for i, a in enumerate(data["anchors"]):
        missing = REQUIRED_ANCHOR_KEYS - a.keys()
        if missing:
            sys.exit(f"[Status: Critical] {path.name} 第 {i+1} 个 anchor 缺少字段: {missing}")
        bad = set(a["days"]) - VALID_DAYS
        if bad:
            sys.exit(f"[Status: Critical] {path.name} anchor `{a['title']}` 的 days 非法: {bad}")
        # keys are the idempotency handle; a silent duplicate would make one
        # anchor untraceable after insert.
        k = a.get("key", a["title"])
        if k in seen:
            sys.exit(f"[Status: Critical] {path.name} anchor key 重复: `{k}`")
        seen.add(k)
    return data


def _sync_protocol(dry_run: bool) -> None:
    data = _load_protocol(PROTOCOL_PATH)
    anchors = data["anchors"]
    timezone = data["timezone"]
    start_date = data["start_date"]
    if isinstance(start_date, str):
        start_date = date.fromisoformat(start_date)

    print(f"[Status: OK] 读取 {PROTOCOL_PATH.relative_to(ROOT)} — "
          f"{len(anchors)} 个常驻锚点, tz={timezone}, 起算 {start_date}")

    if dry_run:
        for a in anchors:
            first = gcal.first_occurrence(a["days"], start_date)
            every = "" if a.get("interval", 1) == 1 else f" (每 {a['interval']} 周)"
            print(f"  {','.join(a['days']):<20} {a['start']}-{a['end']}  {a['title']}"
                  f"  → 首次 {first}{every}")
        print("\n[Status: OK] Dry-run 完成，未写入 Calendar。去掉 DRY=1 真推。")
        return

    calendar_name = data.get("calendar_name")
    if calendar_name:
        calendar_id = gcal.resolve_calendar(calendar_name)
        print(f"[Status: OK] 目标日历 「{calendar_name}」 → {calendar_id}")
    else:
        calendar_id = os.environ.get("GOOGLE_CALENDAR_ID", "primary")

    deleted, inserted = gcal.sync_protocol(anchors, timezone, start_date, calendar_id)
    print(f"[Status: OK] 已清除旧的常驻事件 {deleted} 个，写入 {inserted} 个周期性事件")
    print("[Note] 全部无提醒 (reminders off)、标记为 Free — 参考用，不占用忙碌状态、不阻挡他人约会。")


def main() -> None:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser()
    parser.add_argument("--week", help="e.g. 2026-w31 (default: latest calendar.yaml)")
    parser.add_argument("--protocol", action="store_true",
                        help="推送 data/protocol/standard_week.yaml 的周期性锚点")
    parser.add_argument("--dry-run", action="store_true", help="只打印，不写 Calendar")
    args = parser.parse_args()

    if args.protocol:
        _sync_protocol(args.dry_run)
        return

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
