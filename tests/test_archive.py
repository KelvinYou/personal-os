"""Cold-log archiving + COROS staging-buffer pruning (scripts/archive.py).

Runs the real `--apply` path against a temp data/ tree, because the risky part
of this script is deletion and a dry-run test would never exercise it.
"""
from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import archive  # noqa: E402
from lib.schema import Adherence, Body, DailyLog, Readiness, Sleep  # noqa: E402

TODAY = date(2026, 8, 16)


def _daily_md(d: date, **fm) -> str:
    lines = ["---"]
    for k, v in fm.items():
        if isinstance(v, dict):
            lines.append(f"{k}:")
            for kk, vv in v.items():
                lines.append(f"  {kk}: {vv}")
        else:
            lines.append(f"{k}: {v}")
    lines += ["---", "", f"log body for {d}"]
    return "\n".join(lines)


class ArchiveSandbox(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.daily = base / "daily"
        self.fitness = base / "fitness"
        self.arch = base / "archive"
        self.daily.mkdir()
        self.fitness.mkdir()

        self._orig = (archive.DAILY_DIR, archive.FITNESS_DIR, archive.ARCHIVE_DIR)
        archive.DAILY_DIR = self.daily
        archive.FITNESS_DIR = self.fitness
        archive.ARCHIVE_DIR = self.arch
        # lib.daily_log.load_safe resolves paths passed to it, so no patch needed there.

    def tearDown(self):
        archive.DAILY_DIR, archive.FITNESS_DIR, archive.ARCHIVE_DIR = self._orig
        self.tmp.cleanup()

    # -- helpers -----------------------------------------------------------
    def write_day(self, d: date, **fm):
        (self.daily / f"{d.isoformat()}.md").write_text(_daily_md(d, **fm), encoding="utf-8")

    def write_fitness(self, d: date):
        (self.fitness / f"{d.isoformat()}.yaml").write_text(
            f"date: '{d.isoformat()}'\nsleep:\n  duration: 7.5\n", encoding="utf-8"
        )


class KeepRuleTests(unittest.TestCase):
    def test_routine_blocker_alone_is_not_kept(self):
        """Pre-W22 logs filled primary_blocker daily as commentary, not as an event."""
        log = DailyLog(date=TODAY, primary_blocker="前夜睡眠质量差导致精力基线下降", energy_level=6,
                       sleep=Sleep(duration=6.8))
        self.assertIsNone(archive.keep_reason(log, energy_low=4))

    def test_energy_critical_is_kept(self):
        log = DailyLog(date=TODAY, primary_blocker="健身房突发黑视", energy_level=3)
        self.assertEqual(archive.keep_reason(log, energy_low=4), "energy-critical")

    def test_plan_break_is_kept(self):
        log = DailyLog(date=TODAY, adherence=Adherence(timetable="🔴"))
        self.assertEqual(archive.keep_reason(log, energy_low=4), "plan-break")

    def test_severe_short_sleep_is_kept(self):
        log = DailyLog(date=TODAY, sleep=Sleep(duration=4.2))
        self.assertEqual(archive.keep_reason(log, energy_low=4), "severe-short-sleep")

    def test_measurement_day_is_not_kept(self):
        """body.csv carries the full series; the surrounding file adds nothing."""
        log = DailyLog(date=TODAY, body=Body(weight=70.1, body_fat_pct=18.0), energy_level=7)
        self.assertIsNone(archive.keep_reason(log, energy_low=4))


class ApplyTests(ArchiveSandbox):
    def test_full_apply_cycle(self):
        cold = TODAY - timedelta(days=200)   # 2026-01-28, well outside hot window
        cold_keep = cold + timedelta(days=1)
        hot = TODAY - timedelta(days=10)

        self.write_day(cold, energy_level=7, deep_work_hours=8, body={"weight": 71.5},
                       primary_blocker="会议挤掉下午 block", sleep={"duration": 7.2})
        self.write_day(cold_keep, energy_level=2, sleep={"duration": 4.1})   # energy-critical
        self.write_day(hot, energy_level=6, sleep={"duration": 7.8})

        self.write_fitness(cold)        # old + has daily → prunable
        self.write_fitness(hot)         # inside replay window → kept

        archive.run(hot_days=90, fitness_days=30, apply=True, today=TODAY)

        # cold digestible day folded away; kept day and hot day survive
        self.assertFalse((self.daily / f"{cold.isoformat()}.md").exists())
        self.assertTrue((self.daily / f"{cold_keep.isoformat()}.md").exists())
        self.assertTrue((self.daily / f"{hot.isoformat()}.md").exists())

        # staging buffer pruned only where a daily log already holds the data
        self.assertFalse((self.fitness / f"{cold.isoformat()}.yaml").exists())
        self.assertTrue((self.fitness / f"{hot.isoformat()}.yaml").exists())

        # digest carries the week row and the blocker text
        q = (self.arch / "2026-Q1.md").read_text(encoding="utf-8")
        self.assertIn("2026-W05", q)
        self.assertIn("会议挤掉下午 block", q)

        # body.csv spans the whole history, including the folded day
        with (self.arch / "body.csv").open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(rows[0]["date"], cold.isoformat())
        self.assertEqual(rows[0]["weight"], "71.5")

    def test_cold_orphan_data_reaches_the_digest(self):
        """The whole point of repairing orphans before pruning.

        For an orphan past the hot window, repair creates a daily log that the
        same run then folds into a digest row. That is the intended end state:
        without the repair step the fitness prune would drop those nights on the
        floor, since no daily log ever held them.

        (On the real data only 1 of the 20 orphans took this path — the other 19
        fell inside the hot window and survive as full logs, per the next test.)
        """
        orphan = TODAY - timedelta(days=150)  # 2026-03-19, cold
        self.write_fitness(orphan)

        archive.run(hot_days=90, fitness_days=30, apply=True, today=TODAY)

        # both files are gone...
        self.assertFalse((self.daily / f"{orphan.isoformat()}.md").exists())
        self.assertFalse((self.fitness / f"{orphan.isoformat()}.yaml").exists())
        # ...but the night it recorded is in the archive
        q = (self.arch / "2026-Q1.md").read_text(encoding="utf-8")
        self.assertIn("2026-W12", q)
        self.assertIn("7.50", q)  # the 7.5h duration from the fitness yaml

    def test_hot_orphan_is_repaired_in_place(self):
        orphan = TODAY - timedelta(days=5)
        self.write_fitness(orphan)

        archive.run(hot_days=90, fitness_days=30, apply=True, today=TODAY)

        created = self.daily / f"{orphan.isoformat()}.md"
        self.assertTrue(created.exists())
        self.assertIn("duration: 7.5", created.read_text(encoding="utf-8"))
        self.assertTrue((self.fitness / f"{orphan.isoformat()}.yaml").exists())

    def test_dry_run_changes_nothing(self):
        cold = TODAY - timedelta(days=200)
        self.write_day(cold, energy_level=7, sleep={"duration": 7.2})
        self.write_fitness(cold)

        archive.run(hot_days=90, fitness_days=30, apply=False, today=TODAY)

        self.assertTrue((self.daily / f"{cold.isoformat()}.md").exists())
        self.assertTrue((self.fitness / f"{cold.isoformat()}.yaml").exists())
        self.assertFalse(self.arch.exists())

    def test_idempotent(self):
        """Re-running must preserve body points already moved to the archive."""
        cold = TODAY - timedelta(days=200)
        hot = TODAY - timedelta(days=10)
        self.write_day(
            cold,
            energy_level=7,
            sleep={"duration": 7.2},
            body={"weight": 71.5},
        )
        self.write_day(
            hot,
            energy_level=7,
            sleep={"duration": 7.2},
            body={"weight": 70.5},
        )
        archive.run(hot_days=90, fitness_days=30, apply=True, today=TODAY)
        body_csv = self.arch / "body.csv"
        with body_csv.open(encoding="utf-8") as f:
            first_rows = list(csv.DictReader(f))
        first_dates = [row["date"] for row in first_rows]
        self.assertEqual(first_dates, [cold.isoformat(), hot.isoformat()])

        archive.run(hot_days=90, fitness_days=30, apply=True, today=TODAY)
        with body_csv.open(encoding="utf-8") as f:
            second_rows = list(csv.DictReader(f))
        self.assertEqual(second_rows, first_rows)


if __name__ == "__main__":
    unittest.main()
