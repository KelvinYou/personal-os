#!/usr/bin/env python3
"""Tracked Assets — maturity, valuation & rate monitor.

See docs/plan-wealth-dashboard.md Phases A/B. Deterministic; no LLM and no network.

Both this text output and the web dashboard render from `build_report()`, so
the valuation math has exactly one implementation.

Usage:
    make wealth                  # today
    make wealth DATE=2026-09-01  # 以指定日期为"今天"跑（预演到期）
    make wealth JSON=1           # 机器可读输出（web dashboard 消费这个）
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.config import load_thresholds  # noqa: E402
from lib.wealth import (  # noqa: E402
    build_report,
    load_portfolio,
    load_rates,
    load_savings,
)

RULE = "─" * 66


def _pct(value: float | None) -> str:
    return "  n/a" if value is None else f"{value:.2f}%"


def render_text(r: dict) -> int:
    """Render the report; returns the process exit code (0 ok / 1 warn / 2 crit)."""
    cfg = r["thresholds"]
    exit_code = 0
    print(f"[Tracked Assets] as of {r['as_of']}  ({r['currency']})")
    print(RULE)

    if r["stale_files"]:
        print("\n[Status: Warning] 数据陈旧 — 以下结论的可信度受限")
        for f in r["stale_files"]:
            print(
                f"  - {f['name']}: 已 {f['age_days']} 天未更新 "
                f"(阈值 {cfg['staleness_warn_days']} 天)"
            )
        exit_code = max(exit_code, 1)

    if r["summary_drift"]:
        print("\n[Status: Warning] savings.yaml 的手写 summary 与推导值不一致")
        for d in r["summary_drift"]:
            delta = d["recorded"] - d["derived"]
            print(
                f"  - {d['field']}: 记录 {d['recorded']:,.2f} vs "
                f"推导 {d['derived']:,.2f} (差 {delta:+,.2f})"
            )
        exit_code = max(exit_code, 1)

    if r["catalog_conflicts"]:
        print("\n[Status: Warning] savings.yaml 记录的利率在 rate catalog 中找不到对应档位")
        for c in r["catalog_conflicts"]:
            print(
                f"  - {c['key']}: 记录 {_pct(c['held_rate'])}，"
                f"catalog 只有 base {_pct(c['catalog_base'])} / promo {_pct(c['catalog_promo'])}"
            )
        print("    → 需人工确认实际所处 tier；工具不替你选一个数字。")
        exit_code = max(exit_code, 1)

    cash = r["cash"]
    print("\n■ 现金汇总 (由 accounts 推导)")
    print(f"  总现金        RM{cash['total_cash']:>12,.2f}")
    print(f"  加权平均利率  {cash['weighted_avg_rate']:>12.2f}%")
    print(f"  可动用        RM{cash['liquid_now']:>12,.2f}")
    print(f"  锁定中        RM{cash['locked']:>12,.2f}")

    stocks = r["stocks"]
    print(
        f"\n■ 股票估值 (price owner: ai-stock-analysis pipeline, "
        f"FX {stocks['fx_usd_myr']})"
    )
    for p in stocks["positions"]:
        if p["price"] is None:
            print(f"  [Status: Warning] {p['symbol']:<9} 无价格 — 未计入合计")
            exit_code = max(exit_code, 1)
            continue
        fx = stocks["fx_usd_myr"] if p["currency"] == "USD" else 1.0
        print(
            f"  {p['symbol']:<9} {p['shares']:>6.0f} @ {p['price']:>8,.2f} {p['currency']}  "
            f"= RM{p['market_value_myr']:>10,.2f}  "
            f"P&L {p['pnl'] * fx:>+10,.2f} ({p['pnl_pct']:>+6.1f}%)  "
            f"[{p['price_source']} {p['price_as_of']}]"
        )

    print(
        f"\n  股票市值合计  RM{stocks['total_myr']:>12,.2f}  "
        f"({stocks['priced_count']}/{stocks['total_count']} 已计价)"
    )
    unpriced = [p["symbol"] for p in stocks["positions"] if p["price"] is None]
    if unpriced:
        print(
            f"  [Status: Warning] {len(unpriced)} 个持仓无价格: "
            f"{', '.join(unpriced)} — 合计已低估"
        )

    if stocks["stale_prices"]:
        print(f"\n  [Status: Warning] 价格过期 (阈值 {cfg['price_stale_days']} 天):")
        for sp in stocks["stale_prices"]:
            print(f"    - {sp['symbol']}: {sp['age_days']} 天前")
        exit_code = max(exit_code, 1)

    print("\n■ 资产配置 (按经济行为)")
    for a in r["allocation"]:
        bar = "█" * max(1, round(a["pct"] / 2))
        print(f"  {a['label']:<22} {a['pct']:>5.1f}%  RM{a['amount_myr']:>11,.2f}  {bar}")

    print(f"\n  跟踪资产合计  RM{r['tracked_total_myr']:>12,.2f}")
    print("  (不是 net worth — liabilities 只记月供，不追踪本金)")

    print(f"\n■ 到期监控 (窗口 {cfg['maturity_alert_days']} 天)")
    if not r["maturity"]:
        print("  [Status: OK] 窗口内无锁定产品到期。")
    for ev in r["maturity"]:
        when = (
            f"{abs(ev['days_left'])} 天前已到期"
            if ev["days_left"] < 0
            else f"还剩 {ev['days_left']} 天"
        )
        print(
            f"\n  [Status: {ev['severity']}] {ev['key']} — "
            f"RM{ev['balance']:,.2f} @ {_pct(ev['rate'])}"
        )
        print(f"    到期日 {ev['lock_until']} ({when})")
        exit_code = max(exit_code, 2 if ev["severity"] == "Critical" else 1)

        eligible = [c for c in ev["candidates"] if c["eligible"]]
        blocked = [c for c in ev["candidates"] if not c["eligible"]]

        print(f"\n    到期资金去处 — 优于现有 {_pct(ev['rate'])} 且可投:")
        if not eligible:
            print("      (无) 现有利率已是可及范围内最优，默认动作 = 原地续做")
        for c in eligible:
            tenure = f", {c['tenure_months']}mo" if c["tenure_months"] else ""
            print(
                f"      · {c['key']:<20} {_pct(c['rate'])} ({c['basis']}{tenure})  "
                f"+{c['rate'] - ev['rate']:.2f}% vs 现有"
            )
            for reason in c["reasons"]:
                print(f"          ⚠ {reason}")
            if c["notes"]:
                print(f"          条件: {c['notes']}")

        if blocked:
            print("\n    已排除:")
            for c in blocked:
                print(f"      · {c['key']:<20} {_pct(c['rate'])} ({c['basis']})")
                for reason in c["reasons"]:
                    print(f"          ✗ {reason}")

    print(f"\n■ Cap 利用率 (阈值 {cfg['cap_utilization_warn']:.0%})")
    if not r["caps"]:
        print("  [Status: OK] 无账户接近 cap。")
    for w in r["caps"]:
        print(
            f"  [Status: Warning] {w['key']} — RM{w['balance']:,.2f} / "
            f"cap RM{w['cap']:,.0f} ({w['utilization']:.1%})"
        )
        if w["overflow"] > 0:
            print(f"    超出 RM{w['overflow']:,.2f} 只享 base rate，考虑迁出")
        else:
            print(f"    剩余 headroom RM{w['cap'] - w['balance']:,.2f}")
        exit_code = max(exit_code, 1)

    print(f"\n{RULE}")
    print("范围: 现金/FD/MMF + 股票。NAV 计价产品 (unit trust) 无持仓，不在报告内。")
    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser(description="Tracked Assets monitor")
    parser.add_argument("--date", help="以此日期作为 today (YYYY-MM-DD)，用于预演")
    parser.add_argument("--json", action="store_true", help="输出 JSON 而非文本")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="以严重度作为退出码 (1=Warning, 2=Critical)，供 cron/CI 使用。"
        "默认退出 0——本命令是信息性报告，warning 不代表运行失败。",
    )
    args = parser.parse_args()
    today = date.fromisoformat(args.date) if args.date else date.today()

    cfg = load_thresholds().wealth
    try:
        report = build_report(
            load_savings(), load_rates(), load_portfolio(), cfg, today
        )
    except FileNotFoundError as exc:
        msg = f"找不到财务数据文件: {exc}"
        if args.json:
            print(json.dumps({"error": msg}, ensure_ascii=False))
        else:
            print(f"[Status: Critical] {msg}", file=sys.stderr)
            print(
                "  data submodule 可能未 checkout: git submodule update --init data",
                file=sys.stderr,
            )
        return 1

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    severity = render_text(report)
    return severity if args.strict else 0


if __name__ == "__main__":
    raise SystemExit(main())
