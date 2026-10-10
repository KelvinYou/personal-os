"""Focused gates for telemetry-created records and unknown scoring inputs."""
from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.config import load_thresholds  # noqa: E402
from lib.daily_log import load  # noqa: E402
from lib.metrics import compute_weekly_aggregate  # noqa: E402
from lib.schema import DailyLog  # noqa: E402
from lib.score import caffeine_compliance_rate, compute_base_score  # noqa: E402
from patch_coros import create_or_patch_daily  # noqa: E402


class TelemetryRecordTests(unittest.TestCase):
    def test_first_sync_rerun_and_manual_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "2026-09-28.md"
            data = {"sleep": {"duration": 7.5}, "activities": []}
            self.assertTrue(create_or_patch_daily(path, data))
            self.assertEqual(load(path).sleep.duration, 7.5)
            self.assertTrue(load(path).coros_synced)
            self.assertEqual(create_or_patch_daily(path, data), [])
            path.write_text(path.read_text().replace("---\n", "---\nenergy_level: 8\n", 1)
                            + "Manual note\n")
            create_or_patch_daily(path, {"sleep": {"duration": 8.0}})
            self.assertEqual(load(path).energy_level, 8)
            self.assertIn("Manual note", path.read_text())
            self.assertEqual(load(path).sleep.duration, 8.0)
            self.assertTrue(load(path).coros_synced)

    def test_empty_fetch_does_not_create_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "2026-09-28.md"
            self.assertEqual(create_or_patch_daily(path, {"activities": []}), [])
            self.assertFalse(path.exists())
            path.write_text("---\nenergy_level: 8\n---\nManual note\n")
            before = path.read_text()
            self.assertEqual(create_or_patch_daily(path, {"activities": []}), [])
            self.assertEqual(path.read_text(), before)



class UnknownScoreTests(unittest.TestCase):
    def test_explicit_zero_and_nondefault_caffeine_cutoff(self):
        cfg = load_thresholds()
        day = date(2026, 9, 28)
        absent = DailyLog(date=day)
        zero = DailyLog(date=day, deep_work_hours=0, caffeine_cutoff="13:30")
        self.assertIsNone(caffeine_compliance_rate([absent], cutoff="13:00"))
        self.assertEqual(caffeine_compliance_rate([zero], cutoff="14:00"), 1)
        self.assertEqual(caffeine_compliance_rate([zero], cutoff="13:00"), 0)
        for log, expected in ((absent, None), (zero, 0)):
            agg = compute_weekly_aggregate([log], [log], cfg.sleep.baseline_hours)
            score = compute_base_score(agg, [log], cfg.scoring,
                                       caffeine_cutoff="13:00")
            self.assertEqual(score.output.criteria[0].points, expected)
            self.assertFalse(score.complete)

    def test_weight_only_snapshot(self):
        from lib.schema import Body

        log = DailyLog(date=date(2026, 9, 28), body=Body(weight=72.4))
        agg = compute_weekly_aggregate([log], [log], 8)
        self.assertEqual(agg.body_days, 1)
        self.assertEqual(agg.latest_body, {"weight": 72.4})
        self.assertEqual(agg.latest_body_date, log.date)

    def test_partial_week_does_not_claim_weekly_spend_or_sleep_score(self):
        from lib.schema import Sleep, DailySpend

        cfg = load_thresholds()
        log = DailyLog(date=date(2026, 9, 28), sleep=Sleep(duration=8),
                       daily_spend=[DailySpend(amount=0)])
        agg = compute_weekly_aggregate([log], [log], cfg.sleep.baseline_hours)
        score = compute_base_score(agg, [log], cfg.scoring,
                                   caffeine_cutoff=cfg.caffeine.cutoff_time)
        self.assertEqual(agg.spend_days, 1)
        self.assertIsNone(next(c for c in score.habits.criteria
                               if c.name == "weekly_spend").points)
        self.assertIsNone(next(c for c in score.health.criteria
                               if c.name == "poor_sleep_days").points)


if __name__ == "__main__":
    unittest.main()
