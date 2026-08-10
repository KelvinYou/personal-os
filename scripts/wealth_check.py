#!/usr/bin/env python3
"""Tracked Assets — maturity & rate monitor (plan-wealth-dashboard.md Phase A).

Deterministic; no LLM and no network. Covers yield/maturity assets only
(FD / digital bank / interest-bearing savings). Stocks and any NAV-priced
product are out of scope by design.

Usage:
    make wealth                  # today
    make wealth DATE=2026-09-01  # 以指定日期为"今天"跑（预演到期）
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.config import load_thresholds  # noqa: E402
from lib.wealth import (  # noqa: E402
    cap_warnings,
    catalog_conflicts,
    derive_summary,
    load_portfolio,
    load_rates,
    load_savings,
    maturity_events,
    resolve_positions,
    rollover_candidates,
    stale_files,
    stale_prices,
    summary_drift,
)

RULE = "─" * 66


def _fmt_pct(value: float | None) -> str:
    return "  n/a" if value is None else f"{value:.2f}%"


def main() -> int:
    parser = argparse.ArgumentParser(description="Tracked Assets maturity & rate monitor")
    parser.add_argument("--date", help="以此日期作为 today (YYYY-MM-DD)，用于预演")
    args = parser.parse_args()
    today = date.fromisoformat(args.date) if args.date else date.today()

    cfg = load_thresholds().wealth
    try:
        savings = load_savings()
        rates = load_rates()
        portfolio = load_portfolio()
    except FileNotFoundError as exc:
        print(f"[Status: Critical] 找不到财务数据文件: {exc}", file=sys.stderr)
        print("  data submodule 可能未 checkout: git submodule update --init data", file=sys.stderr)
        return 1

    print(f"[Tracked Assets] as of {today}  ({savings.currency})")
    print(RULE)

    exit_code = 0

    # ── 数据新鲜度 ────────────────────────────────────────────────
    stale = stale_files(
        cfg,
        today,
        **{
            "savings.yaml": savings.updated,
            "interest_rates.yaml": rates.updated,
            "portfolio.yaml": portfolio.updated,
        },
    )
    if stale:
        print("\n[Status: Warning] 数据陈旧 — 以下结论的可信度受限")
        for name, age in stale:
            print(f"  - {name}: 已 {age} 天未更新 (阈值 {cfg.staleness_warn_days} 天)")
        exit_code = max(exit_code, 1)

    # ── summary 漂移 ─────────────────────────────────────────────
    drifts = summary_drift(savings)
    if drifts:
        print("\n[Status: Warning] savings.yaml 的手写 summary 与推导值不一致")
        for d in drifts:
            print(
                f"  - {d.field_name}: 记录 {d.recorded:,.2f} vs 推导 {d.derived:,.2f} "
                f"(差 {d.delta:+,.2f})"
            )
        exit_code = max(exit_code, 1)

    # ── 目录一致性 ────────────────────────────────────────────────
    conflicts = catalog_conflicts(savings, rates)
    if conflicts:
        print("\n[Status: Warning] savings.yaml 记录的利率在 rate catalog 中找不到对应档位")
        for c in conflicts:
            base = _fmt_pct(c.catalog_base)
            promo = _fmt_pct(c.catalog_promo)
            print(
                f"  - {c.key}: 记录 {_fmt_pct(c.held_rate)}，"
                f"catalog 只有 base {base} / promo {promo}"
            )
        print("    → 需人工确认实际所处 tier；工具不替你选一个数字。")
        exit_code = max(exit_code, 1)

    # ── 现金汇总 ──────────────────────────────────────────────────
    derived = derive_summary(savings)
    print("\n■ 现金汇总 (由 accounts 推导)")
    print(f"  总现金        RM{derived['total_cash']:>12,.2f}")
    print(f"  加权平均利率  {derived['weighted_avg_rate']:>12.2f}%")
    print(f"  可动用        RM{derived['liquid_now']:>12,.2f}")
    print(f"  锁定中        RM{derived['locked']:>12,.2f}")

    # ── 股票估值 ──────────────────────────────────────────────────
    positions = resolve_positions(portfolio)
    priced = [p for p in positions if p.priced]
    unpriced = [p for p in positions if not p.priced]
    print(f"\n■ 股票估值 (price owner: ai-stock-analysis pipeline, FX {portfolio.usd_myr})")
    for p in sorted(positions, key=lambda x: (x.market, x.symbol)):
        if not p.priced:
            print(f"  [Status: Warning] {p.symbol:<9} 无价格 — 未计入合计")
            continue
        pnl_myr = p.pnl * (portfolio.usd_myr if p.currency == "USD" else 1.0)
        print(
            f"  {p.symbol:<9} {p.shares:>6.0f} @ {p.price:>8,.2f} {p.currency}  "
            f"= RM{p.in_myr(portfolio.usd_myr):>10,.2f}  "
            f"P&L {pnl_myr:>+10,.2f} ({p.pnl_pct:>+6.1f}%)  "
            f"[{p.price_source} {p.price_as_of}]"
        )

    stock_total = sum(p.in_myr(portfolio.usd_myr) for p in priced)
    print(f"\n  股票市值合计  RM{stock_total:>12,.2f}  ({len(priced)}/{len(positions)} 已计价)")
    if unpriced:
        print(
            f"  [Status: Warning] {len(unpriced)} 个持仓无价格: "
            f"{', '.join(p.symbol for p in unpriced)} — 合计已低估"
        )
        exit_code = max(exit_code, 1)

    price_stale = stale_prices(positions, cfg, today)
    if price_stale:
        print(f"\n  [Status: Warning] 价格过期 (阈值 {cfg.price_stale_days} 天):")
        for sym, age in price_stale:
            print(f"    - {sym}: {age} 天前")
        exit_code = max(exit_code, 1)

    print(f"\n  跟踪资产合计  RM{stock_total + derived['total_cash']:>12,.2f}")
    print("  (不是 net worth — liabilities 只记月供，不追踪本金)")

    # ── 到期监控 ──────────────────────────────────────────────────
    events = maturity_events(savings, cfg, today)
    print(f"\n■ 到期监控 (窗口 {cfg.maturity_alert_days} 天)")
    if not events:
        print("  [Status: OK] 窗口内无锁定产品到期。")
    for ev in events:
        when = (
            f"{abs(ev.days_left)} 天前已到期" if ev.days_left < 0 else f"还剩 {ev.days_left} 天"
        )
        print(
            f"\n  [Status: {ev.severity}] {ev.key} — RM{ev.balance:,.2f} @ {_fmt_pct(ev.rate)}"
        )
        print(f"    到期日 {ev.lock_until} ({when})")
        exit_code = max(exit_code, 2 if ev.severity == "Critical" else 1)

        cands = rollover_candidates(rates, savings, ev.balance, ev.rate, cfg, today)
        eligible = [c for c in cands if c.eligible]
        blocked = [c for c in cands if not c.eligible]

        print(f"\n    到期资金去处 — 优于现有 {_fmt_pct(ev.rate)} 且可投:")
        if not eligible:
            print("      (无) 现有利率已是可及范围内最优，默认动作 = 原地续做")
        for c in eligible:
            tenure = f", {c.tenure_months}mo" if c.tenure_months else ""
            print(
                f"      · {c.key:<20} {_fmt_pct(c.rate)} ({c.basis}{tenure})  "
                f"+{c.rate - ev.rate:.2f}% vs 现有"
            )
            for r in c.reasons:
                print(f"          ⚠ {r}")
            if c.notes:
                print(f"          条件: {c.notes}")

        if blocked:
            print("\n    已排除:")
            for c in blocked:
                print(f"      · {c.key:<20} {_fmt_pct(c.rate)} ({c.basis})")
                for r in c.reasons:
                    print(f"          ✗ {r}")

    # ── cap 利用率 ────────────────────────────────────────────────
    caps = cap_warnings(savings, cfg)
    print(f"\n■ Cap 利用率 (阈值 {cfg.cap_utilization_warn:.0%})")
    if not caps:
        print("  [Status: OK] 无账户接近 cap。")
    for w in caps:
        print(
            f"  [Status: Warning] {w.key} — RM{w.balance:,.2f} / cap RM{w.cap:,.0f} "
            f"({w.utilization:.1%})"
        )
        if w.overflow > 0:
            print(f"    超出 RM{w.overflow:,.2f} 只享 base rate，考虑迁出")
        else:
            print(f"    剩余 headroom RM{w.cap - w.balance:,.2f}")
        exit_code = max(exit_code, 1)

    print(f"\n{RULE}")
    print("范围: yield/maturity 类资产。股票与 NAV 计价产品不在本报告内。")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
