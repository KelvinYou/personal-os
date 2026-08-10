"""Tracked Assets — yield/maturity layer (Phase A).

Reads the two private finance files and answers deterministic questions only:
  - 哪个锁定产品快到期了？
  - 到期那笔钱可以去哪，各自什么条件？
  - 哪个账户顶到 cap 了，超出部分在拿 base rate？

No LLM, no market data, no NAV. Market-valued assets (stocks/ETF/unit trust)
are deliberately out of scope — see plan-wealth-dashboard.md §3.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict

from .schema import WealthCfg

ROOT = Path(__file__).resolve().parents[2]
FINANCE_DIR = ROOT / "data" / "finance"
SAVINGS_PATH = FINANCE_DIR / "savings.yaml"
RATES_PATH = FINANCE_DIR / "interest_rates.yaml"
PORTFOLIO_PATH = FINANCE_DIR / "portfolio.yaml"

# Price owner (Phase B decision): the ai-stock-analysis pipeline, not portfolio.yaml.
# That repo is PUBLIC and read-only from here — we never write into it.
STOCK_DATA_DIR = ROOT / "repos" / "ai-stock-analysis" / "data"


# ── Data layer models ────────────────────────────────────────────────────

class SavingsAccount(BaseModel):
    model_config = ConfigDict(extra="allow")
    balance: float
    rate: float
    type: Literal["fd", "mmf", "wallet", "savings"]
    rate_reason: str = ""
    liquidity: Literal["instant", "t+1", "locked"]
    locked: bool = False
    lock_start: date | None = None
    lock_until: date | None = None
    cap: float | None = None
    role: str | None = None


class SavingsSummary(BaseModel):
    model_config = ConfigDict(extra="allow")
    total_cash: float
    weighted_avg_rate: float
    liquid_now: float
    locked: float


class SavingsFile(BaseModel):
    model_config = ConfigDict(extra="allow")
    updated: date
    currency: str = "MYR"
    accounts: dict[str, SavingsAccount]
    summary: SavingsSummary | None = None


class RateEntry(BaseModel):
    """One product in the rate catalog.

    Every field is optional: the catalog mixes shapes (digital banks carry
    base/promo, FD promos carry tenure/min_deposit, general_board_rates
    carries only a prose ``rate_range``).
    """

    model_config = ConfigDict(extra="allow")
    base_rate: float | None = None
    promo_rate: float | None = None
    tenure_months: int | None = None
    min_deposit: float | None = None
    promo_valid_until: date | None = None
    rate_range: str | None = None
    notes: str = ""


class RatesFile(BaseModel):
    model_config = ConfigDict(extra="allow")
    updated: date
    currency: str = "MYR"
    digital_banks: dict[str, RateEntry] = {}
    cash_management: dict[str, RateEntry] = {}
    traditional_fd_promos: dict[str, RateEntry] = {}

    def all_entries(self) -> list[tuple[str, str, RateEntry]]:
        """Flatten to (category, key, entry), catalog order preserved."""
        out: list[tuple[str, str, RateEntry]] = []
        for category in ("digital_banks", "cash_management", "traditional_fd_promos"):
            for key, entry in getattr(self, category).items():
                out.append((category, key, entry))
        return out


class UsHolding(BaseModel):
    model_config = ConfigDict(extra="allow")
    symbol: str
    shares: float
    avg_cost_usd: float
    # Fallback only, for symbols the pipeline does not cover. Pipeline wins.
    manual_price_usd: float | None = None
    manual_price_as_of: date | None = None


class MyHolding(BaseModel):
    model_config = ConfigDict(extra="allow")
    symbol: str
    code: str
    shares: float
    avg_cost: float
    manual_price: float | None = None
    manual_price_as_of: date | None = None


class PortfolioFile(BaseModel):
    model_config = ConfigDict(extra="allow")
    updated: date
    usd_myr: float
    us_holdings: list[UsHolding] = []
    my_holdings: list[MyHolding] = []


def load_savings(path: Path | None = None) -> SavingsFile:
    p = path or SAVINGS_PATH
    return SavingsFile.model_validate(yaml.safe_load(p.read_text(encoding="utf-8")))


def load_rates(path: Path | None = None) -> RatesFile:
    p = path or RATES_PATH
    return RatesFile.model_validate(yaml.safe_load(p.read_text(encoding="utf-8")))


def load_portfolio(path: Path | None = None) -> PortfolioFile:
    p = path or PORTFOLIO_PATH
    return PortfolioFile.model_validate(yaml.safe_load(p.read_text(encoding="utf-8")))


# ── Analysis layer ───────────────────────────────────────────────────────

Severity = Literal["OK", "Warning", "Critical"]


@dataclass
class MaturityEvent:
    key: str
    balance: float
    rate: float
    lock_until: date
    days_left: int
    severity: Severity


@dataclass
class Candidate:
    category: str
    key: str
    rate: float | None  # None = 无可比较利率，见 basis="none"
    basis: Literal["promo", "base", "none"]
    eligible: bool
    reasons: list[str] = field(default_factory=list)
    min_deposit: float | None = None
    tenure_months: int | None = None
    notes: str = ""


@dataclass
class CapWarning:
    key: str
    balance: float
    cap: float
    utilization: float
    overflow: float


@dataclass
class SummaryDrift:
    field_name: str
    recorded: float
    derived: float

    @property
    def delta(self) -> float:
        return self.recorded - self.derived


def maturity_events(
    savings: SavingsFile, cfg: WealthCfg, today: date
) -> list[MaturityEvent]:
    """Locked accounts with a lock_until inside the alert horizon (or past it)."""
    events: list[MaturityEvent] = []
    for key, acct in savings.accounts.items():
        if acct.lock_until is None:
            continue
        days_left = (acct.lock_until - today).days
        if days_left > cfg.maturity_alert_days:
            continue
        severity: Severity = (
            "Critical" if days_left <= cfg.maturity_critical_days else "Warning"
        )
        events.append(
            MaturityEvent(
                key=key,
                balance=acct.balance,
                rate=acct.rate,
                lock_until=acct.lock_until,
                days_left=days_left,
                severity=severity,
            )
        )
    return sorted(events, key=lambda e: e.days_left)


def rollover_candidates(
    rates: RatesFile,
    savings: SavingsFile,
    amount: float,
    current_rate: float,
    cfg: WealthCfg,
    today: date,
) -> list[Candidate]:
    """Rank where a maturing amount could go.

    Eligibility is decided only from structured fields (promo_valid_until,
    min_deposit, and the user's own cap headroom in savings.yaml). Conditions
    that live in prose (spend requirements, stamp counts, tier tables) are
    surfaced verbatim via ``notes`` rather than guessed at — see the
    "unstructured caps" limitation in plan-wealth-dashboard.md §4 Phase B.
    """
    candidates: list[Candidate] = []
    for category, key, entry in rates.all_entries():
        promo_live = entry.promo_rate is not None and (
            entry.promo_valid_until is None or entry.promo_valid_until >= today
        )
        eligible = True
        reasons: list[str] = []

        if promo_live:
            rate, basis = entry.promo_rate, "promo"
        elif entry.base_rate is not None:
            rate, basis = entry.base_rate, "base"
        else:
            # Nothing rankable: an expired promo with no fallback base rate, or a
            # prose-only entry (general_board_rates). Emit it as ineligible rather
            # than dropping it — a silently missing candidate reads as "considered
            # and rejected" when it was never considered at all.
            rate, basis, eligible = None, "none", False
            if entry.rate_range:
                reasons.append(f"仅有 prose rate_range ({entry.rate_range})，无法排名")
            elif entry.promo_rate is None:
                reasons.append("catalog 中既无 base_rate 也无 promo_rate")
            # else: the promo-expiry line appended below already explains it.

        if entry.promo_rate is not None and not promo_live:
            fallback = f"回落至 base {rate:.2f}%" if rate is not None else "且无 base rate 兜底"
            reasons.insert(
                0,
                f"promo {entry.promo_rate:.2f}% 已于 {entry.promo_valid_until} 过期，{fallback}",
            )
        if entry.min_deposit is not None and amount < entry.min_deposit:
            eligible = False
            reasons.append(f"min_deposit RM{entry.min_deposit:,.0f} > 可投 RM{amount:,.2f}")

        held = savings.accounts.get(key)
        if held is not None:
            if held.cap is not None:
                headroom = held.cap - held.balance
                if headroom <= 0:
                    eligible = False
                    reasons.append(f"已顶满 cap RM{held.cap:,.0f}，无 headroom")
                elif headroom < amount:
                    reasons.append(
                        f"仅剩 headroom RM{headroom:,.2f} (cap RM{held.cap:,.0f})，"
                        f"其余部分只拿 base rate"
                    )
            else:
                reasons.append(f"已持有 RM{held.balance:,.2f}，迁入会加重集中度")

        if eligible and rate is not None:
            edge = rate - current_rate
            if edge < 0:
                eligible = False
                reasons.append(f"{rate:.2f}% 低于现有 {current_rate:.2f}% ({edge:+.2f}%)")
            elif edge < cfg.rate_edge_min_pct:
                eligible = False
                reasons.append(
                    f"相对现有 {current_rate:.2f}% 仅 {edge:+.2f}%，"
                    f"低于 rate_edge_min_pct {cfg.rate_edge_min_pct:.2f}%"
                )

        candidates.append(
            Candidate(
                category=category,
                key=key,
                rate=rate,
                basis=basis,
                eligible=eligible,
                reasons=reasons,
                min_deposit=entry.min_deposit,
                tenure_months=entry.tenure_months,
                notes=entry.notes,
            )
        )

    return sorted(
        candidates,
        key=lambda c: (not c.eligible, c.rate is None, -(c.rate or 0.0), c.key),
    )


def cap_warnings(savings: SavingsFile, cfg: WealthCfg) -> list[CapWarning]:
    """Accounts whose balance is at/near cap — overflow silently earns base rate."""
    out: list[CapWarning] = []
    for key, acct in savings.accounts.items():
        if not acct.cap:
            continue
        utilization = acct.balance / acct.cap
        if utilization < cfg.cap_utilization_warn:
            continue
        out.append(
            CapWarning(
                key=key,
                balance=acct.balance,
                cap=acct.cap,
                utilization=utilization,
                overflow=max(0.0, acct.balance - acct.cap),
            )
        )
    return sorted(out, key=lambda w: -w.utilization)


def derive_summary(savings: SavingsFile) -> dict[str, float]:
    """Recompute the four summary values that savings.yaml currently hand-writes."""
    accounts = savings.accounts.values()
    total = sum(a.balance for a in accounts)
    locked = sum(a.balance for a in accounts if a.locked)
    return {
        "total_cash": round(total, 2),
        "weighted_avg_rate": round(
            sum(a.balance * a.rate for a in accounts) / total, 2
        )
        if total
        else 0.0,
        "liquid_now": round(total - locked, 2),
        "locked": round(locked, 2),
    }


def summary_drift(savings: SavingsFile, tolerance: float = 0.01) -> list[SummaryDrift]:
    """Diff the hand-written summary block against the derived values."""
    if savings.summary is None:
        return []
    derived = derive_summary(savings)
    drifts: list[SummaryDrift] = []
    for name, value in derived.items():
        recorded = getattr(savings.summary, name)
        if abs(recorded - value) > tolerance:
            drifts.append(SummaryDrift(field_name=name, recorded=recorded, derived=value))
    return drifts


# ── Market-valued layer (stocks) ─────────────────────────────────────────

PriceSource = Literal["pipeline", "manual", "none"]


@dataclass
class Position:
    symbol: str
    market: Literal["US", "MY"]
    currency: Literal["USD", "MYR"]
    shares: float
    avg_cost: float
    price: float | None
    price_source: PriceSource
    price_as_of: date | None

    @property
    def priced(self) -> bool:
        return self.price is not None

    @property
    def market_value(self) -> float | None:
        return None if self.price is None else self.shares * self.price

    @property
    def cost_basis(self) -> float:
        return self.shares * self.avg_cost

    @property
    def pnl(self) -> float | None:
        mv = self.market_value
        return None if mv is None else mv - self.cost_basis

    @property
    def pnl_pct(self) -> float | None:
        pnl = self.pnl
        return None if pnl is None or not self.cost_basis else pnl / self.cost_basis * 100

    def in_myr(self, usd_myr: float) -> float | None:
        mv = self.market_value
        if mv is None:
            return None
        return mv * usd_myr if self.currency == "USD" else mv


def _pipeline_price(ticker: str, data_dir: Path) -> tuple[float, date] | None:
    """Read close + as_of_date from the ai-stock-analysis technicals product."""
    path = data_dir / ticker / "technicals.json"
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return float(raw["close"]), date.fromisoformat(raw["as_of_date"])
    except (ValueError, KeyError, TypeError):
        return None


def resolve_positions(
    portfolio: PortfolioFile, data_dir: Path | None = None
) -> list[Position]:
    """Price every holding, pipeline first, manual fallback, else unpriced.

    Unpriced positions are returned with ``price=None`` rather than skipped —
    dropping them would understate the portfolio while looking complete.
    """
    d = data_dir or STOCK_DATA_DIR
    positions: list[Position] = []

    for h in portfolio.us_holdings:
        hit = _pipeline_price(h.symbol, d)
        if hit:
            price, as_of, source = hit[0], hit[1], "pipeline"
        elif h.manual_price_usd is not None:
            price, as_of, source = h.manual_price_usd, h.manual_price_as_of, "manual"
        else:
            price, as_of, source = None, None, "none"
        positions.append(
            Position(
                symbol=h.symbol,
                market="US",
                currency="USD",
                shares=h.shares,
                avg_cost=h.avg_cost_usd,
                price=price,
                price_source=source,
                price_as_of=as_of,
            )
        )

    for h in portfolio.my_holdings:
        # Bursa tickers live under their numeric code in the pipeline data dir.
        hit = _pipeline_price(h.code, d)
        if hit:
            price, as_of, source = hit[0], hit[1], "pipeline"
        elif h.manual_price is not None:
            price, as_of, source = h.manual_price, h.manual_price_as_of, "manual"
        else:
            price, as_of, source = None, None, "none"
        positions.append(
            Position(
                symbol=h.symbol,
                market="MY",
                currency="MYR",
                shares=h.shares,
                avg_cost=h.avg_cost,
                price=price,
                price_source=source,
                price_as_of=as_of,
            )
        )

    return positions


def stale_prices(
    positions: list[Position], cfg: WealthCfg, today: date
) -> list[tuple[str, int]]:
    """(symbol, age_days) for priced positions whose price is past its shelf life."""
    out = []
    for p in positions:
        if p.price_as_of is None:
            continue
        age = (today - p.price_as_of).days
        if age > cfg.price_stale_days:
            out.append((p.symbol, age))
    return sorted(out, key=lambda x: -x[1])


# ── Cross-file consistency ───────────────────────────────────────────────

@dataclass
class CatalogConflict:
    key: str
    held_rate: float
    catalog_base: float | None
    catalog_promo: float | None


def catalog_conflicts(savings: SavingsFile, rates: RatesFile) -> list[CatalogConflict]:
    """Accounts whose booked rate matches neither the base nor the promo rate.

    Reports the mismatch; deliberately does not pick a winner — which number is
    real depends on which tier the user is actually in, and that is not
    derivable from either file.
    """
    catalog = {key: entry for _, key, entry in rates.all_entries()}
    out: list[CatalogConflict] = []
    for key, acct in savings.accounts.items():
        entry = catalog.get(key)
        if entry is None:
            continue
        known = {r for r in (entry.base_rate, entry.promo_rate) if r is not None}
        if known and acct.rate not in known:
            out.append(
                CatalogConflict(
                    key=key,
                    held_rate=acct.rate,
                    catalog_base=entry.base_rate,
                    catalog_promo=entry.promo_rate,
                )
            )
    return out


def stale_files(cfg: WealthCfg, today: date, **files: date) -> list[tuple[str, int]]:
    """(filename, age_days) for each file older than staleness_warn_days."""
    out = []
    for name, updated in files.items():
        age = (today - updated).days
        if age > cfg.staleness_warn_days:
            out.append((name, age))
    return sorted(out, key=lambda x: -x[1])


# ── Report assembly ──────────────────────────────────────────────────────
# Single source of truth for the numbers. Both the CLI text output and the
# web dashboard render from this dict — the valuation math is never
# reimplemented downstream, which is the same dual-owner bug Phase B removed,
# just at the code layer instead of the data layer.

# Allocation buckets follow economic behaviour, not vehicle branding.
BUCKET_LABELS = {
    "stocks": "股票 (market-valued)",
    "fd": "定存 FD (locked)",
    "mmf": "货币基金 MMF",
    "wallet": "钱包 (instant)",
    "savings": "储蓄账户",
}


def _iso(value: date | None) -> str | None:
    return None if value is None else value.isoformat()


def _candidate_dict(c: Candidate) -> dict:
    return {
        "category": c.category,
        "key": c.key,
        "rate": c.rate,
        "basis": c.basis,
        "eligible": c.eligible,
        "reasons": c.reasons,
        "min_deposit": c.min_deposit,
        "tenure_months": c.tenure_months,
        "notes": c.notes,
    }


def build_report(
    savings: SavingsFile,
    rates: RatesFile,
    portfolio: PortfolioFile,
    cfg: WealthCfg,
    today: date,
    data_dir: Path | None = None,
) -> dict:
    cash = derive_summary(savings)
    positions = resolve_positions(portfolio, data_dir)
    priced = [p for p in positions if p.priced]
    fx = portfolio.usd_myr
    stock_total = sum(p.in_myr(fx) for p in priced)

    buckets: dict[str, float] = {"stocks": stock_total}
    for acct in savings.accounts.values():
        buckets[acct.type] = buckets.get(acct.type, 0.0) + acct.balance
    grand_total = sum(buckets.values())
    allocation = [
        {
            "bucket": key,
            "label": BUCKET_LABELS.get(key, key),
            "amount_myr": round(amount, 2),
            "pct": round(amount / grand_total * 100, 2) if grand_total else 0.0,
        }
        for key, amount in sorted(buckets.items(), key=lambda kv: -kv[1])
        if amount > 0
    ]

    return {
        "as_of": today.isoformat(),
        "currency": savings.currency,
        "thresholds": cfg.model_dump(),
        "stale_files": [
            {"name": n, "age_days": a}
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
        "summary_drift": [
            {"field": d.field_name, "recorded": d.recorded, "derived": d.derived}
            for d in summary_drift(savings)
        ],
        "catalog_conflicts": [
            {
                "key": c.key,
                "held_rate": c.held_rate,
                "catalog_base": c.catalog_base,
                "catalog_promo": c.catalog_promo,
            }
            for c in catalog_conflicts(savings, rates)
        ],
        "cash": {
            **cash,
            "accounts": [
                {
                    "key": key,
                    "balance": a.balance,
                    "rate": a.rate,
                    "type": a.type,
                    "liquidity": a.liquidity,
                    "locked": a.locked,
                    "cap": a.cap,
                    "lock_until": _iso(a.lock_until),
                    "rate_reason": a.rate_reason,
                    "rate_unverified": bool((a.model_extra or {}).get("rate_unverified")),
                }
                for key, a in sorted(
                    savings.accounts.items(), key=lambda kv: -kv[1].balance
                )
            ],
        },
        "stocks": {
            "fx_usd_myr": fx,
            "total_myr": round(stock_total, 2),
            "priced_count": len(priced),
            "total_count": len(positions),
            "positions": [
                {
                    "symbol": p.symbol,
                    "market": p.market,
                    "currency": p.currency,
                    "shares": p.shares,
                    "avg_cost": p.avg_cost,
                    "price": p.price,
                    "price_source": p.price_source,
                    "price_as_of": _iso(p.price_as_of),
                    "market_value": p.market_value,
                    "market_value_myr": p.in_myr(fx),
                    "pnl": p.pnl,
                    "pnl_pct": p.pnl_pct,
                }
                for p in sorted(positions, key=lambda x: (x.market, x.symbol))
            ],
            "stale_prices": [
                {"symbol": s, "age_days": a} for s, a in stale_prices(positions, cfg, today)
            ],
        },
        "allocation": allocation,
        "maturity": [
            {
                "key": ev.key,
                "balance": ev.balance,
                "rate": ev.rate,
                "lock_until": _iso(ev.lock_until),
                "days_left": ev.days_left,
                "severity": ev.severity,
                "candidates": [
                    _candidate_dict(c)
                    for c in rollover_candidates(
                        rates, savings, ev.balance, ev.rate, cfg, today
                    )
                ],
            }
            for ev in maturity_events(savings, cfg, today)
        ],
        "caps": [
            {
                "key": w.key,
                "balance": w.balance,
                "cap": w.cap,
                "utilization": w.utilization,
                "overflow": w.overflow,
            }
            for w in cap_warnings(savings, cfg)
        ],
        "tracked_total_myr": round(stock_total + cash["total_cash"], 2),
    }
