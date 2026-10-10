"""Balance-sheet acceptance tests using synthetic holdings, never private data."""
import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib.wealth import build_report, load_savings, load_rates, load_portfolio, load_fx
from lib.schema import WealthCfg
from lib.wealth.files import Liability

FIX = ROOT / 'tests/fixtures/finance'

class LiabilityReportTests(unittest.TestCase):
    def report(self, debts):
        savings = load_savings(FIX / 'savings.yaml')
        savings.liabilities = debts
        return build_report(savings, load_rates(FIX / 'interest_rates.yaml'),
                            load_portfolio(FIX / 'portfolio.yaml'), load_fx(FIX / 'fx.yaml'),
                            WealthCfg(), date(2026, 9, 5), ROOT / 'tests/fixtures/stockdata')

    def test_card_debt_is_subtracted_once_and_loan_principal_stays_unknown(self):
        report = self.report({
            'card': Liability(type='credit_card', outstanding=600, as_of=date(2026,9,5)),
            'loan': Liability(type='housing', monthly_now=80, monthly_full=240),
        })
        self.assertEqual(report['liabilities']['known_outstanding_myr'], 600)
        self.assertEqual(report['liabilities']['unknown_balance_keys'], ['loan'])
        self.assertEqual(report['liabilities']['monthly_commitments_myr'], 80)
        self.assertFalse(report['liabilities']['balances_complete'])
        self.assertEqual(report['balance_sheet']['after_known_debt_myr'], report['tracked_total_myr'] - 600)
        self.assertEqual(report['tracked_total_myr'], self.report({})['tracked_total_myr'])

    def test_unknown_debt_is_not_zero_but_explicit_zero_is_known(self):
        unknown = self.report({'card': Liability(type='credit_card')})
        self.assertIsNone(unknown['liabilities']['known_outstanding_myr'])
        self.assertIsNone(unknown['balance_sheet']['after_known_debt_myr'])
        zero = self.report({'card': Liability(type='credit_card', outstanding=0, as_of=date(2026,9,5))})
        self.assertEqual(zero['liabilities']['known_outstanding_myr'], 0)
        self.assertEqual(zero['balance_sheet']['after_known_debt_myr'], zero['tracked_total_myr'])

    def test_old_balance_is_flagged_and_payment_never_implies_principal(self):
        report = self.report({'loan': Liability(type='auto', monthly=90, outstanding=1200, as_of=date(2026,7,1))})
        self.assertEqual(report['liabilities']['stale_balance_keys'], ['loan'])
        self.assertEqual(report['liabilities']['monthly_commitments_myr'], 90)
        self.assertEqual(report['balance_sheet']['after_known_debt_myr'], report['tracked_total_myr']-1200)

    def test_missing_date_and_negative_debt_are_rejected(self):
        from pydantic import ValidationError
        for fields in ({'outstanding': 10}, {'as_of': date(2026,9,5)}, {'outstanding': -10, 'as_of': date(2026,9,5)}):
            with self.assertRaises(ValidationError):
                Liability(type='credit_card', **fields)

    def test_unconverted_cash_is_visible_but_never_in_myr_totals(self):
        from lib.wealth.files import TravelCashFile, load_travel_cash
        import tempfile
        report = self.report({})
        savings = load_savings(FIX / 'savings.yaml')
        travel = TravelCashFile(updated=date(2026,9,5), currency='CNY', purpose='Test journey', accounts={'wallet': {'balance': 100}})
        with_cash = build_report(savings, load_rates(FIX / 'interest_rates.yaml'), load_portfolio(FIX / 'portfolio.yaml'), load_fx(FIX / 'fx.yaml'), WealthCfg(), date(2026,9,5), ROOT / 'tests/fixtures/stockdata', travel_cash=travel)
        self.assertEqual(with_cash['tracked_total_myr'], report['tracked_total_myr'])
        self.assertEqual(with_cash['excluded_cash'][0]['balance'], 100)
        self.assertEqual(with_cash['excluded_cash'][0]['currency'], 'CNY')
        with tempfile.TemporaryDirectory() as folder:
            self.assertIsNone(load_travel_cash(Path(folder) / 'absent.yaml'))

if __name__ == '__main__':
    unittest.main()
