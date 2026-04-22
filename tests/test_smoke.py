"""E2E smoke tests covering the lib layer + Option P-d + breakers + scoring."""
from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.breakers import evaluate  # noqa: E402
from lib.config import load_thresholds  # noqa: E402
from lib.daily_log import derive_poor_sleep, iter_all, iter_week, load  # noqa: E402
from lib.metrics import compute_rolling_debt, compute_weekly_aggregate, latest_metrics  # noqa: E402
from lib.score import compute_base_score  # noqa: E402

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "daily"


class FixtureHelpers(unittest.TestCase):
    def _fixtures(self):
        return [load(p) for p in sorted(FIXTURES_DIR.glob("*.md"))]


class PoorSleepDerivationTests(unittest.TestCase):
    def test_short_duration_is_poor(self):
        log = load(FIXTURES_DIR / "2026-01-06.md")
        self.assertLess(log.sleep.duration, 6.5)
        self.assertTrue(derive_poor_sleep(log))

    def test_full_night_not_poor(self):
        log = load(FIXTURES_DIR / "2026-01-05.md")
        self.assertGreaterEqual(log.sleep.duration, 6.5)
        self.assertFalse(derive_poor_sleep(log))

    def test_fragmented_with_low_hrv_is_poor(self):
        # 6.55h sleep but awake 50min and HRV 40 vs baseline 54 (< 0.9×)
        from lib.schema import DailyLog, Sleep, Readiness
        log = DailyLog(
            date=date(2026, 1, 8),
            sleep=Sleep(duration=6.6, awake_min=50),
            readiness=Readiness(hrv=40, hrv_baseline=54),
        )
        self.assertTrue(derive_poor_sleep(log))

    def test_null_duration_is_not_poor(self):
        from lib.schema import DailyLog
        log = DailyLog(date=date(2026, 1, 9))
        self.assertFalse(derive_poor_sleep(log))


class RollingDebtTests(FixtureHelpers):
    def test_rolling_debt_matches_manual(self):
        logs = self._fixtures()
        cfg = load_thresholds()
        debt = compute_rolling_debt(logs, cfg.sleep.baseline_hours, ref=date(2026, 1, 7))
        # baseline 7.5: 01-05 7.8→0, 01-06 5.0→2.5, 01-07 5.5→2.0 => 4.5h
        self.assertAlmostEqual(debt, 4.5, places=2)


class LatestMetricsTests(FixtureHelpers):
    def test_walks_back_for_missing_fields(self):
        from lib.schema import DailyLog
        logs = self._fixtures()
        # append an empty day on 2026-01-08 — latest_metrics should still see
        # 2026-01-07's HRV rather than collapse to {}.
        logs.append(DailyLog(date=date(2026, 1, 8)))
        cfg = load_thresholds()
        m = latest_metrics(logs, cfg.sleep.baseline_hours)
        self.assertIn("hrv", m)
        self.assertEqual(m["hrv"], 45.0)
        self.assertIn("sleep_duration", m)
        self.assertEqual(m["sleep_duration"], 5.5)


class BreakerEvalTests(FixtureHelpers):
    def test_sleep_debt_l1_not_tripped_at_4_5h(self):
        logs = self._fixtures()
        cfg = load_thresholds()
        m = latest_metrics(logs, cfg.sleep.baseline_hours)
        tripped = {t.name for t in evaluate(m, cfg.circuit_breakers)}
        self.assertNotIn("Sleep Debt Level 1", tripped)

    def test_overtraining_warning_trips_on_high_load_ratio(self):
        logs = self._fixtures()
        cfg = load_thresholds()
        m = latest_metrics(logs, cfg.sleep.baseline_hours)
        tripped = {t.name for t in evaluate(m, cfg.circuit_breakers)}
        self.assertIn("Overtraining Warning", tripped)

    def test_missing_metric_does_not_false_positive(self):
        # Empty metrics snapshot should never trip any breaker.
        cfg = load_thresholds()
        tripped = evaluate({}, cfg.circuit_breakers)
        self.assertEqual(tripped, [])


class WeeklyAggregateTests(FixtureHelpers):
    def test_aggregate_surfaces_training_sessions(self):
        logs = self._fixtures()
        cfg = load_thresholds()
        # Treat the 3-log fixture set as one pseudo-week.
        agg = compute_weekly_aggregate(
            logs, logs, cfg.sleep.baseline_hours, today=date(2026, 1, 7)
        )
        self.assertEqual(agg.days_logged, 3)
        self.assertEqual(agg.training_sessions, 1)  # only 01-07 has an activity
        self.assertGreater(agg.avg_hrv, 0)
        self.assertGreater(agg.total_spend, 0)


class BaseScoreTests(FixtureHelpers):
    def test_score_bounded_and_subjective_defaults_to_zero(self):
        logs = self._fixtures()
        cfg = load_thresholds()
        agg = compute_weekly_aggregate(
            logs, logs, cfg.sleep.baseline_hours, today=date(2026, 1, 7)
        )
        bs = compute_base_score(agg, logs, cfg.scoring)
        self.assertGreaterEqual(bs.total, 0)
        self.assertLessEqual(bs.total, 100)
        # Subjective criteria default to 0 basis → 0 points
        names = {c.name: c for c in bs.output.criteria}
        self.assertEqual(names["output_quality"].points, 0)

    def test_subjective_overrides_score(self):
        logs = self._fixtures()
        cfg = load_thresholds()
        agg = compute_weekly_aggregate(
            logs, logs, cfg.sleep.baseline_hours, today=date(2026, 1, 7)
        )
        bs = compute_base_score(
            agg, logs, cfg.scoring,
            subjective={"output_quality": 0.8, "crisis_handling": 1.0},
        )
        names = {c.name: c for c in bs.output.criteria}
        self.assertAlmostEqual(names["output_quality"].points, 0.8 * 10, places=2)


class ProductionLogValidationTests(unittest.TestCase):
    """Sanity: every log under data/daily/ loads through pydantic."""

    def test_all_daily_logs_validate(self):
        daily_dir = ROOT / "data" / "daily"
        if not daily_dir.exists():
            self.skipTest("data/daily not present")
        logs = list(iter_all(daily_dir))
        # iter_all swallows errors; validate by re-loading each file strictly.
        for fp in sorted(daily_dir.glob("*.md")):
            with self.subTest(file=fp.name):
                load(fp)  # raises on failure


if __name__ == "__main__":
    unittest.main()
