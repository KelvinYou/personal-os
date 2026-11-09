"""Finance manager research: buy-vs-rent projection, proposal contract and review ledger.

Synthetic inputs only; never reads private finance files.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.wealth.research import (  # noqa: E402
    Proposal, PurchaseRules, RentVsBuyInputs, ResearchError, Tier, append_review, fingerprint,
    load_rules, project, read_snapshot, sliced, upfront_costs,
)

FIXTURE = ROOT / "tests" / "fixtures" / "finance_research" / "kl-buy-vs-rent-demo.yaml"
RULES = PurchaseRules.model_validate({
    "transfer_stamp_tiers": [{"up_to": 100000, "rate": 0.01}, {"up_to": 500000, "rate": 0.02}, {"up_to": 1000000, "rate": 0.03}, {"up_to": None, "rate": 0.04}],
    "loan_stamp_rate": 0.005,
    "legal_fee_tiers": [{"up_to": 500000, "rate": 0.0125}, {"up_to": None, "rate": 0.01}],
    "legal_fee_tax_rate": 0.08,
    "first_home_exemption_cap": 500000,
    "rpgt_by_holding_year": [0.3, 0.3, 0.3, 0.2, 0.15],
    "sources": [{"label": "synthetic", "url": "https://example.com", "verified_at": "2026-11-09"}],
    "verified_at": "2026-11-09", "fresh_days": 180,
})


def inputs(**changes) -> RentVsBuyInputs:
    base = yaml.safe_load(FIXTURE.read_text())["inputs"]
    return RentVsBuyInputs.model_validate({**base, **changes})


def run(*args: str, stdin: str = "") -> dict:
    out = subprocess.run([sys.executable, str(ROOT / "scripts" / "finance_research.py"), *args], input=stdin, capture_output=True, text=True, cwd=ROOT)
    return json.loads(out.stdout)


class ProjectionTest(unittest.TestCase):
    def test_tiers_slice_each_band_once(self):
        tiers = [Tier(up_to=100000, rate=0.01), Tier(up_to=500000, rate=0.02), Tier(up_to=None, rate=0.03)]
        self.assertAlmostEqual(sliced(50000, tiers), 500)
        self.assertAlmostEqual(sliced(600000, tiers), 1000 + 8000 + 3000)

    def test_first_home_exemption_only_under_cap(self):
        self.assertEqual(upfront_costs(inputs(property_price=480000, first_home_exemption=True), RULES).transfer_stamp_duty, 0)
        over = upfront_costs(inputs(property_price=520000, first_home_exemption=True), RULES)
        self.assertAlmostEqual(over.transfer_stamp_duty, 1000 + 8000 + 600)
        self.assertAlmostEqual(over.loan_stamp_duty, over.loan * 0.005)

    def test_year_zero_gap_is_the_cost_of_buying_and_selling(self):
        i = inputs()
        result = project(i, RULES)
        first = result.scenarios[result.base_index].rows[0]
        self.assertAlmostEqual(first.rent_net_worth, result.upfront.total)
        self.assertAlmostEqual(first.gap, -(result.upfront.total - result.upfront.down_payment) - i.property_price * i.selling_cost_rate, places=4)

    def test_loan_is_repaid_at_tenure_and_instalments_stop(self):
        result = project(inputs(horizon_years=20, loan_tenure_years=10), RULES)
        rows = result.scenarios[result.base_index].rows
        self.assertLess(rows[10].loan_balance, 1)
        self.assertLess(rows[11].owner_monthly_cost, rows[10].owner_monthly_cost - result.upfront.monthly_instalment * 0.9)

    def test_gap_moves_with_property_growth_and_etf_return(self):
        gaps = [s.final_gap for s in project(inputs(), RULES).scenarios]
        # Row-major growth × ETF: more growth helps buying, more ETF return helps renting.
        for e in range(3):
            self.assertLess(gaps[e], gaps[3 + e])
            self.assertLess(gaps[3 + e], gaps[6 + e])
        for g in range(3):
            self.assertGreater(gaps[g * 3], gaps[g * 3 + 1])
            self.assertGreater(gaps[g * 3 + 1], gaps[g * 3 + 2])

    def test_breakeven_growth_ties_the_paths(self):
        result = project(inputs(), RULES)
        self.assertIsNotNone(result.breakeven_property_growth)
        g = result.breakeven_property_growth
        tied = project(inputs(property_growth={"low": g, "base": g, "high": g}), RULES)
        # Rounded to 0.001 percentage points: within 0.1% of the price is a tie.
        self.assertLess(abs(tied.scenarios[4].final_gap), 500)

    def test_cheaper_path_invests_the_difference(self):
        rows = project(inputs(), RULES).scenarios[4].rows
        self.assertGreater(rows[5].rent_net_worth, rows[0].rent_net_worth)
        self.assertTrue(all(r.buyer_portfolio >= 0 for r in rows))


class ProposalTest(unittest.TestCase):
    def test_rejects_notes_for_unknown_inputs(self):
        raw = yaml.safe_load(FIXTURE.read_text())
        raw["input_notes"]["salary"] = "not an input"
        with self.assertRaises(ValueError):
            Proposal.model_validate(raw)

    def test_fixture_recommendation_matches_its_inputs(self):
        proposal = Proposal.model_validate(yaml.safe_load(FIXTURE.read_text()))
        self.assertEqual(proposal.recommendation.written_for, fingerprint(proposal.inputs))

    def test_review_is_append_only_and_bound_to_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "p.yaml").write_text(FIXTURE.read_text())
            (root / "broken.yaml").write_text("schema_version: 1\n")
            snap = read_snapshot(root, date(2026, 11, 9), RULES, "private")
            self.assertEqual(snap.invalid_files, ["broken.yaml"])
            view = snap.proposals[0]
            self.assertEqual(view.status, "ready_for_review")
            with self.assertRaises(ResearchError) as stale:
                append_review(root, view.proposal.id, "accepted", "", "0" * 16, snap.proposals)
            self.assertEqual(stale.exception.status, 409)
            append_review(root, view.proposal.id, "revise", "Use RM450k", view.result.inputs_fingerprint, snap.proposals)
            after = read_snapshot(root, date(2026, 11, 9), RULES, "private").proposals[0]
            self.assertEqual((after.status, after.reviews[-1].note), ("revise", "Use RM450k"))
            self.assertEqual(len((root / "reviews.jsonl").read_text().splitlines()), 1)

    def test_public_rules_load_and_carry_sources(self):
        rules = load_rules()
        self.assertTrue(rules.sources)
        self.assertTrue(all(s.url.startswith("https://") for s in rules.sources))


class CliTest(unittest.TestCase):
    def test_demo_reads_whatifs_and_refuses_reviews(self):
        snap = run("read", "--demo")
        self.assertEqual(snap["source"], "demo")
        pid = snap["proposals"][0]["proposal"]["id"]
        cheaper = run("apply", "--demo", stdin=json.dumps({"op": "whatif", "id": pid, "inputs": {"property_price": 400000}}))
        self.assertLess(cheaper["upfront"]["loan"], snap["proposals"][0]["result"]["upfront"]["loan"])
        refused = run("apply", "--demo", stdin=json.dumps({"op": "review", "id": pid, "decision": "accepted", "note": "", "written_for": "0" * 16}))
        self.assertEqual(refused["error"]["code"], "review_needs_private_data")

    def test_generated_web_contract_is_current(self):
        result = subprocess.run([sys.executable, str(ROOT / "scripts/export_finance_research_schema.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_validate_reports_fingerprint(self):
        result = run("validate", str(FIXTURE))
        self.assertTrue(result["ok"] and result["recommendation_matches_inputs"])


if __name__ == "__main__":
    unittest.main()
