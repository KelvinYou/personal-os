"""Yield/maturity layer — 到期、续做候选、cap 利用率、现金汇总推导。

只回答确定性问题，不碰市场价格。拆自 scripts/lib/wealth.py（审计 §3.9）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Literal

from ..schema import WealthCfg
from .consistency import resolve_products
from .files import RatesFile, SavingsFile


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
    "unstructured caps" limitation in docs/plan-wealth-dashboard.md §4 Phase B.
    """
    candidates: list[Candidate] = []
    # catalog key → 持有该产品的账户。走显式 product_id，不再假设两份文件的
    # YAML key 恰好同名（审计 §3.5）。
    held_by = {
        product: savings.accounts[account]
        for account, product in resolve_products(savings, rates).items()
    }
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

        held = held_by.get(key)
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
    """现金汇总的唯一 owner —— 单向推导。

    savings.yaml 曾经手写一份 summary block（Phase B 移除，模型于审计 §3.5 删除）。
    这里只往一个方向算：accounts → 汇总，没有可以写回去的入口。
    """
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

