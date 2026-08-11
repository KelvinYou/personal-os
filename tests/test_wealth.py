"""Tests for the Tracked Assets yield/maturity layer (Phase A).

Runs against tests/fixtures/finance/ rather than the live private data, so
updating real holdings never turns these red.
"""
from __future__ import annotations

import json
import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from pydantic import ValidationError  # noqa: E402

from lib.config import load_thresholds  # noqa: E402
from lib.schema import WealthCfg  # noqa: E402
from lib.wealth import (  # noqa: E402
    build_report,
    build_report_model,
    cap_warnings,
    catalog_conflicts,
    derive_summary,
    load_fx,
    load_portfolio,
    load_rates,
    load_savings,
    maturity_events,
    resolve_positions,
    resolve_products,
    rollover_candidates,
    stale_files,
    stale_prices,
)

FIXTURES = Path(__file__).parent / "fixtures" / "finance"
STOCK_FIXTURES = Path(__file__).parent / "fixtures" / "stockdata"
TODAY = date(2026, 8, 11)


def _cfg() -> WealthCfg:
    return WealthCfg()


def _savings():
    return load_savings(FIXTURES / "savings.yaml")


def _rates():
    return load_rates(FIXTURES / "interest_rates.yaml")


def _fx():
    return load_fx(FIXTURES / "fx.yaml")


class ThresholdsWiringTests(unittest.TestCase):
    def test_wealth_block_loads_from_real_thresholds(self):
        cfg = load_thresholds().wealth
        self.assertGreater(cfg.maturity_alert_days, cfg.maturity_critical_days)
        self.assertGreater(cfg.rate_edge_min_pct, 0)


class MaturityTests(unittest.TestCase):
    def test_locked_account_inside_window_is_flagged(self):
        events = maturity_events(_savings(), _rates(), _cfg(), TODAY)
        self.assertEqual([e.key for e in events], ["locked_fd"])
        self.assertEqual(events[0].days_left, 9)
        self.assertEqual(events[0].severity, "Warning")  # 9 > critical window (7)

    def test_severity_escalates_inside_critical_window(self):
        cfg = _cfg()
        far = maturity_events(_savings(), _rates(), cfg, date(2026, 8, 1))
        self.assertEqual(far[0].severity, "Warning")
        near = maturity_events(_savings(), _rates(), cfg, date(2026, 8, 18))
        self.assertEqual(near[0].severity, "Critical")

    def test_outside_window_is_silent(self):
        self.assertEqual(maturity_events(_savings(), _rates(), _cfg(), date(2026, 6, 1)), [])

    def test_already_matured_still_reported(self):
        events = maturity_events(_savings(), _rates(), _cfg(), date(2026, 8, 25))
        self.assertEqual(events[0].days_left, -5)
        self.assertEqual(events[0].severity, "Critical")

    def test_no_product_id_leaves_renewal_rate_unresolved(self):
        # locked_fd 没有 product_id → catalog 排不出续做利率。必须是 None，
        # 不能悄悄拿合约利率冒充"续做还有这么多"。
        ev = maturity_events(_savings(), _rates(), _cfg(), TODAY)[0]
        self.assertIsNone(ev.renewal_rate)
        self.assertIsNone(ev.renewal_product)

    def test_renewal_rate_comes_from_catalog_not_from_the_contract_rate(self):
        savings = _savings()
        # 合约 4.00%，但同产品今天只给得出 base 1.00%（promo 已过期）。
        savings.accounts["locked_fd"].product_id = "expired_with_base"
        ev = maturity_events(savings, _rates(), _cfg(), TODAY)[0]
        self.assertEqual(ev.rate, 4.00)
        self.assertEqual(ev.renewal_rate, 1.00)
        self.assertEqual(ev.renewal_product, "expired_with_base")


