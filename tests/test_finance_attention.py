"""Finance attention list (scripts/lib/wealth/attention.py) and its phone push.

Synthetic fixtures only: the contract report from test_report_contract, temp state
files and a mocked deliver. No network, no real private data.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
from lib.office.push import MESSAGES  # noqa: E402
from lib.schema import OfficePushCfg  # noqa: E402
from lib.wealth.attention import attention_items  # noqa: E402
from lib.wealth.report_models import WealthReport  # noqa: E402
from test_report_contract import contract_report  # noqa: E402


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


finance_push = load("finance_push", ROOT / "scripts" / "finance_push.py")
office_signal = load("office_signal_fa", ROOT / "scripts" / "office_signal.py")
CFG = OfficePushCfg(enabled=True, topic="pos-test-topic-0123456789abcdef")


class AttentionTests(unittest.TestCase):
    def setUp(self):
        self.report = WealthReport.model_validate(contract_report())

    def test_ranked_amount_free_and_matching_the_report(self):
        items = self.report.attention
        self.assertEqual([i.severity for i in items], sorted((i.severity for i in items), key={"Critical": 0, "Warning": 1, "OK": 2}.get))
        self.assertEqual({i.kind for i in items}, {"maturity", "debt_principal_missing", "deposit_cap", "valuation"})
        text = json.dumps([i.model_dump(mode="json") for i in items])
        for amount in (self.report.tracked_total_myr, self.report.cash.total_cash):
            self.assertNotIn(f"{amount:,.2f}", text); self.assertNotIn(str(amount), text)
        self.assertEqual(items, attention_items(self.report), "attention must be a pure function of the finished report")

    def test_wording_handles_past_and_singular(self):
        maturity = next(i for i in self.report.attention if i.kind == "maturity")
        self.assertRegex(maturity.title, r"^Matured \d+ days ago$")
        debt = next(i for i in self.report.attention if i.kind == "debt_principal_missing")
        self.assertTrue(debt.title.startswith("1 of 2 liabilities has "))

    def test_cap_below_threshold_is_not_listed(self):
        cfg = self.report.thresholds.model_copy(update={"cap_utilization_warn": 0.999})
        relaxed = self.report.model_copy(update={"thresholds": cfg})
        self.assertFalse([i for i in attention_items(relaxed) if i.kind == "deposit_cap"])

    def test_clean_report_has_no_items(self):
        clean = self.report.model_copy(update={
            "maturity": [], "caps": [], "stale_files": [], "catalog_conflicts": [],
            "cash": self.report.cash.model_copy(update={"accounts": [a.model_copy(update={"rate_unverified": False}) for a in self.report.cash.accounts]}),
            "stocks": self.report.stocks.model_copy(update={"stale_prices": []}),
            "fx": self.report.fx.model_copy(update={"stale": False}),
            "allocation": self.report.allocation.model_copy(update={"incomplete": False}),
            "liabilities": self.report.liabilities.model_copy(update={"stale_balance_keys": [], "accounts": [a for a in self.report.liabilities.accounts if a.outstanding_myr is not None]}),
            "wealth_rules": self.report.wealth_rules.model_copy(update={"stale": False}),
        })
        self.assertEqual(attention_items(clean), [])


class FinancePushTests(unittest.TestCase):
    def run_push(self, report: dict, state: Path, cfg=CFG):
        office = mock.Mock(push=cfg)
        with mock.patch.object(finance_push, "STATE", state), mock.patch.object(finance_push, "build", return_value=report), \
             mock.patch("lib.config.load_thresholds", return_value=mock.Mock(office=office)), \
             mock.patch("lib.office.push.deliver") as deliver:
            self.assertEqual(finance_push.main([]), 0)
        return deliver

    def test_each_open_item_pushes_once_and_returns_after_resolving(self):
        report = contract_report()
        with TemporaryDirectory() as tmp:
            state = Path(tmp) / "runtime" / "finance-push.json"
            self.run_push(report, state).assert_called_once_with(CFG, "finance_attention")
            self.run_push(report, state).assert_not_called()
            resolved = {**report, "attention": [i for i in report["attention"] if i["kind"] != "deposit_cap"]}
            self.run_push(resolved, state).assert_not_called()
            self.run_push(report, state).assert_called_once()  # the cap item came back

    def test_disabled_switches_never_push(self):
        with TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            self.run_push(contract_report(), state, CFG.model_copy(update={"finance_attention": False})).assert_not_called()
            self.run_push(contract_report(), Path(tmp) / "t.json", CFG.model_copy(update={"enabled": False})).assert_not_called()

    def test_pushed_text_is_fixed(self):
        title, body, _ = MESSAGES["finance_attention"]
        self.assertNotRegex(title + body, r"\d")

    def test_session_start_starts_the_finance_worker_only_with_finance_data(self):
        with TemporaryDirectory() as tmp, mock.patch.object(office_signal, "ROOT", Path(tmp)), \
             mock.patch("lib.office.signals.record"), mock.patch.object(office_signal, "spawn_finance") as spawn:
            (Path(tmp) / "data").mkdir()
            office_signal.hook(json.dumps({"hook_event_name": "SessionStart", "session_id": "s"}))
            spawn.assert_not_called()
            (Path(tmp) / "data" / "finance").mkdir()
            office_signal.hook(json.dumps({"hook_event_name": "SessionStart", "session_id": "s"}))
            spawn.assert_called_once()


if __name__ == "__main__": unittest.main()
