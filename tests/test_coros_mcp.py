"""Official evidence boundary and historical compatibility; fixtures only."""
from __future__ import annotations

import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.config import load_thresholds
from lib.coros_mcp import CorosSnapshot, load_snapshot
from lib.schema import DailyLog
from weekly_synthesis import generate_weekly_synthesis


def fixture(records=None):
    return {
        "source": "coros-official-mcp", "retrieved_at": "2026-10-02T09:00:00+08:00",
        "period_start": "2026-09-28", "period_end": "2026-10-02",
        "records": records if records is not None else [
            {"date": "2026-10-02", "tools": ["querySleepData"],
             "sleep": {"duration": 7.75}},
        ],
    }


class OfficialEvidenceTests(unittest.TestCase):
    def test_stdin_and_invalid_inputs(self):
        with patch("sys.stdin", io.StringIO(json.dumps(fixture()))):
            self.assertEqual(load_snapshot("-").records[0].sleep.duration, 7.75)
        cases = [
            {**fixture(), "source": "password-api"},
            {**fixture(), "retrieved_at": "2026-10-02T09:00:00"},
            fixture(fixture()["records"] * 2),
            fixture([{"date": "2026-10-03", "tools": ["sleep"]}]),
            fixture([{"date": "2026-10-02", "tools": ["sleep"], "energy_level": 8}]),
            fixture([{"date": "2026-10-02", "tools": ["sleep"], "sleep": {"duration": float("nan")}}]),
            fixture([{"date": "2026-10-02", "tools": ["sleep"], "sleep": {"duration": 480}}]),
        ]
        for case in cases:
            with self.subTest(case=case), self.assertRaises(ValidationError):
                CorosSnapshot.model_validate(case)

    def test_merge_preserves_manual_without_historical_health_fallback(self):
        local = DailyLog(date=date(2026, 10, 2), energy_level=8, deep_work_hours=0,
                         sleep={"duration": 4}, readiness={"hrv": 90}, body={"weight": 72})
        before = local.model_dump()
        snapshot = CorosSnapshot.model_validate(fixture())
        merged = snapshot.merge([local])[0]
        self.assertEqual(merged.sleep.duration, 7.75)
        self.assertIsNone(merged.readiness.hrv)
        self.assertEqual(merged.energy_level, 8)
        self.assertEqual(merged.deep_work_hours, 0)
        self.assertEqual(merged.body.weight, 72)
        self.assertEqual(local.model_dump(), before)
        empty = CorosSnapshot.model_validate(fixture([]))
        self.assertIsNone(empty.merge([local])[0].sleep.duration)
        metrics = empty.metrics(empty.merge([local]), load_thresholds(), date(2026, 10, 2))
        self.assertNotIn("sleep_duration", metrics)
        self.assertNotIn("hrv", metrics)
        self.assertNotIn("rolling_7d_sleep_debt", metrics)

    def test_previous_day_is_not_current_day(self):
        snapshot = CorosSnapshot.model_validate(fixture([
            {"date": "2026-10-01", "tools": ["sleep", "hrv"],
             "sleep": {"duration": 5}, "readiness": {"hrv": 35}},
        ]))
        metrics = snapshot.metrics(snapshot.merge([]), load_thresholds(), date(2026, 10, 2))
        self.assertNotIn("sleep_duration", metrics)
        self.assertNotIn("hrv", metrics)
        self.assertNotIn("consecutive_poor_sleep", metrics)
        self.assertGreater(metrics["rolling_7d_sleep_debt"], 0)

    def test_empty_activity_result_is_evidence_and_unknown_sleep_is_not_recovery(self):
        snapshot = CorosSnapshot.model_validate(fixture([
            {"date": "2026-09-30", "tools": ["sleep"], "sleep": {"duration": 5}},
            {"date": "2026-10-02", "tools": ["sleep", "activities"],
             "sleep": {"duration": 5}, "activities": []},
        ]))
        manual = DailyLog(date=date(2026, 10, 1), energy_level=8)
        logs = snapshot.merge([manual])
        metrics = snapshot.metrics(logs, load_thresholds(), date(2026, 10, 2))
        self.assertEqual(metrics["consecutive_poor_sleep"], 2)
        empty_activity = CorosSnapshot.model_validate(fixture([
            {"date": "2026-10-02", "tools": ["querySportRecords"], "activities": []},
        ]))
        self.assertEqual(len(empty_activity.merge([])), 1)

    def test_health_only_week_creates_prompt_not_daily_files(self):
        import weekly_synthesis

        snapshot = CorosSnapshot.model_validate(fixture())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(weekly_synthesis, "PROJECT_ROOT", root), \
                    patch.object(weekly_synthesis, "DAILY_DIR", root / "daily"), \
                    patch.object(weekly_synthesis, "iter_all", return_value=iter([])), \
                    patch.object(weekly_synthesis, "emit_event"), \
                    patch("decisions_due.iter_due", return_value=[]), \
                    patch("decisions_due.DECISIONS_DIR", root / "decisions"), \
                    contextlib.redirect_stdout(io.StringIO()):
                generate_weekly_synthesis(date(2026, 10, 2), snapshot)
            prompt = (root / "weekly_report_prompt.md").read_text()
            self.assertIn("COROS official MCP", prompt)
            self.assertIn("7.75", prompt)
            self.assertFalse((root / "daily").exists())
            self.assertFalse((root / "fitness").exists())

    def test_retired_sync_needs_no_dependency_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run([sys.executable, str(ROOT / "scripts/sync_coros.py")],
                                    cwd=tmp, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("official", result.stderr)
            self.assertEqual(list(Path(tmp).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