class RolloverHurdleTests(unittest.TestCase):
    """到期比较的门槛是**续做利率**，不是即将失效的合约利率。

    回归背景 (2026-08-12)：GXBank 的 4.00% FD 到期，同产品续做只剩 3.55%，
    但引擎拿 4.00% 当门槛，把 3.88% 的 KDI Save 判成"低于现有"排除掉，
    最后输出"默认动作 = 原地续做" —— 恰好推荐了候选池里第二差的选项。
    """

    def _setup(self):
        savings = _savings()
        savings.accounts["locked_fd"].product_id = "expired_with_base"  # 续做 1.00%
        return savings

    def test_candidate_between_renewal_and_contract_rate_is_eligible(self):
        savings = self._setup()
        # capped_mmf 3.00%：低于合约 4.00%，但远高于续做 1.00% → 必须可选。
        cands = rollover_candidates(
            _rates(), savings, 10000.0, 1.00, _cfg(), TODAY,
            incumbent="expired_with_base",
        )
        c = next(x for x in cands if x.key == "capped_mmf")
        self.assertTrue(c.eligible, f"应可选，实际被排除: {c.reasons}")

    def test_incumbent_is_the_hurdle_not_a_concentration_reject(self):
        savings = self._setup()
        cands = rollover_candidates(
            _rates(), savings, 10000.0, 1.00, _cfg(), TODAY,
            incumbent="expired_with_base",
        )
        c = next(x for x in cands if x.key == "expired_with_base")
        self.assertFalse(c.eligible)
        self.assertTrue(any("原地续做" in r for r in c.reasons), c.reasons)
        # 续做不是"迁入会加重集中度"——钱本来就在那儿。
        self.assertFalse(any("集中度" in r for r in c.reasons), c.reasons)

    def test_report_wires_renewal_rate_into_the_hurdle(self):
        savings = self._setup()
        report = build_report(
            savings,
            _rates(),
            load_portfolio(FIXTURES / "portfolio.yaml"),
            _fx(),
            _cfg(),
            TODAY,
            STOCK_FIXTURES,
        )
        ev = report["maturity"][0]
        self.assertEqual(ev["renewal_rate"], 1.00)
        eligible = {c["key"] for c in ev["candidates"] if c["eligible"]}
        self.assertIn("capped_mmf", eligible)


class RolloverCandidateTests(unittest.TestCase):
    def _candidates(self, amount=10000.0, current_rate=4.00):
        return rollover_candidates(
            _rates(), _savings(), amount, current_rate, _cfg(), TODAY
        )

    def _by_key(self, key):
        return next(c for c in self._candidates() if c.key == key)

    def test_every_catalog_entry_is_represented(self):
        # No silent drops: an omitted candidate reads as "rejected" when it was
        # never evaluated. 7 entries across the three catalog sections.
        self.assertEqual(len(self._candidates()), 7)

    def test_live_promo_ranks_first_and_is_eligible(self):
        top = self._candidates()[0]
        self.assertEqual(top.key, "high_promo_bank")
        self.assertEqual(top.rate, 5.50)
        self.assertEqual(top.basis, "promo")
        self.assertTrue(top.eligible)

    def test_expired_promo_falls_back_to_base_rate(self):
        c = self._by_key("expired_with_base")
        self.assertEqual(c.rate, 1.00)
        self.assertEqual(c.basis, "base")
        self.assertFalse(c.eligible)
        self.assertTrue(any("已于 2026-07-01 过期" in r for r in c.reasons))

    def test_expired_promo_without_base_is_surfaced_not_dropped(self):
        c = self._by_key("expired_no_base")
        self.assertIsNone(c.rate)
        self.assertEqual(c.basis, "none")
        self.assertFalse(c.eligible)

    def test_prose_only_entry_is_surfaced_not_dropped(self):
        c = self._by_key("general_board_rates")
        self.assertIsNone(c.rate)
        self.assertTrue(any("rate_range" in r for r in c.reasons))

    def test_min_deposit_above_amount_blocks(self):
        c = self._by_key("big_min_fd")
        self.assertFalse(c.eligible)
        self.assertTrue(any("min_deposit" in r for r in c.reasons))

    def test_min_deposit_passes_when_amount_is_large_enough(self):
        big = rollover_candidates(
            _rates(), _savings(), 80000.0, 4.00, _cfg(), TODAY
        )
        self.assertTrue(next(c for c in big if c.key == "big_min_fd").eligible)

    def test_existing_cap_headroom_is_cross_referenced(self):
        c = self._by_key("capped_mmf")
        self.assertTrue(any("headroom RM500.00" in r for r in c.reasons))

    def test_rate_below_hurdle_is_reported_as_below_not_as_thin_edge(self):
        c = self._by_key("expired_with_base")
        self.assertTrue(any("低于门槛" in r for r in c.reasons))
        self.assertFalse(any("rate_edge_min_pct" in r for r in c.reasons))

    def test_thin_positive_edge_is_rejected_by_rate_edge(self):
        # fd_ok at 4.50 vs a current 4.40 → +0.10, under the 0.25 floor.
        cands = rollover_candidates(_rates(), _savings(), 10000.0, 4.40, _cfg(), TODAY)
        c = next(x for x in cands if x.key == "fd_ok")
        self.assertFalse(c.eligible)
        self.assertTrue(any("rate_edge_min_pct" in r for r in c.reasons))

    def test_eligible_candidates_sort_before_blocked(self):
        cands = self._candidates()
        first_blocked = next(i for i, c in enumerate(cands) if not c.eligible)
        self.assertTrue(all(c.eligible for c in cands[:first_blocked]))
        self.assertTrue(all(not c.eligible for c in cands[first_blocked:]))


