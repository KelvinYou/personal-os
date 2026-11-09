"""Ranked owner actions derived from a built wealth report.

One owner for the wording: /finance renders the list, the Office Finance notice
shows the first item, and scripts/finance_push.py pushes when a new id appears.
Every input is already in the report; this module adds no valuation arithmetic.
"""
from __future__ import annotations

from .report_models import AttentionItem, WealthReport

RANK = {"Critical": 0, "Warning": 1, "OK": 2}
DEBT_NAMES = {"credit_card": "credit card", "housing": "home loan", "auto": "car loan"}


def valuation_observations(r: WealthReport) -> list[str]:
    """Every valuation caveat, one sentence each."""
    return [
        *(f"{f.name}: last updated {f.age_days} days ago." for f in r.stale_files),
        *(f"{c.key}: recorded {c.held_rate:.2f}% differs from the reference catalog. Keep the reported rate until product terms are checked." for c in r.catalog_conflicts),
        *(f"{a.key}: current yield has not been confirmed." for a in r.cash.accounts if a.rate_unverified),
        *(f"{p.symbol}: price is {p.age_days} days old." for p in r.stocks.stale_prices),
        *(f"{key}: outstanding balance observation is stale." for key in r.liabilities.stale_balance_keys),
        *([f"USD conversion uses {r.fx.rate} MYR, observed {r.fx.as_of.isoformat()} ({r.fx.age_days} days old)."] if r.fx.stale else []),
        *([f"Unpriced holdings: {', '.join(r.allocation.unpriced_symbols)}. Asset allocation is incomplete."] if r.allocation.incomplete else []),
        *([f"Regulatory facts need review: {', '.join(r.wealth_rules.stale_facts)}."] if r.wealth_rules.stale else []),
    ]


def _maturity_title(days: int) -> str:
    if days < 0:
        return f"Matured {-days} {'day' if days == -1 else 'days'} ago"
    if days == 0:
        return "Matures today"
    return f"Matures in {days} {'day' if days == 1 else 'days'}"


def attention_items(r: WealthReport) -> list[AttentionItem]:
    items: list[AttentionItem] = []
    debts = r.liabilities.accounts
    missing = [d for d in debts if d.outstanding_myr is None]
    if missing:
        names = ", ".join(DEBT_NAMES.get(d.type, d.key.replace("_", " ")) for d in missing)
        items.append(AttentionItem(
            id="debt_principal_missing", kind="debt_principal_missing", severity="Warning", subject=None,
            title=f"{len(missing)} of {len(debts)} liabilities {'has' if len(missing) == 1 else 'have'} no outstanding principal",
            detail=f"{names}. The after-debt figure leaves these out until balances are recorded.",
            target="liabilities", observations=[]))
    warn = r.thresholds.cap_utilization_warn
    for cap in r.caps:
        if cap.utilization < warn:
            continue
        items.append(AttentionItem(
            id=f"deposit_cap:{cap.key}", kind="deposit_cap", severity="Critical" if cap.overflow > 0 else "Warning",
            subject=cap.key, title=f"Deposit limit {cap.utilization * 100:.1f}% used",
            detail="Part of the balance is above the limit and earns only the base rate." if cap.overflow > 0
            else f"New deposits above the limit earn only the base rate (warning at {warn * 100:.0f}%).",
            target="cash", observations=[]))
    for ev in r.maturity:
        items.append(AttentionItem(
            id=f"maturity:{ev.key}:{ev.lock_until.isoformat()}", kind="maturity", severity=ev.severity, subject=ev.key,
            title=_maturity_title(ev.days_left),
            detail=f"Unlocks {ev.lock_until.isoformat()}. Compare renewal candidates before the date.",
            target="cash", observations=[]))
    observations = valuation_observations(r)
    if observations:
        fx = f"USD uses the {r.fx.as_of.isoformat()} exchange rate. " if r.fx.stale else ""
        items.append(AttentionItem(
            id="valuation", kind="valuation", severity="Warning", subject=None,
            title=f"{len(observations)} valuation observations need review",
            detail=f"{fx}Totals use the recorded values until these are checked.",
            target="stocks" if r.stocks.stale_prices or r.allocation.incomplete else "cash",
            observations=observations))
    return sorted(items, key=lambda i: RANK[i.severity])
