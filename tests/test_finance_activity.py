"""Finance activity contract tests use synthetic inputs only."""
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

from scripts.lib.wealth.activity import ActivityReport, Transaction, append_transaction, build_activity, monthly_assets, read_transactions

ROOT = Path(__file__).resolve().parents[1]


def point(day, value):
    return dict(date=day, tracked_total_myr=value, cash_total_myr=value, stocks_total_myr=0)


def event(**overrides):
    return Transaction.model_validate(dict(id="sample-rent", recorded_on="2026-11-07", kind="expense", amount=100, currency="MYR", account="sample_bank", description="Sample expense", **overrides))


class ActivityTests(unittest.TestCase):
    def test_months_sort_use_last_snapshot_and_cross_year(self):
        rows = monthly_assets([point("2027-01-12", 1200), point("2026-12-31", 1000), point("2027-01-02", 1100)])
        self.assertIsNone(rows[0].change)
        self.assertEqual(rows[1].change, 200)
        self.assertEqual(rows[1].changePct, 20)

    def test_missing_month_and_zero_baselines_are_unknown(self):
        rows = monthly_assets([point("2026-08-31", 0), point("2026-09-30", 100), point("2026-10-04", 75), point("2026-12-31", 200)])
        self.assertEqual(rows[1].change, 100)
        self.assertIsNone(rows[1].changePct)
        self.assertEqual(rows[2].changePct, -25)
        self.assertIsNone(rows[3].change)
        self.assertEqual(monthly_assets([]), [])

    def test_idempotent_append_conflict_and_malformed_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "transactions.jsonl"
            self.assertTrue(append_transaction(event(), path))
            self.assertFalse(append_transaction(event(), path))
            original = path.read_text()
            changed = event().model_copy(update={"amount": 200})
            with self.assertRaises(ValueError):
                append_transaction(changed, path)
            self.assertEqual(path.read_text(), original)
            self.assertIsNone(read_transactions(path)[0].occurred_on)
            path.write_text(original + "invalid-json\n")
            with self.assertRaises(ValueError):
                build_activity([], date(2026, 11, 7), path)
            with self.assertRaises(ValueError):
                append_transaction(event(), path)

    def test_journal_missing_and_current_month_are_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = build_activity([point("2026-09-30", 100)], date(2026, 11, 7), Path(tmp) / "absent")
            self.assertEqual(report.journal_state, "missing")
            self.assertIsNone(report.current_month)
            self.assertEqual(report.transactions, [])

    def test_validation_rejects_bad_trade_transfer_and_amounts(self):
        for changes in ({"amount": -1}, {"amount": 0}, {"amount": float("nan")}, {"currency": "EUR"}, {"kind": "buy"}, {"kind": "transfer"}, {"counter_account": "sample_bank"}, {"unexpected": 1}, {"occurred_on": "2026-11-08"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                Transaction.model_validate(event().model_dump() | changes)
        for changes in ({"kind": "buy", "symbol": "SAMPLE", "quantity": 2}, {"kind": "transfer", "counter_account": "other"}):
            Transaction.model_validate(event().model_dump() | changes)

    def test_catalog_fixture_has_correct_python_projection(self):
        fixture = json.loads((ROOT / "web/app/design-system/finance-activity.fixture.json").read_text())
        report = ActivityReport.model_validate(fixture)
        self.assertEqual([m.model_dump(mode="json") for m in monthly_assets(fixture["points"])], fixture["months"])
        self.assertEqual(report.current_month, report.months[-1])

    def test_generated_activity_contract_is_current(self):
        result = subprocess.run([sys.executable, str(ROOT / "scripts/export_finance_activity_schema.py"), "--check"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
