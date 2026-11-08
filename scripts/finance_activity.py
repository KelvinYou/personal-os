#!/usr/bin/env python3
# flow: wealth
"""Read monthly asset changes or append a confirmed private transaction.

Read: .venv/bin/python scripts/finance_activity.py
Append one JSON event from stdin: ... finance_activity.py add < event.json
Writes evidence only; never changes holdings, cash balances or history snapshots.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.config import load_thresholds
from lib.wealth import build_report, load_savings, load_rates, load_portfolio, load_fx
from lib.clock import today_kl
from lib.wealth.activity import Transaction, append_transaction, build_activity
from lib.wealth.history import read_history


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", choices=["read", "add"], default="read")
    args = parser.parse_args()
    try:
        if args.command == "add":
            raw = json.load(sys.stdin)
            raw.setdefault("recorded_on", today_kl().isoformat())
            event = Transaction.model_validate(raw)
            if event.recorded_on > today_kl():
                raise ValueError("Recorded date cannot be in the future")
            inserted = append_transaction(event)
            print(json.dumps({"ok": True, "inserted": inserted}))
        else:
            today = today_kl()
            wealth = build_report(load_savings(), load_rates(), load_portfolio(), load_fx(), load_thresholds().wealth, today)
            print(build_activity(read_history(), today, wealth=wealth).model_dump_json())
        return 0
    except (ValueError, OSError) as exc:
        # Avoid printing private payloads in generic subprocess errors.
        print(json.dumps({"ok": False, "error": "Invalid or unavailable finance activity; check the local journal and event schema."}))
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
