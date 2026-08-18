"""Baseline resolution for unfilled manual fields (scripts/lib/defaults.py).

The invariant under test: silence means the baseline was executed, not that
nothing happened — but only for manual fields, only for scoring, and only from
`effective_from` onward.
"""
from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.config import load_thresholds  # noqa: E402
from lib.defaults import MANUAL_FIELDS, measured_fields, resolve, resolve_all  # noqa: E402
from lib.metrics import compute_weekly_aggregate, latest_metrics  # noqa: E402
from lib.schema import DailyLog, DailySpend, LoggingDefaultsCfg, Readiness, Sleep  # noqa: E402

CFG = LoggingDefaultsCfg(
    enabled=True,
    effective_from=date(2026, 8, 17),
    energy_level=7,
    mental_load=3,
    deep_work_hours=8.0,
    deep_work_hours_weekend=0.0,
    caffeine_cutoff="14:00",
    adherence="✅",
    daily_spend=25.9,
    coverage_warn_ratio=0.60,
    adherence_drift_days=3,
)

# 2026-08-18 is a Tuesday, 2026-08-22 a Saturday — both after effective_from.
WEEKDAY = date(2026, 8, 18)
WEEKEND = date(2026, 8, 22)
BEFORE = date(2026, 8, 16)


class ResolveTests(unittest.TestCase):
    def test_empty_weekday_log_gets_every_baseline(self):
        out, filled = resolve(DailyLog(date=WEEKDAY), CFG)
        self.assertCountEqual(filled, MANUAL_FIELDS)
        self.assertEqual(out.energy_level, 7)
        self.assertEqual(out.mental_load, 3)
        self.assertEqual(out.deep_work_hours, 8.0)
        self.assertEqual(out.caffeine_cutoff, "14:00")
        self.assertEqual(out.adherence.timetable, "✅")
        self.assertEqual(out.daily_spend[0].amount, 25.9)

    def test_weekend_deep_work_defaults_to_zero(self):
        out, _ = resolve(DailyLog(date=WEEKEND), CFG)
        self.assertEqual(out.deep_work_hours, 0.0)

    def test_user_values_are_never_overwritten(self):
        log = DailyLog(
            date=WEEKDAY,
            energy_level=3,
            mental_load=6,
            deep_work_hours=2.0,
            caffeine_cutoff="17:30",
            daily_spend=[DailySpend(amount=48.0, category="food", item="外食")],
        )
        out, filled = resolve(log, CFG)
        self.assertEqual(out.energy_level, 3)
        self.assertEqual(out.deep_work_hours, 2.0)
        self.assertEqual(out.caffeine_cutoff, "17:30")
        self.assertEqual(out.daily_spend[0].amount, 48.0)
        self.assertNotIn("energy_level", filled)
        self.assertNotIn("daily_spend", filled)

    def test_zero_deep_work_is_a_value_not_a_gap(self):
        # An explicit 0 must survive; treating it as blank is how 2026-08-09's
        # guessed `deep_work_hours: 0` would silently become 8.
        out, filled = resolve(DailyLog(date=WEEKDAY, deep_work_hours=0.0), CFG)
        self.assertEqual(out.deep_work_hours, 0.0)
        self.assertNotIn("deep_work_hours", filled)

    def test_noop_before_effective_from(self):
        out, filled = resolve(DailyLog(date=BEFORE), CFG)
        self.assertEqual(filled, [])
        self.assertIsNone(out.energy_level)

    def test_noop_when_disabled(self):
        out, filled = resolve(DailyLog(date=WEEKDAY), CFG.model_copy(update={"enabled": False}))
        self.assertEqual(filled, [])
        self.assertIsNone(out.energy_level)


