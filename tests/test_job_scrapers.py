"""learning-agent job scrapers: salary parsing, NaN cleanup, fail-loud on empty scans.

No network: JobSpy is never called — scrape() is stubbed, and parse_salary()
gets hand-built SEEK records.
"""
from __future__ import annotations

import json
import math
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".agents" / "skills" / "learning-agent" / "scripts"))

import fetch_jobs  # noqa: E402
import fetch_jobstreet  # noqa: E402


class ParseSalaryTest(unittest.TestCase):
    def test_v5_label_range_monthly(self):
        rec = {"salaryLabel": "RM\xa08,500 – RM\xa012,500 per month"}
        self.assertEqual(fetch_jobstreet.parse_salary(rec), (8500.0, 12500.0, "monthly"))

    def test_k_suffix_yearly(self):
        rec = {"salaryLabel": "$120k - $150k per year"}
        self.assertEqual(fetch_jobstreet.parse_salary(rec), (120000.0, 150000.0, "yearly"))

    def test_single_amount(self):
        self.assertEqual(
            fetch_jobstreet.parse_salary({"salaryLabel": "SGD 4000 per month"}),
            (4000.0, 4000.0, "monthly"),
        )

    def test_no_amount(self):
        for label in ("", "Competitive", None):
            self.assertEqual(fetch_jobstreet.parse_salary({"salaryLabel": label}), (None, None, None))

    def test_legacy_dict_still_supported(self):
        self.assertEqual(
            fetch_jobstreet.parse_salary({"salary": {"min": 5000, "max": 7000}}),
            (5000, 7000, None),
        )


class CleanTest(unittest.TestCase):
    def test_missing_values_become_none(self):
        self.assertIsNone(fetch_jobs.clean(float("nan")))
        self.assertIsNone(fetch_jobs.clean(None))

    def test_real_values_pass_through(self):
        for v in (0, 5000.0, "MYR", False, ""):
            self.assertEqual(fetch_jobs.clean(v), v)


class FetchJobsMainTest(unittest.TestCase):
    def _run(self, jobs, sources="linkedin,indeed,google"):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        out = Path(tmp.name) / "scan.json"
        argv = ["fetch_jobs.py", "--query", "q", "--location", "my", "--sources", sources, "--output", str(out)]
        with mock.patch.object(fetch_jobs, "scrape", return_value=jobs), mock.patch.object(sys, "argv", argv):
            code = fetch_jobs.main()
        return code, out

    def test_zero_jobs_fails_and_writes_nothing(self):
        code, out = self._run([])
        self.assertNotEqual(code, 0)
        self.assertFalse(out.exists(), "an empty file would be served as today's cache")

    def test_partial_sources_recorded_and_json_strict(self):
        job = {"id": "1", "site": "indeed", "min_amount": None, "max_amount": 6000.0, "interval": "monthly"}
        code, out = self._run([job])
        self.assertEqual(code, 0)
        text = out.read_text()
        payload = json.loads(text, parse_constant=lambda c: self.fail(f"non-standard JSON constant {c}"))
        self.assertEqual(payload["sources_empty"], ["linkedin", "google"])

    def test_nan_in_jobs_is_rejected_not_written(self):
        job = {"id": "1", "site": "indeed", "min_amount": math.nan}
        with self.assertRaises(ValueError):
            self._run([job])


if __name__ == "__main__":
    unittest.main()
