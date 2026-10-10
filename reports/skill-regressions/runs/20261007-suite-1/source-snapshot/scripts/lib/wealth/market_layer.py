"""Market-valued layer — 股票持仓定价与陈旧检查。

价格唯一 owner 是 ai-stock-analysis pipeline，manual 仅作兜底且必须带 as_of。
拆自 scripts/lib/wealth.py（审计 §3.9）。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal

from ..schema import WealthCfg
from .files import STOCK_DATA_DIR, PortfolioFile


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

    def pnl_in_myr(self, usd_myr: float) -> float | None:
        """按**当前** FX 折算的 P&L —— 不是真实本币回报。

        买入时的 FX、手续费与汇兑成本都没有记录，所以这个数字回答的是
        "现在把它换成 MYR 值多少"，而不是"这笔投资赚了多少 MYR"。
        真实 MYR return 要等 transaction ledger（审计 §3.10）。

        它必须活在这里而不是渲染层：`wealth_check.py` 曾经自己做 `pnl * fx`,
        那是全系统唯一一处渲染层算数——结果 web 侧不敢重算，干脆不显示绝对
        P&L，于是 CLI 和 dashboard 对同一持仓给出的信息量不一样。
        """
        pnl = self.pnl
        if pnl is None:
            return None
        return pnl * usd_myr if self.currency == "USD" else pnl


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

