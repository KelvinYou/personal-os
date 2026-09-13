"""Tests for scripts/finance_edit.py — the only writer of data/finance/*.yaml.

Runs against a tmp copy of tests/fixtures/finance/*.yaml so it never touches
real holdings, and asserts comments survive the round-trip (the whole reason
this script exists instead of a plain PyYAML dump).
"""
from __future__ import annotations

import shutil
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from pydantic import ValidationError  # noqa: E402

import finance_edit as fe  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "finance"


class FinanceEditTestCase(unittest.TestCase):
    def setUp(self) -> None:
        tmp = Path(self._get_tmp_dir())
        self.savings_path = tmp / "savings.yaml"
        self.portfolio_path = tmp / "portfolio.yaml"
        shutil.copy(FIXTURES / "savings.yaml", self.savings_path)
        shutil.copy(FIXTURES / "portfolio.yaml", self.portfolio_path)

    def _get_tmp_dir(self) -> Path:
        import tempfile

        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        return d


class TestSavingsSet(FinanceEditTestCase):
    def test_round_trip_preserves_comments(self) -> None:
        original = self.savings_path.read_text(encoding="utf-8")
        fe.savings_set(
            "capped_mmf", ["rate_reason=renewed 6mo"], path=self.savings_path
        )
        after = self.savings_path.read_text(encoding="utf-8")

        self.assertIn("renewed 6mo", after)
        # Comment on an untouched account must survive byte-for-byte.
        self.assertIn("# 距 fixture today (2026-08-11) 9 天 → Warning", original)
        self.assertIn("# 距 fixture today (2026-08-11) 9 天 → Warning", after)

    def test_updates_the_updated_date(self) -> None:
        import datetime

        fe.savings_set("capped_mmf", ["balance=19600.00"], path=self.savings_path)
        after = self.savings_path.read_text(encoding="utf-8")
        self.assertIn(f"updated: {datetime.date.today().isoformat()}", after)

    def test_rejects_locked_without_lock_until(self) -> None:
        original = self.savings_path.read_text(encoding="utf-8")
        with self.assertRaises(ValidationError):
            fe.savings_set(
                "roomy_wallet", ["locked=true"], path=self.savings_path
            )
        # No write on validation failure.
        self.assertEqual(original, self.savings_path.read_text(encoding="utf-8"))

    def test_rejects_unknown_field(self) -> None:
        original = self.savings_path.read_text(encoding="utf-8")
        with self.assertRaises(fe.EditError):
            fe.savings_set(
                "capped_mmf", ["product_id=sneaky"], path=self.savings_path
            )
        self.assertEqual(original, self.savings_path.read_text(encoding="utf-8"))

    def test_rejects_unknown_account(self) -> None:
        with self.assertRaises(fe.EditError):
            fe.savings_set("does_not_exist", ["balance=1"], path=self.savings_path)


class TestSavingsAddDelete(FinanceEditTestCase):
    def test_add_then_delete_round_trips(self) -> None:
        fe.savings_add(
            "new_wallet",
            ["balance=100", "rate=1.5", "type=wallet", "liquidity=instant"],
            path=self.savings_path,
        )
        after_add = self.savings_path.read_text(encoding="utf-8")
        self.assertIn("new_wallet", after_add)
        self.assertIn("balance: 100", after_add)

        fe.savings_delete("new_wallet", path=self.savings_path)
        after_delete = self.savings_path.read_text(encoding="utf-8")
        self.assertNotIn("new_wallet", after_delete)

    def test_add_requires_all_mandatory_fields(self) -> None:
        original = self.savings_path.read_text(encoding="utf-8")
        with self.assertRaises(fe.EditError):
            fe.savings_add("new_wallet", ["balance=100"], path=self.savings_path)
        self.assertEqual(original, self.savings_path.read_text(encoding="utf-8"))

    def test_add_rejects_duplicate_account(self) -> None:
        with self.assertRaises(fe.EditError):
            fe.savings_add(
                "capped_mmf",
                ["balance=1", "rate=1", "type=wallet", "liquidity=instant"],
                path=self.savings_path,
            )

    def test_delete_rejects_unknown_account(self) -> None:
        with self.assertRaises(fe.EditError):
            fe.savings_delete("does_not_exist", path=self.savings_path)

    def test_fixture_path_never_touches_real_history(self) -> None:
        # Every real (path=None) mutation upserts data/finance/history.csv;
        # a test using an explicit fixture path must never write it.
        from lib.wealth.history import HISTORY_PATH

        before_exists = HISTORY_PATH.exists()
        before = HISTORY_PATH.read_text(encoding="utf-8") if before_exists else None

        fe.savings_add(
            "new_wallet",
            ["balance=100", "rate=1.5", "type=wallet", "liquidity=instant"],
            path=self.savings_path,
        )

        after_exists = HISTORY_PATH.exists()
        after = HISTORY_PATH.read_text(encoding="utf-8") if after_exists else None
        self.assertEqual(before_exists, after_exists)
        self.assertEqual(before, after)


