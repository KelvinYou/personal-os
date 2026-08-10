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

from lib.config import load_thresholds  # noqa: E402
from lib.schema import WealthCfg  # noqa: E402
from lib.wealth import (  # noqa: E402
    build_report,
    cap_warnings,
    catalog_conflicts,
    derive_summary,
    load_portfolio,
    load_rates,
    load_savings,
    maturity_events,
    resolve_positions,
    rollover_candidates,
    stale_files,
    stale_prices,
    summary_drift,
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


class ThresholdsWiringTests(unittest.TestCase):
    def test_wealth_block_loads_from_real_thresholds(self):
        cfg = load_thresholds().wealth
        self.assertGreater(cfg.maturity_alert_days, cfg.maturity_critical_days)
        self.assertGreater(cfg.rate_edge_min_pct, 0)


class MaturityTests(unittest.TestCase):
    def test_locked_account_inside_window_is_flagged(self):
        events = maturity_events(_savings(), _cfg(), TODAY)
        self.assertEqual([e.key for e in events], ["locked_fd"])
        self.assertEqual(events[0].days_left, 9)
        self.assertEqual(events[0].severity, "Warning")  # 9 > critical window (7)

    def test_severity_escalates_inside_critical_window(self):
        cfg = _cfg()
        far = maturity_events(_savings(), cfg, date(2026, 8, 1))
        self.assertEqual(far[0].severity, "Warning")
        near = maturity_events(_savings(), cfg, date(2026, 8, 18))
        self.assertEqual(near[0].severity, "Critical")

    def test_outside_window_is_silent(self):
        self.assertEqual(maturity_events(_savings(), _cfg(), date(2026, 6, 1)), [])

    def test_already_matured_still_reported(self):
        events = maturity_events(_savings(), _cfg(), date(2026, 8, 25))
        self.assertEqual(events[0].days_left, -5)
        self.assertEqual(events[0].severity, "Critical")


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

    def test_rate_below_current_is_reported_as_below_not_as_thin_edge(self):
        c = self._by_key("expired_with_base")
        self.assertTrue(any("低于现有" in r for r in c.reasons))
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

    def test_consistent_file_reports_no_drift(self):
        self.assertEqual(summary_drift(_savings()), [])

    def test_drift_is_detected(self):
        savings = _savings()
        savings.summary.total_cash = 31000.00
        drifts = summary_drift(savings)
        self.assertEqual([d.field_name for d in drifts], ["total_cash"])
        self.assertAlmostEqual(drifts[0].delta, 1000.00)


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
                "usd_myr": 4.0,
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
            {a["bucket"] for a in r["allocation"]},
            {"stocks", "fd", "mmf", "wallet"},
        )

    def test_allocation_percentages_sum_to_100(self):
        r = self._report()
        self.assertAlmostEqual(sum(a["pct"] for a in r["allocation"]), 100.0, places=1)

    def test_allocation_is_sorted_largest_first(self):
        amounts = [a["amount_myr"] for a in self._report()["allocation"]]
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
        savings.accounts["capped_mmf"].__pydantic_extra__["rate_unverified"] = True
        r = build_report(
            savings,
            _rates(),
            load_portfolio(FIXTURES / "portfolio.yaml"),
            _cfg(),
            TODAY,
            STOCK_FIXTURES,
        )
        flagged = {a["key"] for a in r["cash"]["accounts"] if a["rate_unverified"]}
        self.assertEqual(flagged, {"capped_mmf"})


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