class CapTests(unittest.TestCase):
    def test_only_accounts_near_cap_warn(self):
        warns = cap_warnings(_savings(), _cfg())
        self.assertEqual([w.key for w in warns], ["capped_mmf"])
        self.assertAlmostEqual(warns[0].utilization, 0.975)
        self.assertEqual(warns[0].overflow, 0.0)

    def test_overflow_is_computed_when_balance_exceeds_cap(self):
        savings = _savings()
        savings.accounts["capped_mmf"].balance = 22000.0
        self.assertEqual(cap_warnings(savings, _cfg())[0].overflow, 2000.0)


class SummaryTests(unittest.TestCase):
    def test_derived_summary_matches_fixture(self):
        self.assertEqual(
            derive_summary(_savings()),
            {
                "total_cash": 30000.00,
                "weighted_avg_rate": 3.34,
                "liquid_now": 20000.00,
                "locked": 10000.00,
            },
        )


class PriceResolutionTests(unittest.TestCase):
    def _positions(self):
        portfolio = load_portfolio(FIXTURES / "portfolio.yaml")
        return {p.symbol: p for p in resolve_positions(portfolio, STOCK_FIXTURES)}

    def test_portfolio_yaml_carries_no_current_price_field(self):
        # Phase B: portfolio.yaml is holding facts only. If a current_price sneaks
        # back in, the pipeline stops being the single price owner.
        raw = (FIXTURES / "portfolio.yaml").read_text(encoding="utf-8")
        self.assertNotIn("current_price", raw)

    def test_pipeline_price_wins_for_us_symbol(self):
        p = self._positions()["PIPED"]
        self.assertEqual((p.price, p.price_source), (150.0, "pipeline"))
        self.assertEqual(p.price_as_of, date(2026, 8, 8))

    def test_bursa_position_resolves_by_numeric_code_not_symbol(self):
        p = self._positions()["BURSA_OK"]
        self.assertEqual((p.price, p.price_source), (2.50, "pipeline"))

    def test_manual_fallback_used_only_without_pipeline_coverage(self):
        p = self._positions()["MANUALED"]
        self.assertEqual((p.price, p.price_source), (6.00, "manual"))
        self.assertEqual(p.price_as_of, date(2026, 7, 1))

    def test_unpriced_position_is_kept_not_dropped(self):
        positions = self._positions()
        self.assertIn("NOPRICE", positions)
        p = positions["NOPRICE"]
        self.assertFalse(p.priced)
        self.assertIsNone(p.market_value)
        self.assertIsNone(p.in_myr(4.0))

    def test_all_holdings_are_represented(self):
        self.assertEqual(len(self._positions()), 5)

    def test_unparseable_pipeline_file_falls_through_rather_than_crashing(self):
        from lib.wealth import PortfolioFile

        portfolio = PortfolioFile.model_validate(
            {
                "updated": "2026-08-10",
                "us_holdings": [{"symbol": "BROKEN", "shares": 1, "avg_cost_usd": 10.0}],
            }
        )
        p = resolve_positions(portfolio, STOCK_FIXTURES)[0]
        self.assertEqual(p.price_source, "none")

    def test_valuation_and_pnl(self):
        p = self._positions()["PIPED"]
        self.assertEqual(p.market_value, 300.0)
        self.assertEqual(p.cost_basis, 200.0)
        self.assertEqual(p.pnl, 100.0)
        self.assertAlmostEqual(p.pnl_pct, 50.0)

    def test_usd_position_converts_to_myr_and_myr_position_does_not(self):
        positions = self._positions()
        self.assertEqual(positions["PIPED"].in_myr(4.0), 1200.0)
        self.assertEqual(positions["BURSA_OK"].in_myr(4.0), 250.0)

    def test_stale_price_flags_only_the_old_one(self):
        positions = list(self._positions().values())
        self.assertEqual(stale_prices(positions, _cfg(), TODAY), [("MANUALED", 41)])


