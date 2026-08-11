"""Data layer — the three private finance files and their models.

拆自原 scripts/lib/wealth.py（审计 §3.9）；schema 于审计 §3.5 收紧。

**所有 positions/catalog model 都是 `extra="forbid"`。** 此前一律 `extra="allow"`，
后果不是"宽容"而是"静默"：`rate_unverified` 写成 `rate_unverfied` 会安静地变成
False，dashboard 不再标警告——而那正是 ryt_bank 4% 是否仍生效的唯一提示。
未知字段现在是启动即报错，不是运行时少一行告警。

要扩展就显式加字段；typo 不是扩展。
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, NonNegativeFloat, model_validator

ROOT = Path(__file__).resolve().parents[3]
FINANCE_DIR = ROOT / "data" / "finance"
SAVINGS_PATH = FINANCE_DIR / "savings.yaml"
RATES_PATH = FINANCE_DIR / "interest_rates.yaml"
PORTFOLIO_PATH = FINANCE_DIR / "portfolio.yaml"
FX_PATH = FINANCE_DIR / "fx.yaml"

# Price owner (Phase B decision): the ai-stock-analysis pipeline, not portfolio.yaml.
# That repo is PUBLIC and read-only from here — we never write into it.
STOCK_DATA_DIR = ROOT / "repos" / "ai-stock-analysis" / "data"

STRICT = ConfigDict(extra="forbid")


# ── Savings ──────────────────────────────────────────────────────────────

class SavingsAccount(BaseModel):
    model_config = STRICT
    balance: NonNegativeFloat
    rate: float
    type: Literal["fd", "mmf", "wallet", "savings"]
    rate_reason: str = ""
    liquidity: Literal["instant", "t+1", "locked"]
    locked: bool = False
    lock_start: date | None = None
    lock_until: date | None = None
    cap: NonNegativeFloat | None = None
    role: str | None = None
    # 显式声明，替代此前经 model_extra 读取的写法：那条路径上一个 typo
    # 就足以让告警静默消失，而没有任何东西会报错。
    rate_unverified: bool = False
    # 指向 interest_rates.yaml 的 catalog key。此前靠"YAML key 恰好相同"隐式
    # join——改名任一侧都会静默断开。写了就必须解析得到唯一 entry（见
    # consistency.resolve_products）；不写就是明确声明"此账户无对应 catalog 条目"。
    product_id: str | None = None

    @model_validator(mode="after")
    def _locked_needs_a_maturity_date(self) -> SavingsAccount:
        if self.locked and self.lock_until is None:
            raise ValueError("locked: true 必须配 lock_until —— 否则永远不会进入到期告警窗")
        return self


class Liability(BaseModel):
    """只记月供，不追踪 outstanding 本金——所以它不进 tracked_total。"""

    model_config = STRICT
    type: str
    status: str | None = None
    monthly: NonNegativeFloat | None = None
    monthly_now: NonNegativeFloat | None = None
    monthly_full: NonNegativeFloat | None = None
    end_date: str | None = None
    notes: str = ""


class SavingsFile(BaseModel):
    model_config = STRICT
    schema_version: int = 1
    updated: date
    currency: str = "MYR"
    accounts: dict[str, SavingsAccount]
    liabilities: dict[str, Liability] = {}
    monthly_debt_service: NonNegativeFloat | None = None


# ── Rate catalog ─────────────────────────────────────────────────────────

class RateEntry(BaseModel):
    """One product in the rate catalog.

    形状仍是 optional superset：digital banks 带 base/promo，FD promo 带
    tenure/min_deposit，general_board_rates 只有 prose `rate_range`。
    但 superset ≠ 允许未知字段穿透——那是 typo 的入口，不是扩展点。
    """

    model_config = STRICT
    base_rate: float | None = None
    promo_rate: float | None = None
    tenure_months: int | None = None
    min_deposit: NonNegativeFloat | None = None
    promo_valid_until: date | None = None
    # promo 没有到期日时必须显式声明，而不是靠"字段缺失"默认它永远有效。
    # 语义是「catalog 未记录到期日」，不是「银行承诺无限期」——仍需人工核实。
    ongoing: bool = False
    rate_range: str | None = None
    notes: str = ""

    @model_validator(mode="after")
    def _promo_needs_an_end_or_an_explicit_forever(self) -> RateEntry:
        if self.promo_rate is not None and self.promo_valid_until is None and not self.ongoing:
            raise ValueError(
                "promo_rate 必须配 promo_valid_until，或显式写 ongoing: true —— "
                "缺失日期会让一个已经结束的 promo 永远排在候选第一位"
            )
        return self


class RatesFile(BaseModel):
    model_config = STRICT
    schema_version: int = 1
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


# ── Portfolio ────────────────────────────────────────────────────────────

class UsHolding(BaseModel):
    model_config = STRICT
    symbol: str
    shares: NonNegativeFloat
    avg_cost_usd: NonNegativeFloat
    # Fallback only, for symbols the pipeline does not cover. Pipeline wins.
    manual_price_usd: NonNegativeFloat | None = None
    manual_price_as_of: date | None = None
    notes: str = ""

    @model_validator(mode="after")
    def _manual_price_must_be_dated(self) -> UsHolding:
        _require_dated_manual_price(self.manual_price_usd, self.manual_price_as_of, self.symbol)
        return self


class MyHolding(BaseModel):
    model_config = STRICT
    symbol: str
    code: str
    shares: NonNegativeFloat
    avg_cost: NonNegativeFloat
    manual_price: NonNegativeFloat | None = None
    manual_price_as_of: date | None = None
    notes: str = ""

    @model_validator(mode="after")
    def _manual_price_must_be_dated(self) -> MyHolding:
        _require_dated_manual_price(self.manual_price, self.manual_price_as_of, self.symbol)
        return self


def _require_dated_manual_price(price: float | None, as_of: date | None, symbol: str) -> None:
    """无日期的手工价比没有价还糟：它看起来是最新的。"""
    if (price is None) != (as_of is None):
        raise ValueError(
            f"{symbol}: manual_price 与 manual_price_as_of 必须成对出现 —— "
            "无日期的手工价会被当成新鲜价格计入合计"
        )


class InvestorProfile(BaseModel):
    model_config = STRICT
    age: int | None = None
    objective: str | None = None
    risk_tolerance: str | None = None
    # 现金流，不是持仓事实。审计 §3.7 计划把它移到 policy.yaml 的
    # cash_flow.monthly_investable_amount；在 policy.yaml 落地前先留在这里。
    monthly_savings: NonNegativeFloat | None = None


class PortfolioFile(BaseModel):
    model_config = STRICT
    schema_version: int = 1
    updated: date
    # usd_myr 已移出（审计 §3.7）→ fx.yaml。它和持仓共用一个 `updated` 字段时，
    # 无法区分"持仓变了"和"汇率变了"，于是 SKILL.md 自己规定的
    # 「FX >1 天即 stale」根本无法执行——等于没有 staleness 检查。
    investor_profile: InvestorProfile | None = None
    us_holdings: list[UsHolding] = []
    my_holdings: list[MyHolding] = []

    @model_validator(mode="after")
    def _tickers_are_unique(self) -> PortfolioFile:
        for label, keys in (
            ("us_holdings.symbol", [h.symbol for h in self.us_holdings]),
            ("my_holdings.symbol", [h.symbol for h in self.my_holdings]),
            ("my_holdings.code", [h.code for h in self.my_holdings]),
        ):
            dupes = sorted({k for k in keys if keys.count(k) > 1})
            if dupes:
                raise ValueError(
                    f"{label} 重复: {', '.join(dupes)} —— 同一标的拆成两条会被重复计入合计"
                )
        return self


# ── FX ───────────────────────────────────────────────────────────────────

class FxObservation(BaseModel):
    """一次汇率观测 —— 有自己的 as_of，因为它比持仓变得快得多。"""

    model_config = STRICT
    rate: float
    as_of: date
    source: str = ""

    @model_validator(mode="after")
    def _rate_must_be_positive(self) -> FxObservation:
        if self.rate <= 0:
            raise ValueError("FX rate 必须为正")
        return self


class FxFile(BaseModel):
    model_config = STRICT
    schema_version: int = 1
    base_currency: str = "MYR"
    pairs: dict[str, FxObservation]

    def pair(self, name: str) -> FxObservation:
        try:
            return self.pairs[name]
        except KeyError:
            raise ValueError(
                f"fx.yaml 缺少 {name} —— 拒绝用一个猜出来的汇率折算"
            ) from None


# ── Loaders ──────────────────────────────────────────────────────────────

def load_savings(path: Path | None = None) -> SavingsFile:
    p = path or SAVINGS_PATH
    return SavingsFile.model_validate(yaml.safe_load(p.read_text(encoding="utf-8")))


def load_rates(path: Path | None = None) -> RatesFile:
    p = path or RATES_PATH
    return RatesFile.model_validate(yaml.safe_load(p.read_text(encoding="utf-8")))


def load_portfolio(path: Path | None = None) -> PortfolioFile:
    p = path or PORTFOLIO_PATH
    return PortfolioFile.model_validate(yaml.safe_load(p.read_text(encoding="utf-8")))


def load_fx(path: Path | None = None) -> FxFile:
    p = path or FX_PATH
    return FxFile.model_validate(yaml.safe_load(p.read_text(encoding="utf-8")))
