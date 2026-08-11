"""Tracked Assets — 现金/到期/利率 + 股票估值。

原本是单文件 `scripts/lib/wealth.py`（709 行 / 4 个职责）。按
`docs/plan-wealth-dashboard.md` §3 的分层词汇拆包（审计 §3.9），使文档与代码互查：

    files.py         — 三个私有 finance 文件的 model + loader
    yield_layer.py   — 到期事件 / 续做候选 / cap 利用率 / 现金汇总推导
    market_layer.py  — 持仓定价（pipeline 优先，manual 兜底）与价格陈旧
    consistency.py   — 跨文件矛盾：catalog 冲突、product_id 解析、币种、文件陈旧
    report_models.py — 报告形状的 Pydantic model（§3.6 步骤 1）
    report.py        — build_report_model，数字的唯一 owner

本模块只做 re-export：`from lib.wealth import build_report, load_savings, ...`
的既有 import 路径完全不变，拆包对 consumer 是零改动。

数据流：
    savings/rates/portfolio.yaml ─┐
    ai-stock-analysis pipeline ───┴─> build_report() ─> CLI 文本 / web dashboard
"""
from __future__ import annotations

from .consistency import (
    CatalogConflict,
    catalog_conflicts,
    check_currencies,
    resolve_products,
    stale_files,
)
from .files import (
    FINANCE_DIR,
    FX_PATH,
    PORTFOLIO_PATH,
    RATES_PATH,
    ROOT,
    SAVINGS_PATH,
    STOCK_DATA_DIR,
    FxFile,
    FxObservation,
    InvestorProfile,
    Liability,
    MyHolding,
    PortfolioFile,
    RateEntry,
    RatesFile,
    SavingsAccount,
    SavingsFile,
    UsHolding,
    load_fx,
    load_portfolio,
    load_rates,
    load_savings,
)
from .market_layer import (
    Position,
    PriceSource,
    resolve_positions,
    stale_prices,
)
from .report import BUCKET_LABELS, build_report, build_report_model
from .report_models import WealthReport
from .yield_layer import (
    Candidate,
    CapWarning,
    MaturityEvent,
    Severity,
    cap_warnings,
    derive_summary,
    maturity_events,
    rollover_candidates,
)

__all__ = [
    "BUCKET_LABELS",
    "Candidate",
    "CapWarning",
    "CatalogConflict",
    "FINANCE_DIR",
    "FX_PATH",
    "FxFile",
    "FxObservation",
    "InvestorProfile",
    "Liability",
    "MaturityEvent",
    "MyHolding",
    "PORTFOLIO_PATH",
    "PortfolioFile",
    "Position",
    "PriceSource",
    "RATES_PATH",
    "ROOT",
    "RateEntry",
    "RatesFile",
    "SAVINGS_PATH",
    "STOCK_DATA_DIR",
    "SavingsAccount",
    "SavingsFile",
    "Severity",
    "UsHolding",
    "WealthReport",
    "build_report",
    "build_report_model",
    "cap_warnings",
    "catalog_conflicts",
    "check_currencies",
    "derive_summary",
    "load_fx",
    "load_portfolio",
    "load_rates",
    "load_savings",
    "maturity_events",
    "resolve_positions",
    "resolve_products",
    "rollover_candidates",
    "stale_files",
    "stale_prices",
]