class CatalogConflictTests(unittest.TestCase):
    def test_matching_rate_is_not_a_conflict(self):
        self.assertEqual(catalog_conflicts(_savings(), _rates()), [])

    def test_rate_matching_neither_tier_is_reported(self):
        savings = _savings()
        savings.accounts["capped_mmf"].rate = 3.30  # catalog has 3.00 / 3.00
        conflicts = catalog_conflicts(savings, _rates())
        self.assertEqual([c.key for c in conflicts], ["capped_mmf"])
        self.assertEqual(conflicts[0].held_rate, 3.30)

    def test_account_absent_from_catalog_is_skipped(self):
        # locked_fd / roomy_wallet have no catalog entry — silence, not a false alarm.
        savings = _savings()
        savings.accounts["locked_fd"].rate = 99.0
        self.assertEqual(catalog_conflicts(savings, _rates()), [])


class BuildReportTests(unittest.TestCase):
    """The report dict is the contract the web dashboard renders from."""

    def _report(self):
        return build_report(
            _savings(),
            _rates(),
            load_portfolio(FIXTURES / "portfolio.yaml"),
            _fx(),
            _cfg(),
            TODAY,
            STOCK_FIXTURES,
        )

    def test_is_json_serialisable(self):
        # The web layer parses this over a pipe; a stray date or dataclass
        # would break the dashboard at runtime, not at test time.
        json.dumps(self._report(), ensure_ascii=False)

    def test_totals_agree_with_the_parts(self):
        r = self._report()
        self.assertAlmostEqual(
            r["tracked_total_myr"],
            round(r["stocks"]["total_myr"] + r["cash"]["total_cash"], 2),
        )

    def test_allocation_buckets_follow_economic_behaviour(self):
        r = self._report()
        self.assertEqual(
            {a["bucket"] for a in r["allocation"]["slices"]},
            {"stocks", "fd", "mmf", "wallet"},
        )

    def test_allocation_percentages_sum_to_100(self):
        r = self._report()
        self.assertAlmostEqual(
            sum(a["pct"] for a in r["allocation"]["slices"]), 100.0, places=1
        )

    def test_allocation_is_sorted_largest_first(self):
        amounts = [a["amount_myr"] for a in self._report()["allocation"]["slices"]]
        self.assertEqual(amounts, sorted(amounts, reverse=True))

    def test_unpriced_holding_excluded_from_stock_total_but_still_listed(self):
        r = self._report()
        self.assertEqual(r["stocks"]["priced_count"], 4)
        self.assertEqual(r["stocks"]["total_count"], 5)
        symbols = {p["symbol"] for p in r["stocks"]["positions"]}
        self.assertIn("NOPRICE", symbols)

    def test_maturity_events_carry_their_candidates(self):
        r = self._report()
        self.assertEqual(len(r["maturity"]), 1)
        self.assertEqual(r["maturity"][0]["key"], "locked_fd")
        self.assertEqual(len(r["maturity"][0]["candidates"]), 7)

    def test_rate_unverified_flag_survives_into_the_report(self):
        savings = _savings()
        savings.accounts["capped_mmf"].rate_unverified = True
        r = build_report(
            savings,
            _rates(),
            load_portfolio(FIXTURES / "portfolio.yaml"),
            _fx(),
            _cfg(),
            TODAY,
            STOCK_FIXTURES,
        )
        flagged = {a["key"] for a in r["cash"]["accounts"] if a["rate_unverified"]}
        self.assertEqual(flagged, {"capped_mmf"})


