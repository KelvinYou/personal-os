#!/usr/bin/env python3
# flow: wealth
"""Targeted, comment-preserving edits to data/finance/{savings,portfolio}.yaml.

Built for the web dashboard's inline-edit feature (web/app/api/finance/*).
Both files are hand-authored with load-bearing inline comments (rationale,
staleness warnings, date reasoning) — PyYAML.safe_load/dump (used elsewhere,
e.g. lib/wealth/files.py) is read-only and would silently drop all of that on
a round-trip. So this script is the *only* place that writes these files, and
it uses ruamel.yaml's round-trip mode to touch just the requested leaf values.

Validation reuses the existing pydantic models (SavingsFile/PortfolioFile) —
the schema rules (e.g. "locked needs lock_until") live once, in
scripts/lib/wealth/files.py, not duplicated here or in TypeScript. An edit
that fails validation writes nothing.

Usage:
    python3 scripts/finance_edit.py savings-set --account gxbank \\
        --set balance=20300.00 --set rate_reason="renewed 6mo"
    python3 scripts/finance_edit.py savings-add --account new_bank \\
        --set balance=1000 --set rate=3.0 --set type=wallet --set liquidity=instant
    python3 scripts/finance_edit.py savings-delete --account new_bank
    python3 scripts/finance_edit.py portfolio-set --market US --symbol MSFT \\
        --set shares=2 --set notes="added another share"
    python3 scripts/finance_edit.py portfolio-add --market MY --symbol MYEG \\
        --set code=0138 --set shares=100 --set avg_cost=1.20
    python3 scripts/finance_edit.py portfolio-delete --market MY --symbol MYEG

Every successful mutation against the real files (not a test's --path
override) also upserts today's row in data/finance/history.csv — see
lib/wealth/history.py — so the web dashboard's chart has something to plot
without a separate "log a snapshot" step.

Prints {"ok": true} or {"ok": false, "error": "..."} as JSON to stdout.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ruamel.yaml import YAML  # noqa: E402
from ruamel.yaml.scalarstring import PreservedScalarString  # noqa: E402

from lib.clock import today_kl  # noqa: E402
from lib.config import load_thresholds  # noqa: E402
from lib.wealth import (  # noqa: E402
    build_report,
    load_fx,
    load_portfolio,
    load_rates,
    load_savings,
    record_snapshot,
)
from lib.wealth.files import (  # noqa: E402
    PORTFOLIO_PATH,
    SAVINGS_PATH,
    PortfolioFile,
    SavingsFile,
)

def _represent_none(representer, _data):
    # ruamel's default None representer dumps an empty scalar ("cap:"), which
    # rewrites every *untouched* `null` field's text too. Force explicit
    # "null" so only the fields this script actually edits change on disk.
    return representer.represent_scalar("tag:yaml.org,2002:null", "null")


YAML_RT = YAML(typ="rt")
YAML_RT.preserve_quotes = True
YAML_RT.representer.add_representer(type(None), _represent_none)
# Match this repo's YAML style: "  - key: value" (dash indented 2 under its
# parent, content 2 more past the dash) — ruamel's block-sequence default has
# no dash indent at all, which would re-flow every list in portfolio.yaml.
YAML_RT.indent(mapping=2, sequence=4, offset=2)
# Effectively "never wrap" — the default 80-column width otherwise reflows
# long `notes` strings onto a continuation line even when untouched.
YAML_RT.width = 1 << 20

SAVINGS_FIELDS = {
    "balance": float,
    "rate": float,
    "rate_reason": str,
    "liquidity": str,
    "locked": bool,
    "lock_until": "date_or_null",
    "cap": "float_or_null",
    "rate_unverified": bool,
}

# (field -> coercion) per market; shares/notes are shared, avg_cost is named
# differently between us_holdings (avg_cost_usd) and my_holdings (avg_cost).
US_HOLDING_FIELDS = {"shares": float, "avg_cost_usd": float, "notes": str}
MY_HOLDING_FIELDS = {"shares": float, "avg_cost": float, "notes": str}

# Add-only: identity fields that -set deliberately excludes (type/code/currency
# don't change on an existing row — renaming is "delete + add", not an edit).
SAVINGS_ADD_FIELDS = {**SAVINGS_FIELDS, "type": str, "currency": str}
MY_HOLDING_ADD_FIELDS = {**MY_HOLDING_FIELDS, "code": str}


class EditError(Exception):
    pass


def _coerce(raw: str, kind) -> object:
    if kind is bool:
        low = raw.strip().lower()
        if low in ("true", "1", "yes"):
            return True
        if low in ("false", "0", "no"):
            return False
        raise EditError(f"不是合法的布尔值: {raw!r}")
    if kind == "float_or_null":
        return None if raw.strip() == "" else float(raw)
    if kind == "date_or_null":
        return None if raw.strip() == "" else date.fromisoformat(raw.strip())
    if kind is float:
        return float(raw)
    return raw


def _parse_sets(pairs: list[str], allowed: dict) -> dict[str, object]:
    out: dict[str, object] = {}
    for pair in pairs:
        if "=" not in pair:
            raise EditError(f"--set 需要 field=value 形式: {pair!r}")
        field, raw = pair.split("=", 1)
        field = field.strip()
        if field not in allowed:
            raise EditError(
                f"字段 {field!r} 不在可编辑白名单内 ({', '.join(sorted(allowed))})"
            )
        try:
            out[field] = _coerce(raw, allowed[field])
        except ValueError as exc:
            raise EditError(f"{field}: 值 {raw!r} 无法转换 — {exc}") from exc
    return out


def _atomic_write(path: Path, data) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        YAML_RT.dump(data, fh)
    os.replace(tmp, path)


def _set_scalar(mapping, field: str, value: object) -> None:
    if isinstance(value, str) and "\n" in value:
        value = PreservedScalarString(value)
    # `shares` is conventionally written as a whole number in this repo
    # (`shares: 100`) even though the schema allows fractional shares. Keep
    # that convention instead of dumping "100.0" for every edited holding.
    if field == "shares" and isinstance(value, float) and value.is_integer():
        value = int(value)
    mapping[field] = value


def _record_history_if_real(path_override: Path | None) -> None:
    """Recompute the full report and upsert today's history row.

    Skipped whenever a caller passed an explicit `path` (tests, or any
    future scripted run against a fixture) — history.csv tracks the real
    data/finance/*.yaml only, never a fixture's stand-in numbers.

    Best-effort: history.csv is a derived cache (see lib/wealth/history.py),
    never a second source of truth, so a failure here must never turn an
    already-successful savings/portfolio write into a reported failure —
    that would leave the caller believing the mutation didn't happen when it
    did. Errors go to stderr, not into the {"ok": ...} contract.
    """
    if path_override is not None:
        return
    try:
        today = today_kl()
        report = build_report(
            load_savings(),
            load_rates(),
            load_portfolio(),
            load_fx(),
            load_thresholds().wealth,
            today,
        )
        record_snapshot(
            today,
            report["tracked_total_myr"],
            report["cash"]["total_cash"],
            report["stocks"]["total_myr"],
        )
    except Exception as exc:  # noqa: BLE001 — best-effort, see docstring
        print(f"[finance_edit] history snapshot skipped: {exc}", file=sys.stderr)


def savings_set(account: str, sets: list[str], path: Path | None = None) -> None:
    is_real = path is None
    path = path or SAVINGS_PATH
    fields = _parse_sets(sets, SAVINGS_FIELDS)
    if not fields:
        raise EditError("没有可写入的字段")

    doc = YAML_RT.load(path.read_text(encoding="utf-8"))
    accounts = doc.get("accounts", {})
    if account not in accounts:
        raise EditError(f"savings.yaml 中没有账户 {account!r}")

    acct = accounts[account]
    for field, value in fields.items():
        _set_scalar(acct, field, value)
    doc["updated"] = date.today()

    SavingsFile.model_validate(doc)  # raises pydantic.ValidationError on failure
    _atomic_write(path, doc)
    if is_real:
        _record_history_if_real(None)


def savings_add(account: str, sets: list[str], path: Path | None = None) -> None:
    is_real = path is None
    path = path or SAVINGS_PATH
    fields = _parse_sets(sets, SAVINGS_ADD_FIELDS)
    required = {"balance", "rate", "type", "liquidity"}
    missing = required - fields.keys()
    if missing:
        raise EditError(f"新建账户缺少必填字段: {', '.join(sorted(missing))}")

    doc = YAML_RT.load(path.read_text(encoding="utf-8"))
    accounts = doc.setdefault("accounts", {})
    if account in accounts:
        raise EditError(f"savings.yaml 中已存在账户 {account!r}")

    acct: dict[str, object] = {}
    for field, value in fields.items():
        _set_scalar(acct, field, value)
    accounts[account] = acct
    doc["updated"] = date.today()

    SavingsFile.model_validate(doc)
    _atomic_write(path, doc)
    if is_real:
        _record_history_if_real(None)


def savings_delete(account: str, path: Path | None = None) -> None:
    is_real = path is None
    path = path or SAVINGS_PATH

    doc = YAML_RT.load(path.read_text(encoding="utf-8"))
    accounts = doc.get("accounts", {})
    if account not in accounts:
        raise EditError(f"savings.yaml 中没有账户 {account!r}")
    del accounts[account]
    doc["updated"] = date.today()

    SavingsFile.model_validate(doc)
    _atomic_write(path, doc)
    if is_real:
        _record_history_if_real(None)


def portfolio_set(
    market: str, symbol: str, sets: list[str], path: Path | None = None
) -> None:
    is_real = path is None
    path = path or PORTFOLIO_PATH
    list_key = "us_holdings" if market == "US" else "my_holdings"
    allowed = US_HOLDING_FIELDS if market == "US" else MY_HOLDING_FIELDS
    fields = _parse_sets(sets, allowed)
    if not fields:
        raise EditError("没有可写入的字段")

    doc = YAML_RT.load(path.read_text(encoding="utf-8"))
    holdings = doc.get(list_key, [])
    match = next((h for h in holdings if h.get("symbol") == symbol), None)
    if match is None:
        raise EditError(f"portfolio.yaml 的 {list_key} 中没有 symbol {symbol!r}")

    for field, value in fields.items():
        _set_scalar(match, field, value)
    doc["updated"] = date.today()

    PortfolioFile.model_validate(doc)
    _atomic_write(path, doc)
    if is_real:
        _record_history_if_real(None)


def portfolio_add(
    market: str, symbol: str, sets: list[str], path: Path | None = None
) -> None:
    is_real = path is None
    path = path or PORTFOLIO_PATH
    list_key = "us_holdings" if market == "US" else "my_holdings"
    allowed = US_HOLDING_FIELDS if market == "US" else MY_HOLDING_ADD_FIELDS
    fields = _parse_sets(sets, allowed)
    required = (
        {"shares", "avg_cost_usd"} if market == "US" else {"shares", "avg_cost", "code"}
    )
    missing = required - fields.keys()
    if missing:
        raise EditError(f"新建持仓缺少必填字段: {', '.join(sorted(missing))}")

    doc = YAML_RT.load(path.read_text(encoding="utf-8"))
    holdings = doc.setdefault(list_key, [])
    if any(h.get("symbol") == symbol for h in holdings):
        raise EditError(f"portfolio.yaml 的 {list_key} 中已存在 symbol {symbol!r}")

    entry: dict[str, object] = {"symbol": symbol}
    for field, value in fields.items():
        _set_scalar(entry, field, value)
    holdings.append(entry)
    doc["updated"] = date.today()

    PortfolioFile.model_validate(doc)
    _atomic_write(path, doc)
    if is_real:
        _record_history_if_real(None)


def portfolio_delete(market: str, symbol: str, path: Path | None = None) -> None:
    is_real = path is None
    path = path or PORTFOLIO_PATH
    list_key = "us_holdings" if market == "US" else "my_holdings"

    doc = YAML_RT.load(path.read_text(encoding="utf-8"))
    holdings = doc.get(list_key, [])
    idx = next((i for i, h in enumerate(holdings) if h.get("symbol") == symbol), None)
    if idx is None:
        raise EditError(f"portfolio.yaml 的 {list_key} 中没有 symbol {symbol!r}")
    del holdings[idx]
    doc["updated"] = date.today()

    PortfolioFile.model_validate(doc)
    _atomic_write(path, doc)
    if is_real:
        _record_history_if_real(None)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_savings = sub.add_parser("savings-set")
    p_savings.add_argument("--account", required=True)
    p_savings.add_argument("--set", dest="sets", action="append", default=[])

    p_savings_add = sub.add_parser("savings-add")
    p_savings_add.add_argument("--account", required=True)
    p_savings_add.add_argument("--set", dest="sets", action="append", default=[])

    p_savings_delete = sub.add_parser("savings-delete")
    p_savings_delete.add_argument("--account", required=True)

    p_portfolio = sub.add_parser("portfolio-set")
    p_portfolio.add_argument("--market", required=True, choices=["US", "MY"])
    p_portfolio.add_argument("--symbol", required=True)
    p_portfolio.add_argument("--set", dest="sets", action="append", default=[])

    p_portfolio_add = sub.add_parser("portfolio-add")
    p_portfolio_add.add_argument("--market", required=True, choices=["US", "MY"])
    p_portfolio_add.add_argument("--symbol", required=True)
    p_portfolio_add.add_argument("--set", dest="sets", action="append", default=[])

    p_portfolio_delete = sub.add_parser("portfolio-delete")
    p_portfolio_delete.add_argument("--market", required=True, choices=["US", "MY"])
    p_portfolio_delete.add_argument("--symbol", required=True)

    args = parser.parse_args()

    try:
        if args.command == "savings-set":
            savings_set(args.account, args.sets)
        elif args.command == "savings-add":
            savings_add(args.account, args.sets)
        elif args.command == "savings-delete":
            savings_delete(args.account)
        elif args.command == "portfolio-set":
            portfolio_set(args.market, args.symbol, args.sets)
        elif args.command == "portfolio-add":
            portfolio_add(args.market, args.symbol, args.sets)
        else:
            portfolio_delete(args.market, args.symbol)
    except EditError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    except Exception as exc:  # pydantic ValidationError and friends
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1

    print(json.dumps({"ok": True}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
