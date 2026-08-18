"""报告形状的 Pydantic model（审计 §3.6 步骤 1）。

此前 `build_report()` 是一段约 130 行的手写嵌套 dict 字面量，而
`web/lib/report.ts` 手抄了一份 TS interface。改 Python 字段名时三件事同时发生：
Python 不报错、TS 编译通过、页面静默渲染 `undefined`。

把 report 建模成 model 是修法的第一步：形状从此有一个可执行的定义，
第二步再从它导出 JSON Schema 并 codegen `report.gen.ts`（届时 TS 侧不再手抄）。

过渡期约定：
  - `build_report_model()` 是唯一的组装入口
  - `build_report()` 仍返回 dict，只是 `.model_dump(mode="json")` 的 wrapper，
    所以 `render_text(r: dict)`、现有 dict-indexing 测试、`json.dumps(...)` 全部不变
  - 全部 `extra="forbid"`：多打一个字段是错误，不是"顺手加的"

字段命名规则：凡是百分比/占比，分母必须写进字段名或紧邻注释里，
否则下游无从判断这个数字能不能拿来比。
"""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict

from ..schema import WealthCfg

STRICT = ConfigDict(extra="forbid")

Severity = Literal["OK", "Warning", "Critical"]


class StaleFile(BaseModel):
    model_config = STRICT
    name: str
    age_days: int


class CatalogConflictOut(BaseModel):
    model_config = STRICT
    key: str
    held_rate: float
    catalog_base: float | None
    catalog_promo: float | None


class CashAccountOut(BaseModel):
    model_config = STRICT
    key: str
    balance: float
    rate: float
    type: str
    liquidity: str
    locked: bool
    cap: float | None
    lock_until: date | None
    rate_reason: str
    rate_unverified: bool
    product_id: str | None


class CashSection(BaseModel):
    model_config = STRICT
    total_cash: float
    weighted_avg_rate: float
    liquid_now: float
    locked: float
    accounts: list[CashAccountOut]


class FxSection(BaseModel):
    """FX 是独立观测，有自己的 as_of —— 它比持仓变得快得多（审计 §3.7）。"""

    model_config = STRICT
    pair: str
    rate: float
    as_of: date
    age_days: int
    stale: bool
    source: str


class PositionOut(BaseModel):
    model_config = STRICT
    symbol: str
    market: Literal["US", "MY"]
    currency: Literal["USD", "MYR"]
    shares: float
    avg_cost: float
    price: float | None
    price_source: Literal["pipeline", "manual", "none"]
    price_as_of: date | None
    market_value: float | None
    market_value_myr: float | None
    pnl: float | None
    # current-FX translated —— 不是真实本币回报（买入时 FX / 手续费 / 汇兑成本
    # 都没记录）。真实 MYR return 要等 transaction ledger（审计 §3.10）。
    pnl_myr: float | None
    pnl_pct: float | None


class StalePrice(BaseModel):
    model_config = STRICT
    symbol: str
    age_days: int


class StocksSection(BaseModel):
    model_config = STRICT
    fx_usd_myr: float
    total_myr: float
    priced_count: int
    total_count: int
    positions: list[PositionOut]
    stale_prices: list[StalePrice]


class AllocationSlice(BaseModel):
    model_config = STRICT
    bucket: str
    label: str
    amount_myr: float
    # 分母 = tracked assets（现金各桶 + 已计价股票）。incomplete 为真时它不完整。
    pct: float


class AllocationSection(BaseModel):
    """有持仓无价时，分母偏低，每一栏 pct 都偏了（审计 §3.11 fail-closed）。

    `incomplete` 不是 UI 标签，是"别拿这些百分比做再平衡判断"的信号。
    """

    model_config = STRICT
    incomplete: bool
    unpriced_symbols: list[str]
    slices: list[AllocationSlice]


class CandidateOut(BaseModel):
    model_config = STRICT
    category: str
    key: str
    rate: float | None
    basis: Literal["promo", "base", "none"]
    eligible: bool
    reasons: list[str]
    min_deposit: float | None
    tenure_months: int | None
    notes: str


class MaturityOut(BaseModel):
    model_config = STRICT
    key: str
    balance: float
    rate: float
    lock_until: date
    days_left: int
    severity: Severity
    # `rate` 是合约利率（到期即失效）；`renewal_rate` 是同产品今天的可得利率。
    # 候选排名的门槛用后者 —— 消费者要展示"不动会掉到多少"就读这个。
    renewal_rate: float | None
    renewal_product: str | None
    candidates: list[CandidateOut]


class CapOut(BaseModel):
    model_config = STRICT
    key: str
    balance: float
    cap: float
    utilization: float
    overflow: float


class WealthRulesHealth(BaseModel):
    model_config = STRICT
    schema_version: int
    stale: bool
    stale_facts: list[str]


class WealthReport(BaseModel):
    model_config = STRICT
    # 消费者（web dashboard / skill）据此判断自己读的是不是它认识的形状。
    # 改动字段含义就 bump 它；删/加字段由 tests/test_report_contract.py 守。
    # v3 (2026-08-18): expose validated regulatory-rule freshness health.
    # v2 (2026-08-12): maturity[] 加 renewal_rate / renewal_product，候选门槛
    # 从合约利率改为续做利率。
    report_schema_version: int = 3
    as_of: date
    currency: str
    thresholds: WealthCfg
    stale_files: list[StaleFile]
    catalog_conflicts: list[CatalogConflictOut]
    cash: CashSection
    fx: FxSection
    stocks: StocksSection
    allocation: AllocationSection
    maturity: list[MaturityOut]
    caps: list[CapOut]
    wealth_rules: WealthRulesHealth
    # 不是 net worth：liabilities 只记月供不追踪本金，NAV 计价产品也不在内。
    tracked_total_myr: float
