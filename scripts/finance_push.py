#!/usr/bin/env python3
# flow: office
"""Phone push when a new Warning/Critical item enters the Finance attention list.

Runs detached at Claude Code SessionStart (scripts/office_signal.py) or by hand
(`make finance-push`). The item list is report.attention from
scripts/lib/wealth/attention.py, the same list /finance renders. Each id is pushed
once: the private state file data/runtime/finance-push.json remembers the ids that
were open at the last run, so a resolved item that comes back alerts again.
The pushed text is fixed; no amount, account name or id leaves the machine.

  --dry-run   print what would be pushed; send nothing and keep the state
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

STATE = ROOT / "data" / "runtime" / "finance-push.json"
ALERT = {"Warning", "Critical"}


def open_ids(report: dict) -> list[str]:
    return sorted(item["id"] for item in report["attention"] if item["severity"] in ALERT)


def new_ids(current: list[str], state: Path) -> list[str]:
    try:
        seen = set(json.loads(state.read_text(encoding="utf-8"))["open_ids"])
    except (OSError, ValueError, KeyError, TypeError):
        seen = set()
    return [i for i in current if i not in seen]


def save(current: list[str], state: Path) -> None:
    state.parent.mkdir(parents=True, exist_ok=True)
    tmp = state.with_suffix(".tmp")
    tmp.write_text(json.dumps({"open_ids": current}, indent=2) + "\n", encoding="utf-8")
    tmp.replace(state)


def build() -> dict:
    from lib.config import load_thresholds
    from lib.clock import today_kl
    from lib.wealth import build_report, load_fx, load_portfolio, load_rates, load_savings
    from lib.wealth.files import load_travel_cash
    return build_report(load_savings(), load_rates(), load_portfolio(), load_fx(),
                        load_thresholds().wealth, today_kl(), travel_cash=load_travel_cash())


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    from lib.config import load_thresholds
    office = load_thresholds().office
    cfg = office.push if office and office.push else None
    current = open_ids(build())
    fresh = new_ids(current, STATE)
    if args.dry_run:
        print(f"[Status: OK] {len(current)} open alert items, {len(fresh)} new: {', '.join(fresh) or '-'}")
        print(f"  push {'would be sent' if fresh and cfg and cfg.enabled and cfg.finance_attention else 'off or nothing new'}")
        return 0
    if fresh and cfg and cfg.enabled and cfg.finance_attention:
        from lib.office.push import deliver
        deliver(cfg, "finance_attention")  # raises on network failure: state stays, so the next run retries
    save(current, STATE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
