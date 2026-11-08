"""Private transaction evidence and the canonical monthly asset projection.

Journal evidence never posts balances and does not imply complete cash-flow coverage.
"""
from __future__ import annotations

import fcntl
import json
import os
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .files import FINANCE_DIR

JOURNAL_PATH = FINANCE_DIR / "transactions.jsonl"
STRICT = ConfigDict(extra="forbid", allow_inf_nan=False, str_strip_whitespace=True)


class Transaction(BaseModel):
    model_config = STRICT
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,100}$")
    recorded_on: date
    occurred_on: date | None = None
    kind: Literal["income", "expense", "deposit", "withdrawal", "transfer", "buy", "sell"]
    amount: float = Field(gt=0)
    currency: Literal["MYR", "USD", "CNY"]
    account: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=1000)
    counter_account: str | None = Field(default=None, min_length=1, max_length=100)
    symbol: str | None = Field(default=None, min_length=1, max_length=30)
    quantity: float | None = Field(default=None, gt=0)
    fees: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def coherent(self):
        if self.occurred_on and self.occurred_on > self.recorded_on:
            raise ValueError("Actual date cannot follow the recorded date")
        if self.kind == "transfer":
            if not self.counter_account or self.counter_account == self.account:
                raise ValueError("Transfers require a different destination account")
        elif self.counter_account is not None:
            raise ValueError("Destination account is only valid for a transfer")
        if self.kind in ("buy", "sell"):
            if not self.symbol or self.quantity is None:
                raise ValueError("Trades require a symbol and quantity")
        elif self.symbol is not None or self.quantity is not None or self.fees is not None:
            raise ValueError("Security, quantity and fees are trade-only fields")
        return self


class HistorySnapshot(BaseModel):
    model_config = STRICT
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    tracked_total_myr: float = Field(ge=0)
    cash_total_myr: float = Field(ge=0)
    stocks_total_myr: float = Field(ge=0)

    @model_validator(mode="after")
    def calendar_date(self):
        date.fromisoformat(self.date)
        return self


class MonthlyAssets(BaseModel):
    model_config = STRICT
    month: str
    snapshot: HistorySnapshot
    previous: HistorySnapshot | None
    change: float | None
    changePct: float | None


class InvestmentSlice(BaseModel):
    model_config = STRICT
    bucket: str
    label: str
    amount_myr: float
    pct: float


class InvestmentAllocation(BaseModel):
    model_config = STRICT
    total_myr: float
    incomplete: bool
    unpriced_symbols: list[str]
    slices: list[InvestmentSlice]


class ActivityReport(BaseModel):
    model_config = STRICT
    schema_version: Literal[1] = 1
    as_of: str
    points: list[HistorySnapshot]
    months: list[MonthlyAssets]
    current_month: MonthlyAssets | None
    journal_state: Literal["missing", "partial"]
    transactions: list[Transaction]
    investments: InvestmentAllocation | None


def monthly_assets(points: list[dict]) -> list[MonthlyAssets]:
    months: dict[str, HistorySnapshot] = {}
    for row in sorted(points, key=lambda p: p["date"]):
        point = HistorySnapshot.model_validate(row)
        months[point.date[:7]] = point
    result = []
    for month, snapshot in months.items():
        year, number = map(int, month.split("-"))
        prior = f"{year - 1}-12" if number == 1 else f"{year}-{number - 1:02d}"
        previous = months.get(prior)
        change = round(snapshot.tracked_total_myr - previous.tracked_total_myr, 2) if previous else None
        pct = change / previous.tracked_total_myr * 100 if previous and previous.tracked_total_myr and change is not None else None
        result.append(MonthlyAssets(month=month, snapshot=snapshot, previous=previous, change=change, changePct=pct))
    return result


def _parse_entries(text: str) -> list[Transaction]:
    entries = []
    seen = set()
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            entry = Transaction.model_validate_json(line)
        except ValueError as exc:
            raise ValueError(f"Invalid transaction at line {number}") from exc
        if entry.id in seen:
            raise ValueError(f"Duplicate transaction id at line {number}")
        seen.add(entry.id)
        entries.append(entry)
    return entries


def read_transactions(path: Path = JOURNAL_PATH) -> list[Transaction]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        fcntl.flock(fh, fcntl.LOCK_SH)
        return _parse_entries(fh.read())


def append_transaction(entry: Transaction, path: Path = JOURNAL_PATH) -> bool:
    # Validation precedes even file creation. All writers use the same lock.
    entry = Transaction.model_validate(entry.model_dump())
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        fh.seek(0)
        text = fh.read()
        for existing in _parse_entries(text):
            if existing.id == entry.id:
                if existing == entry:
                    return False
                raise ValueError("Transaction id already exists with different facts")
        fh.seek(0, os.SEEK_END)
        fh.write(("\n" if text and not text.endswith("\n") else "") + entry.model_dump_json() + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    return True


def build_activity(points: list[dict], today: date, journal_path: Path = JOURNAL_PATH, wealth: dict | None = None) -> ActivityReport:
    months = monthly_assets(points)
    entries = read_transactions(journal_path)
    investments = None
    if wealth is not None:
        stocks = wealth["stocks"]
        total = stocks["total_myr"]
        positions = stocks["positions"]
        unpriced = [p["symbol"] for p in positions if p["market_value_myr"] is None]
        investments = InvestmentAllocation(
            total_myr=total, incomplete=bool(unpriced), unpriced_symbols=unpriced,
            slices=[InvestmentSlice(bucket=p["symbol"], label=p["symbol"], amount_myr=p["market_value_myr"], pct=p["market_value_myr"] / total * 100 if total else 0)
                    for p in sorted(positions, key=lambda p: p["market_value_myr"] or 0, reverse=True) if p["market_value_myr"] is not None],
        )
    return ActivityReport(
        investments=investments,
        as_of=today.isoformat(),
        points=[HistorySnapshot.model_validate(p) for p in sorted(points, key=lambda p: p["date"])],
        months=months,
        current_month=next((m for m in months if m.month == today.strftime("%Y-%m")), None),
        journal_state="partial" if journal_path.exists() else "missing",
        transactions=sorted(entries, key=lambda e: (e.recorded_on, e.id), reverse=True),
    )
