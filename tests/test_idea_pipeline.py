"""Behavioural tests for the startup-idea evaluation pipeline."""
from __future__ import annotations

import asyncio
from contextlib import redirect_stderr
from io import StringIO
import json
import sys
import unittest
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.ideas.models import (  # noqa: E402
    AnalystReport,
    ClaimCandidate,
    Consent,
    ContextField,
    DecisionGoal,
    EvidenceItem,
    EvaluationInput,
    EvidenceStatus,
    GroundingStatus,
    ClaimKind,
    Dispute,
    FormulaOperation,
    FormulaSpec,
    Quantity,
    CostEstimate,
    ImpactIfFalse,
    LedgerState,
    Priority,
    TestProposal,
    LensQuestion,
    LensQuestionStatus,
    ModelProcessing,
    RunBudget,
    TestResultState,
    Unknown,
    UserAssumption,
)
from lib.ideas.registry import register_reports  # noqa: E402
from lib.ideas.ledger import build_ledger  # noqa: E402
from lib.ideas.formulas import FormulaError, evaluate_formula  # noqa: E402
from lib.ideas.storage import IdeaStore, StorageError  # noqa: E402
from lib.ideas.lifecycle import TestLifecycle  # noqa: E402
from lib.ideas.model_client import DemoModelClient, ScriptedModelClient  # noqa: E402
from lib.ideas.config import load_idea_config  # noqa: E402
from lib.ideas.orchestrator import IdeaPipeline  # noqa: E402
from lib.ideas.privacy import prepare_model_input  # noqa: E402
from lib.ideas.validate import validate_context  # noqa: E402
from lib.ideas.validate import ContextValidationError  # noqa: E402
from idea_pipeline import main as idea_cli_main  # noqa: E402


