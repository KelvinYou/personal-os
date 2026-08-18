"""render_text() 的 golden 快照 + --strict 退出码语义（审计 §3.11）。

为什么要测这个：`wealth_check.py` 里 142 行格式化逻辑此前零覆盖，而
`--strict` 的退出码（0=OK / 1=Warning / 2=Critical）是给自动化/CI 用的——
错了不会有人发现，只会安静地不再告警。

快照跑的是 tests/test_report_contract.py 的同一个「所有 section 都非空」场景，
所以格式化的每条分支都会走到。

重新生成（确认输出改动是有意的再跑）：
    .venv/bin/python3 tests/test_wealth_render.py --write
"""
from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).parent))

from lib.schema import WealthCfg  # noqa: E402
from lib.wealth import (  # noqa: E402
    FxFile,
    PortfolioFile,
    RatesFile,
    SavingsFile,
    build_report,
    load_fx,
    load_portfolio,
    load_rates,
    load_savings,
)
from test_report_contract import contract_report  # noqa: E402
from wealth_check import render_text  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures" / "finance"
STOCK_FIXTURES = Path(__file__).parent / "fixtures" / "stockdata"
GOLDEN_PATH = Path(__file__).parent / "fixtures" / "wealth_render.txt"


def _render(report: dict) -> tuple[str, int]:
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = render_text(report)
    return buf.getvalue(), code


def _quiet_report() -> dict:
    """一份彻底干净的报告：没有锁定产品、没有 cap、没有持仓、文件是新的。

    OK 路径没法从现有 fixture 里挑出来——那份 fixture 刻意把每种告警都摆满了。
    """
    today = date(2026, 8, 11)
    savings = SavingsFile.model_validate(
        {
            "updated": today.isoformat(),
            "currency": "MYR",
            "accounts": {
                "plain": {
                    "balance": 1000.0,
                    "rate": 3.0,
                    "type": "savings",
                    "liquidity": "instant",
                    "locked": False,
                }
            },
        }
    )
    rates = RatesFile.model_validate({"updated": today.isoformat(), "currency": "MYR"})
    portfolio = PortfolioFile.model_validate({"updated": today.isoformat()})
    fx = FxFile.model_validate(
        {"pairs": {"USD_MYR": {"rate": 4.0, "as_of": today.isoformat()}}}
    )
    return build_report(savings, rates, portfolio, fx, WealthCfg(), today, STOCK_FIXTURES)


class RenderGoldenTests(unittest.TestCase):
    def test_output_matches_golden_snapshot(self):
        self.assertTrue(
            GOLDEN_PATH.is_file(),
            f"缺少 {GOLDEN_PATH.name} —— 跑 python3 tests/{Path(__file__).name} --write",
        )
        actual, _ = _render(contract_report())
        expected = GOLDEN_PATH.read_text(encoding="utf-8")
        self.assertEqual(
            actual,
            expected,
            "render_text 输出与快照不一致。改动是有意的话跑 "
            f"python3 tests/{Path(__file__).name} --write 重新生成。",
        )

    def test_every_section_heading_is_present(self):
        """快照只在整体比对；这条保证没有 section 被整块删掉后快照被顺手更新掉。"""
        actual, _ = _render(contract_report())
        for heading in ("■ 现金汇总", "■ 股票估值", "■ 资产配置", "■ 到期监控", "■ Cap 利用率"):
            self.assertIn(heading, actual)


class StrictExitCodeTests(unittest.TestCase):
    """退出码语义 —— 自动化/CI 靠它判断要不要提示用户。"""

    def test_clean_report_exits_zero(self):
        _, code = _render(_quiet_report())
        self.assertEqual(code, 0)

    def test_warning_only_report_exits_one(self):
        # 2026-06-01: 锁定 FD 还在 30 天告警窗之外，但 capped_mmf 已 97.5% 顶 cap。
        report = build_report(
            load_savings(FIXTURES / "savings.yaml"),
            load_rates(FIXTURES / "interest_rates.yaml"),
            load_portfolio(FIXTURES / "portfolio.yaml"),
            load_fx(FIXTURES / "fx.yaml"),
            WealthCfg(),
            date(2026, 6, 1),
            STOCK_FIXTURES,
        )
        self.assertEqual(report["maturity"], [])
        _, code = _render(report)
        self.assertEqual(code, 1)

    def test_critical_maturity_escalates_to_two(self):
        _, code = _render(contract_report())
        self.assertEqual(code, 2)


def _write() -> None:
    text, code = _render(contract_report())
    GOLDEN_PATH.write_text(text, encoding="utf-8")
    print(f"[Status: OK] 已写入 {GOLDEN_PATH.relative_to(ROOT)} (exit code {code})")


if __name__ == "__main__":
    if "--write" in sys.argv:
        _write()
    else:
        unittest.main()