class ReportModelTests(unittest.TestCase):
    """审计 §3.6 步骤 1：报告形状有一个可执行定义，dict 只是它的 dump。"""

    def _args(self):
        return (
            _savings(),
            _rates(),
            load_portfolio(FIXTURES / "portfolio.yaml"),
            _fx(),
            _cfg(),
            TODAY,
            STOCK_FIXTURES,
        )

    def test_dict_wrapper_is_exactly_the_model_dump(self):
        # 只有一份组装实现——wrapper 里不能偷偷再算一次。
        self.assertEqual(
            build_report(*self._args()),
            build_report_model(*self._args()).model_dump(mode="json"),
        )

    def test_report_model_rejects_unknown_fields(self):
        from lib.wealth import WealthReport

        payload = build_report_model(*self._args()).model_dump()
        WealthReport.model_validate(payload)  # sanity
        with self.assertRaises(ValidationError):
            WealthReport.model_validate({**payload, "tracked_total_myrr": 1.0})


class SchemaStrictnessTests(unittest.TestCase):
    """审计 §3.5：未知字段是启动即报错，不是运行时安静少一行告警。"""

    def test_typo_in_savings_field_name_is_rejected(self):
        from lib.wealth import SavingsAccount

        good = {
            "balance": 1.0,
            "rate": 3.0,
            "type": "mmf",
            "liquidity": "t+1",
        }
        SavingsAccount.model_validate(good)  # sanity
        with self.assertRaises(ValidationError):
            # 这个 typo 此前会静默变成 False，dashboard 不再标"利率未核实"——
            # 而那正是 ryt_bank 的 4% 是否仍生效的唯一提示。
            SavingsAccount.model_validate({**good, "rate_unverfied": True})

    def test_locked_account_without_maturity_date_is_rejected(self):
        from lib.wealth import SavingsAccount

        with self.assertRaises(ValidationError):
            SavingsAccount.model_validate(
                {
                    "balance": 1.0,
                    "rate": 3.0,
                    "type": "fd",
                    "liquidity": "locked",
                    "locked": True,
                }
            )

    def test_negative_balance_is_rejected(self):
        from lib.wealth import SavingsAccount

        with self.assertRaises(ValidationError):
            SavingsAccount.model_validate(
                {"balance": -1.0, "rate": 3.0, "type": "mmf", "liquidity": "t+1"}
            )

    def test_undated_manual_price_is_rejected(self):
        from lib.wealth import MyHolding

        with self.assertRaises(ValidationError):
            MyHolding.model_validate(
                {
                    "symbol": "X",
                    "code": "1",
                    "shares": 1,
                    "avg_cost": 1.0,
                    "manual_price": 2.0,  # 没有 as_of
                }
            )

    def test_promo_without_expiry_must_declare_ongoing(self):
        from lib.wealth import RateEntry

        with self.assertRaises(ValidationError):
            RateEntry.model_validate({"promo_rate": 5.0})
        RateEntry.model_validate({"promo_rate": 5.0, "ongoing": True})

    def test_duplicate_ticker_is_rejected(self):
        from lib.wealth import PortfolioFile

        with self.assertRaises(ValidationError):
            PortfolioFile.model_validate(
                {
                    "updated": "2026-08-10",
                    "my_holdings": [
                        {"symbol": "A", "code": "1", "shares": 1, "avg_cost": 1.0},
                        {"symbol": "A", "code": "2", "shares": 1, "avg_cost": 1.0},
                    ],
                }
            )


