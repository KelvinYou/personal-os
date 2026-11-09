"""Synthetic funding workflow acceptance; never access private finance files."""
import tempfile
import unittest
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from scripts.lib.wealth.workbench import apply_command, read_workflows
from scripts.lib.wealth.activity import Transaction


class WorkbenchTests(unittest.TestCase):
    def test_invalid_source_journal_is_an_unavailable_source_not_an_empty_board(self):
        from scripts.finance_workbench import snapshot
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / "transactions.jsonl").write_text("broken\n")
            with self.assertRaisesRegex(ValueError, "source_evidence_unavailable"):
                snapshot(directory, datetime(2026, 11, 8, tzinfo=timezone.utc))
            self.assertFalse((directory / "workbench.jsonl").exists())

    def test_concurrent_revisions_and_completed_flow_are_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "workbench.jsonl"
            apply_command({"action": "create_flow", "id": "flow", "request_id": "start", "title": "Synthetic flow"}, path=path, transactions=[])
            def write(index):
                try:
                    return apply_command({"action": "update_step", "id": "flow", "request_id": f"concurrent-{index}", "expected_revision": 1, "step_id": "redeem", "status": "not_applicable", "evidence": "No redemption used in this funding route"}, path=path, transactions=[]).revision
                except ValueError as exc:
                    return str(exc)
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(write, [1, 2]))
            self.assertCountEqual(results, [2, "revision_conflict"])
            for index, step in enumerate(["settle", "fx", "transfer", "purchase", "reconcile"]):
                current = read_workflows(path)[0]
                result = apply_command({"action": "update_step", "id": "flow", "request_id": f"skip-{step}", "expected_revision": current.revision, "step_id": step, "status": "not_applicable", "evidence": "Explicitly excluded in this synthetic case"}, path=path, transactions=[])
            self.assertEqual(result.status, "completed")
            self.assertEqual(len(path.read_text().splitlines()), 7)

    def test_policy_validation_missing_inputs_and_stress_cases(self):
        from scripts.lib.wealth.workbench_planning import audit_policy, ScenarioInput, compare
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "policy.yaml"
            self.assertEqual(audit_policy(path).state, "missing")
            path.write_text('{"schema_version":1,"equity_sleeve":{"core_target_pct":70,"satellite_target_pct":40}}')
            self.assertEqual(audit_policy(path).state, "invalid")
            path.write_text('{"schema_version":1}')
            self.assertIn("allocation.equity_target_pct_of_tracked_investable_assets", audit_policy(path).missing_keys)
        raw = {"as_of": "2026-01-01", "assumptions_confirmed": True, "starting_cash_myr": 100, "monthly_income_myr": 0, "monthly_expenses_myr": 70, "protected_buffer_myr": 50, "one_off_cost_myr": 0, "extra_monthly_expense_myr": 0, "income_pause_months": 0, "horizon_months": 2}
        result = compare(ScenarioInput.model_validate(raw))
        self.assertEqual(result.first_buffer_breach_month, 1)
        self.assertEqual(result.minimum_alternative_myr, -40)
        for override in ({"monthly_income_myr": float("nan")}, {"starting_cash_myr": -1}, {"assumptions_confirmed": False}, {"monthly_expenses_myr": None}, {"horizon_months": True}, {"monthly_expenses_myr": 0.001}):
            with self.assertRaises(ValueError):
                ScenarioInput.model_validate(raw | override)

    def test_demo_cli_replays_saved_commands_without_private_files(self):
        root = Path(__file__).resolve().parents[1]
        command = {"action": "save_scenario", "id": "scenario", "request_id": "scenario-create", "title": "Synthetic stress test", "inputs": {"as_of": "2026-01-01", "assumptions_confirmed": True, "starting_cash_myr": 10000, "monthly_income_myr": 4000, "monthly_expenses_myr": 3000, "protected_buffer_myr": 3000, "one_off_cost_myr": 2000, "extra_monthly_expense_myr": 500, "income_pause_months": 1, "horizon_months": 3}}
        def run(payload):
            response = subprocess.run([sys.executable, str(root / "scripts/finance_workbench.py"), "apply", "--demo"], input=json.dumps(payload), text=True, capture_output=True)
            self.assertEqual(response.returncode, 0, response.stdout)
            return json.loads(response.stdout)
        first = run({"history": [], "command": command})
        second = run({"history": [command]})
        self.assertEqual(first["workflows"][-1]["result"], second["workflows"][-1]["result"])
        self.assertEqual(second["workflows"][-1]["result"]["alternative_end_myr"], 5500)

    def test_generated_contract_is_current(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run([sys.executable, str(root / "scripts/export_finance_workbench_schema.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_saved_worksheets_survive_reload_and_policy_changes_block_old_acceptance(self):
        policy = {"emergency_fund": {"target_months": 3, "monthly_required_expenses": 1000}}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "workbench.jsonl"
            command = {"action": "save_allocation", "id": "monthly", "request_id": "save", "title": "Monthly plan", "inputs": {"as_of": "2026-11-08", "assumptions_confirmed": True, "available_after_bills_myr": 2000, "near_term_need_myr": 300, "protected_reserve_myr": 2000}}
            result = apply_command(command, path=path, transactions=[], policy=policy)
            self.assertEqual(result.status, "draft")
            self.assertEqual(result.result.unassigned_myr, 700)
            review = {"action": "review", "id": "monthly", "request_id": "review", "expected_revision": 1}
            with self.assertRaisesRegex(ValueError, "policy_changed"):
                apply_command(review, path=path, transactions=[], policy={"emergency_fund": {"target_months": 6, "monthly_required_expenses": 1000}})
            reviewed = apply_command(review, path=path, transactions=[], policy=policy)
            self.assertEqual(reviewed.status, "reviewed")
            self.assertEqual(read_workflows(path)[0], reviewed)
            path.write_text(path.read_text() + "broken\n")
            with self.assertRaisesRegex(ValueError, "invalid_workbench_ledger"):
                apply_command(review, path=path, transactions=[], policy=policy)

    def test_policy_gaps_stay_unknown_and_cash_examples_have_independent_results(self):
        from scripts.lib.wealth.workbench_planning import Policy, AllocationInput, ScenarioInput, allocate, compare
        policy = Policy.model_validate({"schema_version": 1, "base_currency": "MYR", "emergency_fund": {"target_months": 3, "monthly_required_expenses": 1000}})
        allocation = allocate(AllocationInput.model_validate({"as_of": "2026-11-08", "assumptions_confirmed": True, "available_after_bills_myr": 2000, "near_term_need_myr": 300, "protected_reserve_myr": 2000}), policy)
        self.assertEqual(allocation.emergency_target_myr, 3000)
        self.assertEqual(allocation.near_term_allocation_myr, 300)
        self.assertEqual(allocation.emergency_allocation_myr, 1000)
        self.assertEqual(allocation.unassigned_myr, 700)
        self.assertIsNone(policy.allocation.equity_target_pct_of_tracked_investable_assets)
        with self.assertRaises(ValueError):
            allocate(AllocationInput.model_validate({"as_of": "2026-11-08", "assumptions_confirmed": True, "available_after_bills_myr": 2000, "near_term_need_myr": 0, "protected_reserve_myr": 0}), Policy())
        scenario = compare(ScenarioInput.model_validate({"as_of": "2026-11-08", "assumptions_confirmed": True, "starting_cash_myr": 10000, "monthly_income_myr": 4000, "monthly_expenses_myr": 3000, "protected_buffer_myr": 3000, "one_off_cost_myr": 2000, "extra_monthly_expense_myr": 500, "income_pause_months": 1, "horizon_months": 3}))
        self.assertEqual([row.baseline_myr for row in scenario.months], [10000, 11000, 12000, 13000])
        self.assertEqual([row.alternative_myr for row in scenario.months], [10000, 4500, 5000, 5500])
        self.assertEqual(scenario.end_difference_myr, -7500)
        self.assertIsNone(scenario.first_buffer_breach_month)

    def test_create_reload_and_idempotent_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "workbench.jsonl"
            command = {"action": "create_flow", "request_id": "sample-create", "id": "sample-flow", "title": "Sample funding"}
            first = apply_command(command, path=path, transactions=[])
            self.assertEqual(first.id, "sample-flow")
            self.assertEqual(first.revision, 1)
            self.assertEqual([s.status for s in first.steps], ["planned"] * 6)
            self.assertEqual(read_workflows(path), [first])
            self.assertEqual(apply_command(command, path=path, transactions=[]), first)
            self.assertEqual(len(path.read_text().splitlines()), 1)

    def test_purchase_does_not_confirm_funding_and_updates_require_evidence_and_revision(self):
        transaction = Transaction.model_validate({"id": "sample-buy", "recorded_on": "2026-11-07", "kind": "buy", "amount": 100, "currency": "USD", "account": "sample-broker", "description": "Synthetic purchase", "symbol": "SAMPLE", "quantity": 1})
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "workbench.jsonl"
            apply = lambda command: apply_command(command, path=path, transactions=[transaction])
            flow = apply({"action": "create_flow", "request_id": "create", "id": "flow", "title": "Sample funding", "source_event_id": "sample-buy"})
            self.assertEqual(flow.steps[4].status, "confirmed")
            self.assertIsNone(flow.steps[4].occurred_on)
            self.assertEqual([s.status for s in flow.steps[:4]], ["planned"] * 4)
            change = {"action": "update_step", "request_id": "change", "id": "flow", "expected_revision": 1, "step_id": "redeem", "status": "in_transit", "amount": 200, "currency": "MYR", "evidence": "Redemption submitted; receipt sample-001"}
            updated = apply(change)
            self.assertEqual(updated.revision, 2)
            self.assertEqual(updated.steps[0].status, "in_transit")
            self.assertEqual(apply(change), updated)
            with self.assertRaisesRegex(ValueError, "revision_conflict"):
                apply(change | {"request_id": "stale"})
            with self.assertRaisesRegex(ValueError, "request_id_conflict"):
                apply(change | {"amount": 201})
            with self.assertRaises(ValueError):
                apply(change | {"request_id": "bad", "expected_revision": 2, "evidence": ""})
            self.assertEqual(read_workflows(path)[0], updated)


if __name__ == "__main__":
    unittest.main()