class IdeaContextTests(unittest.TestCase):
    def _input(self) -> EvaluationInput:
        return EvaluationInput(
            idea_id="pdpa-compliance-agent",
            as_of=date(2026, 9, 11),
            scope="Malaysia SMEs processing customer personal data",
            constraints=["Solo founder", "No autonomous legal advice"],
            decision_goal=DecisionGoal(
                question="Which assumption should be tested before building?",
                owner="Kelvin",
                trigger="Before committing to an MVP",
                deadline=date(2026, 9, 30),
            ),
            context_fields=[
                ContextField(
                    context_ref="ctx-problem",
                    field="problem",
                    value="SMEs need help drafting PDPA compliance artifacts.",
                    scope="Malaysia SMEs",
                )
            ],
            user_assumptions=[
                UserAssumption(
                    user_assumption_id="ua-solo-founder",
                    statement="The first version must be operable by one founder.",
                    scope="Founder constraints",
                    recorded_at=date(2026, 9, 11),
                    owner="Kelvin",
                )
            ],
            evidence=[
                EvidenceItem(
                    evidence_id="ev-complyhq-pricing",
                    locator="https://example.test/pricing",
                    publisher_or_source="Example source",
                    observed_or_effective_at=date(2026, 9, 10),
                    retrieved_at=date(2026, 9, 11),
                    scope="Singapore SME compliance software",
                    excerpt_or_observation="A comparable product publishes paid tiers.",
                    freshness_window=30,
                    model_processing="allowed",
                    quality_note="Comparable market, not proof of Malaysian demand.",
                )
            ],
            unknowns=[
                Unknown(
                    unknown_id="unk-urgent-demand",
                    statement="Whether Malaysian SMEs will pay for this workflow.",
                    scope="Target buyer",
                )
            ],
            unknowns_declared=True,
            consent=Consent(
                actor="Kelvin",
                scope="Startup-idea evaluation model processing",
                granted_at=datetime(2026, 9, 11, 1, 0, tzinfo=timezone.utc),
            ),
            run_budget=RunBudget(
                max_model_calls=20,
                max_debate_rounds=1,
                max_retries_per_stage=1,
                max_model_cost=Decimal("2.00"),
                currency="USD",
                max_wall_clock_minutes=10,
                max_user_minutes=60,
            ),
        )

    def test_preflight_assigns_run_identity_and_stable_input_snapshot(self):
        first = validate_context(self._input(), now=datetime(2026, 9, 11, 2, 0, tzinfo=timezone.utc))
        second = validate_context(self._input(), now=datetime(2026, 9, 11, 3, 0, tzinfo=timezone.utc))

        self.assertEqual(first.idea_id, "pdpa-compliance-agent")
        self.assertRegex(first.run_id, r"^run-[0-9a-f]{32}$")
        self.assertEqual(len(first.input_snapshot_id), 64)
        self.assertEqual(first.input_snapshot_id, second.input_snapshot_id)
        self.assertEqual(first.as_of, date(2026, 9, 11))
        self.assertEqual(first.evaluated_at.tzinfo, timezone.utc)

    def test_preflight_uses_kuala_lumpur_calendar_date_at_utc_midnight(self):
        input_ = self._input().model_copy(
            update={
                "consent": self._input().consent.model_copy(
                    update={"granted_at": datetime(2026, 9, 10, 16, tzinfo=timezone.utc)}
                )
            }
        )
        context = validate_context(
            input_,
            now=datetime(2026, 9, 10, 16, 30, tzinfo=timezone.utc),
        )

        self.assertEqual(context.as_of, date(2026, 9, 11))

    def test_registry_marks_model_hypothesis_as_unresolved(self):
        context = validate_context(self._input(), now=datetime(2026, 9, 11, 2, 0, tzinfo=timezone.utc))
        report = AnalystReport(
            run_id=context.run_id,
            schema_version="1",
            producer_id="demand",
            lens_id="demand",
            checklist=[
                LensQuestion(
                    question_id="demand-question",
                    status=LensQuestionStatus.UNKNOWN,
                    unknown_id="unk-urgent-demand",
                )
            ],
            claims=[
                ClaimCandidate(
                    candidate_key="urgent-demand",
                    statement="Customers will urgently pay for this product.",
                    claim_kind=ClaimKind.HYPOTHESIS,
                )
            ],
        )

        result = register_reports(context, [report])

        self.assertEqual(len(result.claims), 1)
        claim = result.claims[0]
        self.assertEqual(claim.evidence_status, EvidenceStatus.MISSING)
        self.assertEqual(claim.grounding_status, GroundingStatus.MODEL_DEPENDENT)
        self.assertEqual(claim.provenance.value, "MODEL-GUESSED")

    def test_preflight_rejects_undeclared_unknowns(self):
        with self.assertRaises(ContextValidationError):
            validate_context(
                self._input().model_copy(update={"unknowns_declared": False}),
                now=datetime(2026, 9, 11, 2, 0, tzinfo=timezone.utc),
            )

    def test_preflight_rejects_historical_as_of_without_replay_reason(self):
        historical = self._input().model_copy(update={"as_of": date(2026, 9, 10)})

        with self.assertRaises(ContextValidationError):
            validate_context(
                historical,
                now=datetime(2026, 9, 11, 2, 0, tzinfo=timezone.utc),
            )

    def _report(self, context, candidates, *, producer_id="demand", gaps=None):
        return AnalystReport(
            run_id=context.run_id,
            schema_version="1",
            producer_id=producer_id,
            lens_id=producer_id,
            checklist=[
                LensQuestion(
                    question_id="demand-question",
                    status=LensQuestionStatus.UNKNOWN,
                    unknown_id="unk-urgent-demand",
                )
            ],
            claims=candidates,
            evidence_gaps=gaps or [],
        )

    def test_registry_marks_stale_evidence_as_unresolved(self):
        input_ = self._input().model_copy(
            update={
                "evidence": [
                    self._input().evidence[0].model_copy(
                        update={
                            "observed_or_effective_at": date(2026, 7, 1),
                            "freshness_window": 7,
                        }
                    )
                ]
            }
        )
        context = validate_context(input_, now=datetime(2026, 9, 11, 2, 0, tzinfo=timezone.utc))
        report = self._report(
            context,
            [
                ClaimCandidate(
                    candidate_key="old-market-signal",
                    statement="The comparable product has paid tiers.",
                    evidence_refs=["ev-complyhq-pricing"],
                    claim_kind=ClaimKind.FACT,
                )
            ],
        )

        result = register_reports(context, [report])

        self.assertEqual(result.claims[0].evidence_status, EvidenceStatus.STALE)
        self.assertEqual(result.claims[0].grounding_status, GroundingStatus.UNRESOLVED)

    def test_derived_claim_preserves_assumption_dependency(self):
        context = validate_context(self._input(), now=datetime(2026, 9, 11, 2, 0, tzinfo=timezone.utc))
        report = self._report(
            context,
            [
                ClaimCandidate(
                    candidate_key="price-a",
                    statement="The first workflow costs 10 MYR.",
                    context_refs=["ctx-problem"],
                    quantity=Quantity(scalar=Decimal("10"), unit="MYR", precision=0),
                    claim_kind=ClaimKind.ASSUMPTION,
                ),
                ClaimCandidate(
                    candidate_key="price-b",
                    statement="The second workflow costs 5 MYR.",
                    context_refs=["ctx-problem"],
                    quantity=Quantity(scalar=Decimal("5"), unit="MYR", precision=0),
                    claim_kind=ClaimKind.ASSUMPTION,
                ),
                ClaimCandidate(
                    candidate_key="total-price",
                    statement="The combined workflow costs 15 MYR.",
                    derivation_refs=["demand:price-a", "demand:price-b"],
                    formula=FormulaSpec(
                        operation=FormulaOperation.ADD,
                        operands=["demand:price-a", "demand:price-b"],
                        output_unit="MYR",
                        rounding=0,
                    ),
                    claim_kind=ClaimKind.DERIVED,
                ),
            ],
        )

        result = register_reports(context, [report])
        derived = next(claim for claim in result.claims if claim.candidate_key == "total-price")

        self.assertEqual(derived.provenance.value, "DERIVED")
        self.assertEqual(derived.grounding_status, GroundingStatus.ASSUMPTION_DEPENDENT)
        self.assertEqual(derived.quantity.scalar, Decimal("15"))

    def test_formula_gate_rejects_incompatible_units_and_extra_precision(self):
        with self.assertRaises(FormulaError):
            evaluate_formula(
                FormulaSpec(
                    operation=FormulaOperation.ADD,
                    operands=["a", "b"],
                    output_unit="MYR",
                    rounding=0,
                ),
                {
                    "a": Quantity(scalar=Decimal("1"), unit="MYR", precision=0),
                    "b": Quantity(scalar=Decimal("1"), unit="users", precision=0),
                },
            )
        with self.assertRaises(FormulaError):
            evaluate_formula(
                FormulaSpec(
                    operation=FormulaOperation.ADD,
                    operands=["a", "b"],
                    output_unit="MYR",
                    rounding=2,
                ),
                {
                    "a": Quantity(scalar=Decimal("1"), unit="MYR", precision=0),
                    "b": Quantity(scalar=Decimal("1"), unit="MYR", precision=0),
                },
            )

    def test_registry_rejects_mixed_provenance_basis(self):
        context = validate_context(self._input(), now=datetime(2026, 9, 11, 2, 0, tzinfo=timezone.utc))
        report = self._report(
            context,
            [
                ClaimCandidate(
                    candidate_key="mixed",
                    statement="This claim mixes source types.",
                    evidence_refs=["ev-complyhq-pricing"],
                    context_refs=["ctx-problem"],
                    claim_kind=ClaimKind.FACT,
                )
            ],
        )

        result = register_reports(context, [report])

        self.assertEqual(result.claims, [])
        self.assertTrue(any(error.code == "MIXED_BASIS" for error in result.errors))

    def test_supersedes_claim_must_reference_an_older_run(self):
        context = validate_context(self._input(), now=datetime(2026, 9, 11, 2, 0, tzinfo=timezone.utc))
        report = self._report(
            context,
            [
                ClaimCandidate(
                    candidate_key="new-market-signal",
                    statement="A newer observation exists.",
                    context_refs=["ctx-problem"],
                    claim_kind=ClaimKind.ASSUMPTION,
                    supersedes_claim_id="claim-demand-old-signal",
                )
            ],
        )

        result = register_reports(context, [report])

        self.assertEqual(result.claims, [])
        self.assertTrue(
            any(error.code == "SUPERSEDES_CLAIM_REFERENCE" for error in result.errors)
        )

    def test_registry_rejects_checklist_links_to_unknown_claims(self):
        context = validate_context(self._input(), now=datetime(2026, 9, 11, 2, 0, tzinfo=timezone.utc))
        report = self._report(
            context,
            [],
        ).model_copy(
            update={
                "checklist": [
                    LensQuestion(
                        question_id="demand-question",
                        status=LensQuestionStatus.ADDRESSED,
                        claim_ids=["claim-does-not-exist"],
                    )
                ]
            }
        )

        result = register_reports(context, [report])

        self.assertTrue(any(error.code == "CHECKLIST_CLAIM_REFERENCE" for error in result.errors))

    def test_invalid_checklist_report_is_excluded_before_registry(self):
        input_ = self._input().model_copy(
            update={
                "run_budget": self._input().run_budget.model_copy(
                    update={"max_model_calls": 2}
                )
            }
        )

        def response(stage, payload):
            if stage != "baseline":
                raise AssertionError("research-manager must not run after checklist failure")
            return {
                "checklist": [
                    {
                        "question_id": "unconfigured-question",
                        "status": "UNKNOWN",
                        "unknown_id": "unk-urgent-demand",
                    }
                ],
                "claims": [
                    {
                        "candidate_key": "uncovered-claim",
                        "statement": "This claim must not enter the registry.",
                        "claim_kind": "hypothesis",
                    }
                ],
            }

        with TemporaryDirectory() as tmp:
            store = IdeaStore(Path(tmp))
            store.save_input(input_)
            client = ScriptedModelClient(response)
            artifact = asyncio.run(
                IdeaPipeline(
                    client,
                    mode="single",
                    store=store,
                    lens_checklists={"baseline": ("demand-question",)},
                    now=datetime(2026, 9, 11, 2, 0, tzinfo=timezone.utc),
                ).run(input_)
            )

        self.assertEqual(client.calls, ["baseline"])
        self.assertEqual(artifact.run_status.value, "BLOCKED")
        self.assertEqual(artifact.claims, [])
        self.assertTrue(any(error.code == "CHECKLIST_COVERAGE" for error in artifact.errors))

    def test_typed_dispute_marks_claim_conflicted(self):
        context = validate_context(self._input(), now=datetime(2026, 9, 11, 2, 0, tzinfo=timezone.utc))
        report = self._report(
            context,
            [
                ClaimCandidate(
                    candidate_key="market-signal",
                    statement="The comparable product has paid tiers.",
                    evidence_refs=["ev-complyhq-pricing"],
                    claim_kind=ClaimKind.FACT,
                )
            ],
        )
        dispute = Dispute(
            dispute_id="dispute-pricing",
            claim_refs=["claim-demand-market-signal"],
            evidence_refs=["ev-complyhq-pricing"],
            reason="The source scope may not represent the target market.",
            unknown_refs=["unk-urgent-demand"],
            actor="oppose",
        )

        result = register_reports(context, [report], disputes=[dispute])

        self.assertEqual(result.claims[0].evidence_status, EvidenceStatus.CONFLICTED)
        self.assertEqual(result.claims[0].grounding_status, GroundingStatus.UNRESOLVED)

    def test_ledger_keeps_model_guess_evidence_blocked_and_assigns_stable_test_id(self):
        context = validate_context(self._input(), now=datetime(2026, 9, 11, 2, 0, tzinfo=timezone.utc))
        report = self._report(
            context,
            [
                ClaimCandidate(
                    candidate_key="urgent-demand",
                    statement="Customers will urgently pay for this product.",
                    claim_kind=ClaimKind.HYPOTHESIS,
                )
            ],
        )
        registry = register_reports(context, [report])
        proposal = TestProposal(
            test_key="interview-buyer",
            title="Interview target buyers",
            assumption="Target buyers have urgent demand.",
            claim_ids=["claim-demand-urgent-demand"],
            impact_if_false=ImpactIfFalse.FATAL,
            discriminating_test="Interview five target buyers.",
            criterion="At least three describe a current workaround and agree to a follow-up.",
            target_or_sample="Five Malaysia SMEs in the target segment.",
            owner="Kelvin",
            deadline=date(2026, 9, 20),
            estimated_cost=CostEstimate(amount=Decimal("0"), currency="USD", user_minutes=120),
        )

        first = build_ledger(context, registry, [proposal])
        second = build_ledger(context, registry, [proposal.model_copy()])
        priority_variant = build_ledger(
            context,
            registry,
            [proposal.model_copy(update={"proposed_priority": Priority.P2})],
        )

        row = first.ledger.rows[0]
        self.assertEqual(row.state, LedgerState.EVIDENCE_BLOCKED)
        self.assertEqual(row.grounding_status, GroundingStatus.MODEL_DEPENDENT)
        self.assertEqual(row.priority, Priority.P0)
        self.assertEqual(row.test_id, second.ledger.rows[0].test_id)
        self.assertEqual(row.test_id, priority_variant.ledger.rows[0].test_id)

    def test_ledger_does_not_make_incomplete_test_look_executable(self):
        context = validate_context(self._input(), now=datetime(2026, 9, 11, 2, 0, tzinfo=timezone.utc))
        registry = register_reports(context, [])
        proposal = TestProposal(
            test_key="missing-contract",
            title="Incomplete test",
            assumption="Something important is true.",
            impact_if_false=ImpactIfFalse.FATAL,
        )

        result = build_ledger(context, registry, [proposal])
        self.assertEqual(result.ledger.rows, [])
        row = result.ledger.appendix_rows[0]

        self.assertEqual(row.priority, Priority.UNPRIORITIZED)
        self.assertEqual(row.state, LedgerState.UNPRIORITIZED)
        self.assertIsNone(row.owner)
        self.assertIsNone(row.estimated_cost)

    def test_private_store_round_trips_input_and_appends_test_events(self):
        with TemporaryDirectory() as tmp:
            store = IdeaStore(Path(tmp))
            store.save_input(self._input())
            run_id = "run-" + ("a" * 32)
            with self.assertRaises(StorageError):
                store.append_test_event(
                    "pdpa-compliance-agent",
                    {"event_type": "confirmation", "test_id": "test-example"},
                )
            store.append_test_event(
                "pdpa-compliance-agent",
                {
                    "event_type": "confirmation",
                    "test_id": "test-example",
                    "run_id": run_id,
                    "confirmed_at": "2026-09-11T02:00:00+00:00",
                    "confirmed_by": "Kelvin",
                },
            )
            store.append_test_event(
                "pdpa-compliance-agent",
                {
                    "event_type": "result",
                    "test_id": "test-example",
                    "run_id": run_id,
                    "state": TestResultState.NOT_RUN.value,
                    "recorded_at": "2026-09-11T02:01:00+00:00",
                    "recorded_by": "Kelvin",
                    "observation": "The test was not run.",
                    "result_evidence_refs": [],
                    "actual_cost": None,
                },
            )

            loaded = store.load_input("pdpa-compliance-agent")
            events = (Path(tmp) / "pdpa-compliance-agent" / "tests.md").read_text(
                encoding="utf-8"
            )

        self.assertEqual(loaded.idea_id, "pdpa-compliance-agent")
        self.assertEqual(len(loaded.evidence), 1)
        self.assertEqual(events.count("event_type:"), 2)

    def test_test_lifecycle_requires_confirmation_and_persists_typed_result(self):
        with TemporaryDirectory() as tmp:
            store = IdeaStore(Path(tmp))
            store.save_input(self._input())
            artifact = asyncio.run(
                IdeaPipeline(
                    DemoModelClient(),
                    mode="single",
                    store=store,
                    now=datetime(2026, 9, 11, 2, 0, tzinfo=timezone.utc),
                ).run(self._input())
            )
            test_id = artifact.ledger.rows[0].test_id
            lifecycle = TestLifecycle(store)

            with self.assertRaises(StorageError):
                lifecycle.record_result(
                    idea_id=self._input().idea_id,
                    run_id=artifact.run_id,
                    test_id=test_id,
                    state=TestResultState.VALIDATED,
                    recorded_by="Kelvin",
                    observation="Premature result.",
                    result_evidence_refs=[],
                    recorded_at=datetime(2026, 9, 11, 3, 0, tzinfo=timezone.utc),
                )

            lifecycle.confirm(
                idea_id=self._input().idea_id,
                run_id=artifact.run_id,
                test_id=test_id,
                confirmed_by="Kelvin",
                confirmed_at=datetime(2026, 9, 11, 3, 0, tzinfo=timezone.utc),
            )
            result = lifecycle.record_result(
                idea_id=self._input().idea_id,
                run_id=artifact.run_id,
                test_id=test_id,
                state=TestResultState.VALIDATED,
                recorded_by="Kelvin",
                observation="Three buyers described the same workaround.",
                result_evidence_refs=["ev-complyhq-pricing"],
                recorded_at=datetime(2026, 9, 11, 4, 0, tzinfo=timezone.utc),
            )

            self.assertEqual(result.state, TestResultState.VALIDATED)
            self.assertTrue(store.has_result(self._input().idea_id, artifact.run_id, test_id))

    def test_single_agent_pipeline_produces_durable_complete_run(self):
        input_ = self._input().model_copy(
            update={
                "run_budget": self._input().run_budget.model_copy(
                    update={"max_model_calls": 2}
                )
            }
        )

        def response(stage, payload):
            if stage == "baseline":
                return {
                    "checklist": [
                        {
                            "question_id": "demand-question",
                            "status": "UNKNOWN",
                            "unknown_id": "unk-urgent-demand",
                        }
                    ],
                    "claims": [
                        {
                            "candidate_key": "urgent-demand",
                            "statement": "Customers will urgently pay for this product.",
                            "claim_kind": "hypothesis",
                        }
                    ],
                    "alternatives": [],
                    "evidence_gaps": [],
                    "test_proposals": [],
                }
            claim_id = payload["claims"][0]["claim_id"]
            return {
                "thesis": {
                    "statement": "Demand remains an untested hypothesis.",
                    "claim_refs": [claim_id],
                    "unknown_refs": [],
                },
                "strongest_counterexample": {
                    "statement": "No buyer may pay.",
                    "claim_refs": [claim_id],
                    "unknown_refs": [],
                },
                "invalidation_conditions": [],
                "evidence_gaps": [],
                "alternatives": [],
                "candidate_claim_ids": [claim_id],
                "candidate_gap_ids": [],
                "test_proposals": [
                    {
                        "test_key": "buyer-interviews",
                        "title": "Interview buyers",
                        "assumption": "Target buyers have urgent demand.",
                        "claim_ids": [claim_id],
                        "gap_ids": [],
                        "impact_if_false": "FATAL",
                        "discriminating_test": "Interview five target buyers.",
                        "criterion": "Three describe a current workaround.",
                        "target_or_sample": "Five target SMEs.",
                        "owner": "Kelvin",
                        "deadline": "2026-09-20",
                        "estimated_cost": {
                            "amount": "0",
                            "currency": "USD",
                            "user_minutes": 120,
                        },
                    },
                    {
                        "test_key": "buyer-survey",
                        "title": "Survey target buyers",
                        "assumption": "Target buyers have a painful workaround.",
                        "claim_ids": [claim_id],
                        "gap_ids": [],
                        "impact_if_false": "MAJOR",
                        "discriminating_test": "Survey five target buyers.",
                        "criterion": "Three report a current workaround.",
                        "target_or_sample": "Five target SMEs.",
                        "owner": "Kelvin",
                        "deadline": "2026-09-21",
                        "estimated_cost": {
                            "amount": "0",
                            "currency": "USD",
                            "user_minutes": 30,
                        },
                    }
                ],
            }

        client = ScriptedModelClient(response, cost=Decimal("0.10"))
        with TemporaryDirectory() as tmp:
            store = IdeaStore(Path(tmp))
            store.save_input(input_)
            artifact = asyncio.run(
                IdeaPipeline(
                    client,
                    mode="single",
                    store=store,
                    lens_checklists={"baseline": ("demand-question",)},
                    now=datetime(2026, 9, 11, 2, 0, tzinfo=timezone.utc),
                    max_top_rows=1,
                ).run(input_)
            )
            run_path = Path(tmp) / input_.idea_id / "runs" / f"{artifact.run_id}.md"
            run_text = run_path.read_text(encoding="utf-8")
            with redirect_stderr(StringIO()):
                confirm_exit = idea_cli_main(
                    [
                        "confirm-test",
                        "--idea-id",
                        input_.idea_id,
                        "--run-id",
                        artifact.run_id,
                        "--test-id",
                        artifact.ledger.rows[0].test_id,
                        "--confirmed-by",
                        "Kelvin",
                        "--output-dir",
                        tmp,
                    ]
                )

        self.assertEqual(artifact.run_status.value, "COMPLETE")
        self.assertEqual(len(artifact.ledger.rows), 1)
        self.assertEqual(len(artifact.ledger.appendix_rows), 1)
        self.assertEqual(artifact.ledger.rows[0].state, LedgerState.EVIDENCE_BLOCKED)
        self.assertEqual(artifact.execution_config.mode, "single")
        self.assertEqual(artifact.execution_config.max_top_rows, 1)
        self.assertRegex(artifact.execution_config_hash or "", r"^[0-9a-f]{64}$")
        self.assertIsNotNone(artifact.adjudication)
        self.assertEqual(artifact.adjudication.run_id, artifact.run_id)
        self.assertIn("## Adjudication", run_text)
        self.assertRegex(artifact.integrity_hash or "", r"^[0-9a-f]{64}$")
        self.assertIn("supplied-source referenced", run_text)
        self.assertEqual(client.calls, ["baseline", "research-manager"])
        self.assertEqual(confirm_exit, 2)

    def test_multi_agent_pipeline_keeps_debate_closed_world(self):
        input_ = self._input().model_copy(
            update={
                "run_budget": self._input().run_budget.model_copy(
                    update={"max_model_calls": 20, "max_debate_rounds": 1}
                )
            }
        )
        client = DemoModelClient()

        with TemporaryDirectory() as tmp:
            store = IdeaStore(Path(tmp))
            store.save_input(input_)
            artifact = asyncio.run(
                IdeaPipeline(
                    client,
                    mode="multi",
                    store=store,
                    now=datetime(2026, 9, 11, 2, 0, tzinfo=timezone.utc),
                ).run(input_)
            )

        self.assertEqual(artifact.run_status.value, "COMPLETE")
        self.assertEqual(len(artifact.claims), 6)
        self.assertEqual(len(artifact.disputes), 0)
        self.assertEqual(len(artifact.ledger.rows), 1)
        self.assertEqual(
            artifact.ledger.rows[0].grounding_status,
            GroundingStatus.MODEL_DEPENDENT,
        )
        self.assertEqual(
            client.calls,
            [
                "analyst:demand",
                "analyst:buyer-distribution",
                "analyst:unit-economics",
                "analyst:feasibility",
                "analyst:competition",
                "analyst:risk",
                "debate:support:1",
                "debate:oppose:1",
                "debate:summary",
                "research-manager",
            ],
        )

    def test_failed_required_stage_is_persisted_as_blocked(self):
        input_ = self._input()
        client = ScriptedModelClient({}, cost=Decimal("0"))

        with TemporaryDirectory() as tmp:
            store = IdeaStore(Path(tmp))
            store.save_input(input_)
            artifact = asyncio.run(
                IdeaPipeline(
                    client,
                    mode="multi",
                    store=store,
                    now=datetime(2026, 9, 11, 2, 0, tzinfo=timezone.utc),
                ).run(input_)
            )
            run_path = Path(tmp) / input_.idea_id / "runs" / f"{artifact.run_id}.md"
            run_text = run_path.read_text(encoding="utf-8")

        self.assertEqual(artifact.run_status.value, "BLOCKED")
        self.assertTrue(any(error.code == "STAGE_FAILED" for error in artifact.errors))
        self.assertIn("BLOCKED", run_text)

    def test_public_pipeline_config_defines_six_lens_checklists(self):
        config = load_idea_config()

        self.assertEqual(config.max_top_rows, 5)
        self.assertEqual(
            set(config.lens_checklists),
            {
                "demand",
                "buyer-distribution",
                "unit-economics",
                "feasibility",
                "competition",
                "risk",
            },
        )

    def test_excluded_evidence_is_omitted_and_obvious_secrets_are_redacted(self):
        input_ = self._input().model_copy(
            update={
                "context_fields": [
                    self._input().context_fields[0].model_copy(
                        update={"value": "api_key=do-not-send"}
                    )
                ],
                "evidence": [
                    self._input().evidence[0].model_copy(
                        update={
                            "evidence_id": "ev-private-note",
                            "excerpt_or_observation": "private customer note",
                            "model_processing": ModelProcessing.EXCLUDED,
                        }
                    )
                ],
            }
        )
        context = validate_context(input_, now=datetime(2026, 9, 11, 2, 0, tzinfo=timezone.utc))

        payload = prepare_model_input(context)
        encoded = json.dumps(payload, ensure_ascii=False)

        self.assertNotIn("private customer note", encoded)
        self.assertNotIn("do-not-send", encoded)
        self.assertIn("[REDACTED]", encoded)

        with TemporaryDirectory() as tmp:
            store = IdeaStore(Path(tmp))
            store.save_input(input_)
            artifact = asyncio.run(
                IdeaPipeline(
                    DemoModelClient(),
                    mode="single",
                    store=store,
                    now=datetime(2026, 9, 11, 2, 0, tzinfo=timezone.utc),
                ).run(input_)
            )
            run_text = (
                Path(tmp)
                / input_.idea_id
                / "runs"
                / f"{artifact.run_id}.md"
            ).read_text(encoding="utf-8")
            loaded_run = store.load_run(input_.idea_id, artifact.run_id)

        self.assertNotIn("do-not-send", run_text)
        self.assertNotIn("private customer note", run_text)
        self.assertEqual(
            loaded_run.context.evidence[0].excerpt_or_observation,
            "[excluded from run artifact]",
        )

    def test_redacted_evidence_uses_only_the_approved_model_excerpt(self):
        input_ = self._input().model_copy(
            update={
                "evidence": [
                    self._input().evidence[0].model_copy(
                        update={
                            "model_processing": ModelProcessing.REDACTED,
                            "excerpt_or_observation": "private customer note",
                            "model_excerpt_or_observation": "A redacted customer observation.",
                        }
                    )
                ]
            }
        )
        context = validate_context(input_, now=datetime(2026, 9, 11, 2, 0, tzinfo=timezone.utc))

        evidence = prepare_model_input(context)["evidence"][0]

        self.assertEqual(evidence["excerpt_or_observation"], "A redacted customer observation.")
        self.assertNotIn("private customer note", json.dumps(evidence))
        self.assertNotIn("model_excerpt_or_observation", evidence)

        with TemporaryDirectory() as tmp:
            store = IdeaStore(Path(tmp))
            store.save_input(input_)
            artifact = asyncio.run(
                IdeaPipeline(
                    DemoModelClient(),
                    mode="single",
                    store=store,
                    now=datetime(2026, 9, 11, 2, 0, tzinfo=timezone.utc),
                ).run(input_)
            )
            loaded_run = store.load_run(input_.idea_id, artifact.run_id)

        self.assertEqual(
            loaded_run.context.evidence[0].excerpt_or_observation,
            "A redacted customer observation.",
        )

    def test_empty_explicit_unknown_list_is_supported_by_demo_pipeline(self):
        input_ = self._input().model_copy(update={"unknowns": [], "unknowns_declared": True})

        with TemporaryDirectory() as tmp:
            store = IdeaStore(Path(tmp))
            store.save_input(input_)
            artifact = asyncio.run(
                IdeaPipeline(
                    DemoModelClient(),
                    mode="multi",
                    store=store,
                    now=datetime(2026, 9, 11, 2, 0, tzinfo=timezone.utc),
                ).run(input_)
            )

        self.assertEqual(artifact.run_status.value, "COMPLETE")
        self.assertFalse(artifact.errors)

    def test_invalid_research_manager_output_blocks_single_run_without_a_ledger(self):
        input_ = self._input().model_copy(
            update={
                "run_budget": self._input().run_budget.model_copy(
                    update={"max_model_calls": 2, "max_retries_per_stage": 0}
                )
            }
        )

        def response(stage, payload):
            if stage == "baseline":
                return {
                    "checklist": [
                        {
                            "question_id": "demand-question",
                            "status": "UNKNOWN",
                            "unknown_id": "unk-urgent-demand",
                        }
                    ],
                    "claims": [
                        {
                            "candidate_key": "urgent-demand",
                            "statement": "Customers may pay.",
                            "claim_kind": "hypothesis",
                        }
                    ],
                }
            return {
                "thesis": {
                    "statement": "Invalid link.",
                    "claim_refs": ["claim-does-not-exist"],
                },
                "strongest_counterexample": {
                    "statement": "Invalid link.",
                    "claim_refs": ["claim-does-not-exist"],
                },
            }

        with TemporaryDirectory() as tmp:
            store = IdeaStore(Path(tmp))
            store.save_input(input_)
            artifact = asyncio.run(
                IdeaPipeline(
                    ScriptedModelClient(response),
                    mode="single",
                    store=store,
                    lens_checklists={"baseline": ("demand-question",)},
                    now=datetime(2026, 9, 11, 2, 0, tzinfo=timezone.utc),
                ).run(input_)
            )

        self.assertEqual(artifact.run_status.value, "BLOCKED")
        self.assertIsNone(artifact.ledger)
        self.assertTrue(any(error.stage == "research-manager" for error in artifact.errors))

    def test_model_output_with_a_secret_is_not_registered(self):
        input_ = self._input().model_copy(
            update={
                "run_budget": self._input().run_budget.model_copy(
                    update={"max_model_calls": 1, "max_retries_per_stage": 0}
                )
            }
        )

        def response(stage, payload):
            if stage == "baseline":
                return {
                    "checklist": [
                        {
                            "question_id": "demand-question",
                            "status": "UNKNOWN",
                            "unknown_id": "unk-urgent-demand",
                        }
                    ],
                    "claims": [
                        {
                            "candidate_key": "secret-claim",
                            "statement": "api_key=do-not-persist",
                            "claim_kind": "hypothesis",
                        }
                    ],
                }
            claim_id = payload["claims"][0]["claim_id"]
            return {
                "thesis": {
                    "statement": "The claim is untested.",
                    "claim_refs": [claim_id],
                },
                "strongest_counterexample": {
                    "statement": "The claim may be false.",
                    "claim_refs": [claim_id],
                },
            }

        with TemporaryDirectory() as tmp:
            store = IdeaStore(Path(tmp))
            store.save_input(input_)
            artifact = asyncio.run(
                IdeaPipeline(
                    ScriptedModelClient(response),
                    mode="single",
                    store=store,
                    lens_checklists={"baseline": ("demand-question",)},
                    now=datetime(2026, 9, 11, 2, 0, tzinfo=timezone.utc),
                ).run(input_)
            )

        self.assertEqual(artifact.run_status.value, "BLOCKED")
        self.assertEqual(artifact.claims, [])
        self.assertTrue(any(warning.code == "MODEL_OUTPUT_REDACTED" for warning in artifact.warnings))

    def test_load_run_rejects_tampered_content(self):
        input_ = self._input().model_copy(
            update={
                "run_budget": self._input().run_budget.model_copy(
                    update={"max_model_calls": 2}
                )
            }
        )

        def response(stage, payload):
            if stage == "baseline":
                return {
                    "checklist": [
                        {
                            "question_id": "demand-question",
                            "status": "UNKNOWN",
                            "unknown_id": "unk-urgent-demand",
                        }
                    ],
                    "claims": [
                        {
                            "candidate_key": "urgent-demand",
                            "statement": "Customers may pay.",
                            "claim_kind": "hypothesis",
                        }
                    ],
                }
            claim_id = payload["claims"][0]["claim_id"]
            return {
                "thesis": {
                    "statement": "Demand is untested.",
                    "claim_refs": [claim_id],
                },
                "strongest_counterexample": {
                    "statement": "Customers may not pay.",
                    "claim_refs": [claim_id],
                },
            }

        with TemporaryDirectory() as tmp:
            store = IdeaStore(Path(tmp))
            store.save_input(input_)
            artifact = asyncio.run(
                IdeaPipeline(
                    ScriptedModelClient(response),
                    mode="single",
                    store=store,
                    lens_checklists={"baseline": ("demand-question",)},
                    now=datetime(2026, 9, 11, 2, 0, tzinfo=timezone.utc),
                ).run(input_)
            )
            run_path = Path(tmp) / input_.idea_id / "runs" / f"{artifact.run_id}.md"
            run_path.write_text(
                run_path.read_text(encoding="utf-8").replace(
                    "run_status: COMPLETE", "run_status: BLOCKED", 1
                ),
                encoding="utf-8",
            )

            with self.assertRaises(StorageError):
                store.load_run(input_.idea_id, artifact.run_id)


if __name__ == "__main__":
    unittest.main()