class ProductIdTests(unittest.TestCase):
    """审计 §3.5：catalog join 走显式 product_id，不再靠 YAML key 同名。"""

    def test_declared_product_id_resolves(self):
        self.assertEqual(resolve_products(_savings(), _rates()), {"capped_mmf": "capped_mmf"})

    def test_account_without_product_id_is_not_joined(self):
        # locked_fd / roomy_wallet 没写 product_id → 不做交叉检查，也不误报
        savings = _savings()
        savings.accounts["locked_fd"].rate = 99.0
        self.assertEqual(catalog_conflicts(savings, _rates()), [])

    def test_dangling_product_id_is_an_error_not_silence(self):
        savings = _savings()
        savings.accounts["capped_mmf"].product_id = "renamed_in_catalog"
        with self.assertRaises(ValueError) as ctx:
            resolve_products(savings, _rates())
        self.assertIn("renamed_in_catalog", str(ctx.exception))


class FxTests(unittest.TestCase):
    """审计 §3.7：FX 是独立观测，换算发生在 report 层。"""

    def _report(self, today):
        return build_report(
            _savings(),
            _rates(),
            load_portfolio(FIXTURES / "portfolio.yaml"),
            _fx(),
            _cfg(),
            today,
            STOCK_FIXTURES,
        )

    def test_fx_has_its_own_as_of_and_staleness(self):
        fresh = self._report(TODAY)["fx"]
        self.assertEqual((fresh["pair"], fresh["age_days"], fresh["stale"]), ("USD_MYR", 1, False))
        old = self._report(date(2026, 8, 20))["fx"]
        self.assertTrue(old["stale"])
        self.assertEqual(old["age_days"], 10)

    def test_pnl_myr_is_computed_in_the_report_not_the_renderer(self):
        positions = {p["symbol"]: p for p in self._report(TODAY)["stocks"]["positions"]}
        piped = positions["PIPED"]  # USD, pnl 100.0 @ fx 4.0
        self.assertEqual(piped["pnl"], 100.0)
        self.assertEqual(piped["pnl_myr"], 400.0)
        bursa = positions["BURSA_OK"]  # 已是 MYR，不该再乘一次
        self.assertEqual(bursa["pnl_myr"], bursa["pnl"])

    def test_unpriced_position_has_no_pnl_myr(self):
        positions = {p["symbol"]: p for p in self._report(TODAY)["stocks"]["positions"]}
        self.assertIsNone(positions["NOPRICE"]["pnl_myr"])

    def test_missing_pair_refuses_to_guess(self):
        from lib.wealth import FxFile

        with self.assertRaises(ValueError):
            FxFile.model_validate({"pairs": {}}).pair("USD_MYR")


class AllocationFailClosedTests(unittest.TestCase):
    """审计 §3.11：有持仓无价时，每一栏 pct 都偏了 —— 必须显式说出来。"""

    def _report(self, portfolio_path):
        return build_report(
            _savings(),
            _rates(),
            load_portfolio(portfolio_path),
            _fx(),
            _cfg(),
            TODAY,
            STOCK_FIXTURES,
        )

    def test_unpriced_holding_marks_allocation_incomplete(self):
        alloc = self._report(FIXTURES / "portfolio.yaml")["allocation"]
        self.assertTrue(alloc["incomplete"])
        self.assertEqual(alloc["unpriced_symbols"], ["NOPRICE"])

    def test_fully_priced_portfolio_is_complete(self):
        from lib.wealth import PortfolioFile

        portfolio = PortfolioFile.model_validate(
            {
                "updated": "2026-08-10",
                "us_holdings": [{"symbol": "PIPED", "shares": 2, "avg_cost_usd": 100.0}],
            }
        )
        alloc = build_report(
            _savings(), _rates(), portfolio, _fx(), _cfg(), TODAY, STOCK_FIXTURES
        )["allocation"]
        self.assertFalse(alloc["incomplete"])
        self.assertEqual(alloc["unpriced_symbols"], [])


class StalenessTests(unittest.TestCase):
    def test_stale_file_reported_with_age(self):
        stale = stale_files(_cfg(), date(2026, 10, 1), **{"savings.yaml": date(2026, 8, 1)})
        self.assertEqual(stale, [("savings.yaml", 61)])

    def test_fresh_file_silent(self):
        self.assertEqual(
            stale_files(_cfg(), TODAY, **{"savings.yaml": date(2026, 8, 1)}), []
        )


if __name__ == "__main__":
    unittest.main()
