#!/usr/bin/env python3
"""Sync COROS sleep + readiness + training + activities into data/fitness/ and
patch the corresponding data/daily/YYYY-MM-DD.md frontmatter.

Auth: reads COROS_EMAIL / COROS_PASSWORD / COROS_REGION from .env (project root).
Usage:
    make sync-coros                     # yesterday
    make sync-coros DATE=2026-04-21     # specific date
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import date, timedelta
from pathlib import Path

import yaml
from dotenv import load_dotenv

import coros_api

ROOT = Path(__file__).resolve().parents[1]
FITNESS_DIR = ROOT / "data" / "fitness"
DAILY_DIR = ROOT / "data" / "daily"


def _parse_args() -> date:
    p = argparse.ArgumentParser()
    p.add_argument("--date", help="YYYY-MM-DD (default: yesterday)")
    args = p.parse_args()
    return date.fromisoformat(args.date) if args.date else date.today() - timedelta(days=1)


def _r(x, n=1):
    return None if x is None else round(x, n)


def _sleep_block(s) -> dict | None:
    if not s or not s.total_duration_minutes:
        return None
    ph = s.phases
    return {
        "duration": _r(s.total_duration_minutes / 60, 2),
        "deep_min": ph.deep_minutes if ph else None,
        "light_min": ph.light_minutes if ph else None,
        "rem_min": ph.rem_minutes if ph else None,
        "awake_min": ph.awake_minutes if ph else None,
        "nap_min": ph.nap_minutes if ph else None,
        "avg_hr": s.avg_hr,
        "min_hr": s.min_hr,
        "max_hr": s.max_hr,
    }


def _readiness_block(d) -> dict | None:
    if not d:
        return None
    load_ratio = d.training_load_ratio
    return {
        "hrv": _r(d.avg_sleep_hrv, 0),
        "hrv_baseline": _r(d.baseline, 0),
        "rhr": d.rhr,
        "tired_rate": _r(d.tired_rate, 0),
        "ati": _r(d.ati, 0),
        "cti": _r(d.cti, 0),
        "load_ratio": _r(load_ratio, 2),
        "stamina_level": _r(d.stamina_level, 0),
        "performance": d.performance,
    }


def _training_block(d) -> dict | None:
    if not d:
        return None
    return {
        "today_load": d.training_load,
        "vo2max": d.vo2max,
        "lthr": d.lthr,
    }


def _activity_item(a) -> dict:
    out = {
        "type": a.sport_name,
        "name": a.name,
        "duration_min": _r(a.duration_seconds / 60, 1) if a.duration_seconds else None,
        "avg_hr": a.avg_hr,
        "calories": a.calories,
        "training_load": a.training_load,
    }
    if a.distance_meters and a.distance_meters > 0:
        out["distance_km"] = _r(a.distance_meters / 1000, 2)
    if a.elevation_gain and a.elevation_gain > 0:
        out["elevation_m"] = a.elevation_gain
    if a.avg_power and a.avg_power > 0:
        out["avg_power"] = a.avg_power
    return out


async def _fetch(target: date) -> dict:
    auth = await coros_api.try_auto_login()
    if auth is None:
        sys.exit(
            "[Status: Critical] COROS auth failed — check .env "
            "(COROS_EMAIL / COROS_PASSWORD / COROS_REGION)"
        )

    day = target.strftime("%Y%m%d")
    sleep_records, daily_records, acts_pair = await asyncio.gather(
        coros_api.fetch_sleep(auth, day, day),
        coros_api.fetch_daily_records(auth, day, day),
        coros_api.fetch_activities(auth, day, day),
    )
    activities, _total = acts_pair

    # The daily/sleep endpoints sometimes return neighboring days — match by date.
    sleep = next((s for s in sleep_records if s.date == day), None)
    daily = next((d for d in daily_records if d.date == day), None)

    out: dict = {"date": target.isoformat()}
    if block := _sleep_block(sleep):
        out["sleep"] = block
    if block := _readiness_block(daily):
        out["readiness"] = block
    if block := _training_block(daily):
        out["training"] = block
    out["activities"] = [_activity_item(a) for a in activities]
    return out


def main() -> None:
    load_dotenv(ROOT / ".env")
    target = _parse_args()
    data = asyncio.run(_fetch(target))

    FITNESS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = FITNESS_DIR / f"{target.isoformat()}.yaml"
    with out_path.open("w") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)

    blocks = [b for b in ("sleep", "readiness", "training") if b in data]
    n_acts = len(data.get("activities") or [])
    print(f"[Status: OK] wrote {out_path.relative_to(ROOT)} "
          f"(blocks={'+'.join(blocks) or 'none'}, activities={n_acts})")

    # Patch the matching daily log if present
    daily_md = DAILY_DIR / f"{target.isoformat()}.md"
    if daily_md.exists():
        from patch_coros import patch_daily
        changed = patch_daily(daily_md, data)
        print(f"[Status: OK] patched {daily_md.relative_to(ROOT)} "
              f"({len(changed)} field(s))" if changed
              else f"[Status: OK] {daily_md.relative_to(ROOT)} already up to date")
    else:
        print(f"[Status: Info] {daily_md.relative_to(ROOT)} not found, skip patch")


if __name__ == "__main__":
    main()