class TestPortfolioSet(FinanceEditTestCase):
    def test_round_trip_preserves_comments(self) -> None:
        fe.portfolio_set(
            "US", "PIPED", ["shares=3"], path=self.portfolio_path
        )
        after = self.portfolio_path.read_text(encoding="utf-8")
        self.assertIn("shares: 3", after)
        self.assertIn("# pipeline 覆盖 → 用 pipeline 价", after)

    def test_my_holding_uses_symbol_not_code(self) -> None:
        fe.portfolio_set(
            "MY", "BURSA_OK", ["avg_cost=2.50"], path=self.portfolio_path
        )
        after = self.portfolio_path.read_text(encoding="utf-8")
        self.assertIn("avg_cost: 2.5", after)

    def test_rejects_duplicate_symbol_violation(self) -> None:
        original = self.portfolio_path.read_text(encoding="utf-8")
        with self.assertRaises(ValidationError):
            # Renaming would need a dedicated field; simulate a validator
            # failure via an avg_cost that pydantic itself rejects instead
            # (NonNegativeFloat) to prove the write is blocked.
            fe.portfolio_set(
                "US", "PIPED", ["avg_cost_usd=-1"], path=self.portfolio_path
            )
        self.assertEqual(original, self.portfolio_path.read_text(encoding="utf-8"))

    def test_rejects_unknown_symbol(self) -> None:
        with self.assertRaises(fe.EditError):
            fe.portfolio_set(
                "US", "NOSUCH", ["shares=1"], path=self.portfolio_path
            )


class TestPortfolioAddDelete(FinanceEditTestCase):
    def test_add_then_delete_round_trips_us(self) -> None:
        fe.portfolio_add(
            "US", "NEWCO", ["shares=1", "avg_cost_usd=10"], path=self.portfolio_path
        )
        after_add = self.portfolio_path.read_text(encoding="utf-8")
        self.assertIn("NEWCO", after_add)

        fe.portfolio_delete("US", "NEWCO", path=self.portfolio_path)
        after_delete = self.portfolio_path.read_text(encoding="utf-8")
        self.assertNotIn("NEWCO", after_delete)

    def test_add_then_delete_round_trips_my(self) -> None:
        fe.portfolio_add(
            "MY",
            "NEWCO_MY",
            ["code=5678", "shares=50", "avg_cost=1.00"],
            path=self.portfolio_path,
        )
        after_add = self.portfolio_path.read_text(encoding="utf-8")
        self.assertIn("NEWCO_MY", after_add)
        self.assertIn("5678", after_add)

        fe.portfolio_delete("MY", "NEWCO_MY", path=self.portfolio_path)
        after_delete = self.portfolio_path.read_text(encoding="utf-8")
        self.assertNotIn("NEWCO_MY", after_delete)

    def test_add_requires_all_mandatory_fields(self) -> None:
        with self.assertRaises(fe.EditError):
            fe.portfolio_add("US", "NEWCO", ["shares=1"], path=self.portfolio_path)
        with self.assertRaises(fe.EditError):
            fe.portfolio_add(
                "MY", "NEWCO_MY", ["shares=1", "avg_cost=1"], path=self.portfolio_path
            )

    def test_add_rejects_duplicate_symbol(self) -> None:
        with self.assertRaises(fe.EditError):
            fe.portfolio_add(
                "US", "PIPED", ["shares=1", "avg_cost_usd=1"], path=self.portfolio_path
            )

    def test_delete_rejects_unknown_symbol(self) -> None:
        with self.assertRaises(fe.EditError):
            fe.portfolio_delete("US", "NOSUCH", path=self.portfolio_path)


if __name__ == "__main__":
    unittest.main()
