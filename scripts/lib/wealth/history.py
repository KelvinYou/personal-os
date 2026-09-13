"""Daily snapshot history for Tracked Assets — data/finance/history.csv.

Every finance_edit.py mutation (add/edit/delete) upserts *today's* row rather
than appending a new one — intra-day edits are "today's data changed", not
several data points. This file is a derived cache of build_report() output,
never a second source of truth: delete it and it rebuilds from tomorrow's
first edit (past days are lost, which is fine — it's a chart aid, not
ledger-of-record; the YAML files under data/finance/ remain authoritative).
"""
from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from .files import FINANCE_DIR

HISTORY_PATH = FINANCE_DIR / "history.csv"
FIELDS = ["date", "tracked_total_myr", "cash_total_myr", "stocks_total_myr"]


def _read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def record_snapshot(
    today: date,
    tracked_total_myr: float,
    cash_total_myr: float,
    stocks_total_myr: float,
    path: Path | None = None,
) -> None:
    path = path or HISTORY_PATH
    rows = [r for r in _read_rows(path) if r["date"] != today.isoformat()]
    rows.append(
        {
            "date": today.isoformat(),
            "tracked_total_myr": f"{tracked_total_myr:.2f}",
            "cash_total_myr": f"{cash_total_myr:.2f}",
            "stocks_total_myr": f"{stocks_total_myr:.2f}",
        }
    )
    rows.sort(key=lambda r: r["date"])

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def read_history(path: Path | None = None) -> list[dict[str, float | str]]:
    path = path or HISTORY_PATH
    return [
        {
            "date": r["date"],
            "tracked_total_myr": float(r["tracked_total_myr"]),
            "cash_total_myr": float(r["cash_total_myr"]),
            "stocks_total_myr": float(r["stocks_total_myr"]),
        }
        for r in _read_rows(path)
    ]