class BoundaryTests(unittest.TestCase):
    """The three boundaries from thresholds.yaml — the dangerous half."""

    def test_coros_blocks_are_never_synthesized(self):
        out, _ = resolve(DailyLog(date=WEEKDAY), CFG)
        self.assertIsNone(out.sleep.duration)
        self.assertIsNone(out.readiness.hrv)
        self.assertIsNone(out.training.today_load)
        self.assertEqual(out.activities, [])

    def test_body_is_never_synthesized(self):
        out, _ = resolve(DailyLog(date=WEEKDAY), CFG)
        self.assertIsNone(out.body.weight)
        self.assertIsNone(out.body.body_fat_pct)

    def test_primary_blocker_absence_stays_absent(self):
        out, _ = resolve(DailyLog(date=WEEKDAY), CFG)
        self.assertIsNone(out.primary_blocker)

    def test_baseline_energy_cannot_silence_a_breaker(self):
        """Breakers read raw logs; a baseline energy of 7 must not mask a real 2."""
        cfg = load_thresholds()
        raw = [DailyLog(date=WEEKDAY, energy_level=2, sleep=Sleep(duration=8.0))]
        resolved, _ = resolve_all(raw, CFG)
        # Resolution left the real value alone...
        self.assertEqual(resolved[0].energy_level, 2)
        # ...and the breaker path sees the raw value either way.
        self.assertEqual(latest_metrics(raw, cfg.sleep.baseline_hours)["energy_level"], 2)

    def test_missing_day_is_not_invented(self):
        """A day with no log file produces no row — only a days_with_log gap."""
        logs = [DailyLog(date=WEEKDAY)]
        resolved, cov = resolve_all(logs, CFG)
        self.assertEqual(len(resolved), 1)
        self.assertEqual(cov.days_with_log, 1)
        self.assertEqual(cov.days_in_week, 7)


class CoverageTests(unittest.TestCase):
    def test_empty_log_reports_zero_coverage(self):
        _, cov = resolve_all([DailyLog(date=WEEKDAY)], CFG)
        self.assertEqual(cov.measured, 0)
        self.assertEqual(cov.expected, len(MANUAL_FIELDS))
        self.assertTrue(cov.is_low(0.60))

    def test_fully_filled_log_reports_full_coverage(self):
        log = DailyLog(
            date=WEEKDAY,
            energy_level=6,
            mental_load=4,
            deep_work_hours=7.0,
            caffeine_cutoff="13:00",
            adherence={"timetable": "⚠️"},
            daily_spend=[DailySpend(amount=30.0)],
        )
        _, cov = resolve_all([log], CFG)
        self.assertEqual(cov.measured, len(MANUAL_FIELDS))
        self.assertEqual(cov.ratio, 1.0)
        self.assertFalse(cov.is_low(0.60))

    def test_coverage_is_independent_of_effective_from(self):
        """Pre-cutover empty logs must read as 0% covered, not 100%.

        Coverage describes what was recorded; resolution being a no-op says
        nothing about whether the user filled anything in.
        """
        _, cov = resolve_all([DailyLog(date=BEFORE)], CFG)
        self.assertEqual(cov.measured, 0)
        self.assertEqual(cov.defaulted, {})

    def test_measured_fields_ignores_blank_strings(self):
        log = DailyLog(date=WEEKDAY, caffeine_cutoff="   ")
        self.assertEqual(measured_fields(log), [])


class ScoringImpactTests(unittest.TestCase):
    """The point of the whole exercise: an unlogged-but-normal week scores fairly."""

    def _week(self, dates):
        return [DailyLog(date=d, sleep=Sleep(duration=7.6), readiness=Readiness(hrv=58, hrv_baseline=58)) for d in dates]

    def test_silent_week_no_longer_scores_near_zero(self):
        from lib.score import compute_base_score

        cfg = load_thresholds()
        week = self._week([date(2026, 8, 17) + __import__("datetime").timedelta(days=i) for i in range(7)])

        raw_agg = compute_weekly_aggregate(week, week, cfg.sleep.baseline_hours)
        raw_score = compute_base_score(raw_agg, week, cfg.scoring)

        resolved, _ = resolve_all(week, CFG)
        res_agg = compute_weekly_aggregate(resolved, resolved, cfg.sleep.baseline_hours)
        res_score = compute_base_score(res_agg, resolved, cfg.scoring)

        # 5 weekdays × 8h = 40h deep work, energy 7, mental load 3, caffeine compliant.
        self.assertEqual(res_agg.total_deep_work, 40.0)
        self.assertGreater(res_score.total, raw_score.total + 30)


if __name__ == "__main__":
    unittest.main()
