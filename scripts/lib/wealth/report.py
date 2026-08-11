"""Report assembly — 数字的唯一 owner。

CLI 文本输出与 web dashboard 都渲染这份报告，估值算术只有一份实现。
拆自 scripts/lib/wealth.py（审计 §3.9）；形状于审计 §3.6 步骤 1 建模。

组装入口只有 `build_report_model()`。`build_report()` 是过渡期 wrapper，
只做 `.model_dump(mode="json")` —— 没有第二份算数实现。
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from ..schema import WealthCfg
from .consistency import catalog_conflicts, check_currencies, stale_files
from .files import FxFile, PortfolioFile, RatesFile, SavingsFile
from .market_layer import resolve_positions, stale_prices
from .report_models import (
    AllocationSection,
    AllocationSlice,
    CandidateOut,
    CapOut,
    CashAccountOut,
    CashSection,
    CatalogConflictOut,
    FxSection,
    MaturityOut,
    PositionOut,
    StaleFile,
    StalePrice,
    StocksSection,
    WealthReport,
)
from .yield_layer import (
    Candidate,
    cap_warnings,
    derive_summary,
    maturity_events,
    rollover_candidates,
)

# Allocation buckets follow economic behaviour, not vehicle branding.
BUCKET_LABELS = {
    "stocks": "股票 (market-valued)",
    "fd": "定存 FD (locked)",
    "mmf": "货币基金 MMF",
    "wallet": "钱包 (instant)",
    "savings": "储蓄账户",
}


def _candidate(c: Candidate) -> CandidateOut:
    return CandidateOut(
        category=c.category,
        key=c.key,
        rate=c.rate,
        basis=c.basis,
        eligible=c.eligible,
        reasons=c.reasons,
        min_deposit=c.min_deposit,
        tenure_months=c.tenure_months,
        notes=c.notes,
    )


def build_report_model(
    savings: SavingsFile,
    rates: RatesFile,
    portfolio: PortfolioFile,
    fx_file: FxFile,
    cfg: WealthCfg,
    today: date,
    data_dir: Path | None = None,
) -> WealthReport:
    check_currencies(savings, rates)
    cash = derive_summary(savings)
    positions = resolve_positions(portfolio, data_dir)
    priced = [p for p in positions if p.priced]
    unpriced = sorted(p.symbol for p in positions if not p.priced)
    usd_myr = fx_file.pair("USD_MYR")
    fx = usd_myr.rate
    fx_age = (today - usd_myr.as_of).days
    stock_total = sum(p.in_myr(fx) for p in priced)

    buckets: dict[str, float] = {"stocks": stock_total}
    for acct in savings.accounts.values():
        buckets[acct.type] = buckets.get(acct.type, 0.0) + acct.balance
    grand_total = sum(buckets.values())

    return WealthReport(
        as_of=today,
        currency=savings.currency,
        thresholds=cfg,
        stale_files=[
            StaleFile(name=n, age_days=a)
            for n, a in stale_files(
                cfg,
                today,
                **{
                    "savings.yaml": savings.updated,
                    "interest_rates.yaml": rates.updated,
                    "portfolio.yaml": portfolio.updated,
                },
            )
        ],
        catalog_conflicts=[
            CatalogConflictOut(
                key=c.key,
                held_rate=c.held_rate,
                catalog_base=c.catalog_base,
                catalog_promo=c.catalog_promo,
            )
            for c in catalog_conflicts(savings, rates)
        ],
        cash=CashSection(
            **cash,
            accounts=[
                CashAccountOut(
                    key=key,
                    balance=a.balance,
                    rate=a.rate,
                    type=a.type,
                    liquidity=a.liquidity,
                    locked=a.locked,
                    cap=a.cap,
                    lock_until=a.lock_until,
                    rate_reason=a.rate_reason,
                    rate_unverified=a.rate_unverified,
                    product_id=a.product_id,
                )
                for key, a in sorted(
                    savings.accounts.items(), key=lambda kv: -kv[1].balance
                )
            ],
        ),
        fx=FxSection(
            pair="USD_MYR",
            rate=fx,
            as_of=usd_myr.as_of,
            age_days=fx_age,
            stale=fx_age > cfg.fx_stale_days,
            source=usd_myr.source,
        ),
        stocks=StocksSection(
            fx_usd_myr=fx,
            total_myr=round(stock_total, 2),
            priced_count=len(priced),
            total_count=len(positions),
            positions=[
                PositionOut(
                    symbol=p.symbol,
                    market=p.market,
                    currency=p.currency,
                    shares=p.shares,
                    avg_cost=p.avg_cost,
                    price=p.price,
                    price_source=p.price_source,
                    price_as_of=p.price_as_of,
                    market_value=p.market_value,
                    market_value_myr=p.in_myr(fx),
                    pnl=p.pnl,
                    pnl_myr=p.pnl_in_myr(fx),
                    pnl_pct=p.pnl_pct,
                )
                for p in sorted(positions, key=lambda x: (x.market, x.symbol))
            ],
            stale_prices=[
                StalePrice(symbol=s, age_days=a)
                for s, a in stale_prices(positions, cfg, today)
            ],
        ),
        # Fail-closed（审计 §3.11）：只要有持仓无价，分母就是偏低的，每个 pct 都偏了 ——
        # 现金类被抬高、股票类通常被压低，方向不能一概而论。这里仍然给出已知金额，
        # 但把 incomplete 与缺失 ticker 一起带出去，好让下游拒绝据此生成 drift/breach。
        allocation=AllocationSection(
            incomplete=bool(unpriced),
            unpriced_symbols=unpriced,
            slices=[
                AllocationSlice(
                    bucket=key,
                    label=BUCKET_LABELS.get(key, key),
                    amount_myr=round(amount, 2),
                    pct=round(amount / grand_total * 100, 2) if grand_total else 0.0,
                )
                for key, amount in sorted(buckets.items(), key=lambda kv: -kv[1])
                if amount > 0
            ],
        ),
        maturity=[
            MaturityOut(
                key=ev.key,
                balance=ev.balance,
                rate=ev.rate,
                lock_until=ev.lock_until,
                days_left=ev.days_left,
                severity=ev.severity,
                renewal_rate=ev.renewal_rate,
                renewal_product=ev.renewal_product,
                candidates=[
                    _candidate(c)
                    for c in rollover_candidates(
                        rates,
                        savings,
                        ev.balance,
                        # 门槛是续做利率；catalog 排不出时才退回合约利率。
                        ev.renewal_rate if ev.renewal_rate is not None else ev.rate,
                        cfg,
                        today,
                        incumbent=ev.renewal_product,
                    )
                ],
            )
            for ev in maturity_events(savings, rates, cfg, today)
        ],
        caps=[
            CapOut(
                key=w.key,
                balance=w.balance,
                cap=w.cap,
                utilization=w.utilization,
                overflow=w.overflow,
            )
            for w in cap_warnings(savings, cfg)
        ],
        tracked_total_myr=round(stock_total + cash["total_cash"], 2),
    )


def build_report(
    savings: SavingsFile,
    rates: RatesFile,
    portfolio: PortfolioFile,
    fx_file: FxFile,
    cfg: WealthCfg,
    today: date,
    data_dir: Path | None = None,
) -> dict:
    """过渡期 wrapper —— 形状的唯一定义在 `build_report_model()`。

    保留它是为了让 `render_text(r: dict)`、现有 dict-indexing 测试与
    `json.dumps(build_report(...))` 在本批保持不变；等 §3.6 步骤 2 的 codegen
    落地、消费者改读生成产物之后，再决定要不要收掉这层。
    """
    return build_report_model(
        savings, rates, portfolio, fx_file, cfg, today, data_dir
    ).model_dump(mode="json")
