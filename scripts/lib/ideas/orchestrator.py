"""Execution graph for the startup-idea evaluation pipeline."""
from __future__ import annotations

import asyncio
import copy
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Mapping, Sequence

from pydantic import BaseModel, ValidationError

from .canonical import sha256_hex
from .ledger import LedgerBuildResult, build_ledger
from .model_client import ModelClient, ModelResult
from .models import (
    AnalystReport,
    DebateArgument,
    DebateOutput,
    DebateRound,
    DebateSummary,
    Dispute,
    ExecutionConfig,
    EvaluationContext,
    EvaluationInput,
    GroundingStatus,
    ResearchManagerOutput,
    RunArtifact,
    RunMessage,
    RunStatus,
    StageRecord,
    TestProposal,
)
from .privacy import (
    prepare_model_input,
    sanitize_context_for_artifact,
    sanitize_model_output,
)
from .registry import (
    RegistryResult,
    filter_valid_checklist_reports,
    register_reports,
    validate_debate_output,
    validate_research_manager_output,
)
from .storage import IdeaStore
from .validate import validate_context


DEFAULT_LENS_CHECKLISTS: dict[str, tuple[str, ...]] = {
    "demand": ("problem-severity", "urgency", "alternatives"),
    "buyer-distribution": ("buyer", "channel", "willingness-to-pay"),
    "unit-economics": ("price", "cost-shape", "cac-path"),
    "feasibility": ("sellable-version", "operations", "founder-fit"),
    "competition": ("substitutes", "incumbents", "defensibility"),
    "risk": ("regulatory", "trust", "dependencies"),
}
DEFAULT_LENSES = tuple(DEFAULT_LENS_CHECKLISTS)


class PipelineError(RuntimeError):
    """Base error for a required pipeline-stage failure."""


class BudgetExceeded(PipelineError):
    pass


class StageFailure(PipelineError):
    def __init__(self, stage: str, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.stage = stage
        self.retryable = retryable


@dataclass
class _BudgetTracker:
    budget: Any
    started: float = field(default_factory=time.monotonic)
    model_calls: int = 0
    model_cost: Decimal = Decimal("0")
    cost_unknown: bool = False
    currency_mismatch: bool = False
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def reserve(self, stage: str) -> None:
        async with self.lock:
            self.check_time()
            if self.model_calls >= self.budget.max_model_calls:
                raise BudgetExceeded(f"model-call budget exhausted before {stage}")
            self.model_calls += 1

    def record(self, result: ModelResult) -> None:
        if result.cost is None or result.currency is None:
            self.cost_unknown = True
            return
        if not result.cost.is_finite() or result.cost < 0:
            raise BudgetExceeded("model returned an invalid cost")
        if result.currency != self.budget.currency:
            self.currency_mismatch = True
            return
        self.model_cost += result.cost
        if self.model_cost > self.budget.max_model_cost:
            raise BudgetExceeded("model-cost budget exhausted")

    def check_time(self) -> None:
        elapsed_minutes = (time.monotonic() - self.started) / 60
        if elapsed_minutes > self.budget.max_wall_clock_minutes:
            raise BudgetExceeded("wall-clock budget exhausted")


def _message(
    stage: str,
    code: str,
    message: str,
    affected: Sequence[str] = (),
    *,
    retryable: bool = False,
) -> RunMessage:
    return RunMessage(
        stage=stage,
        code=code,
        message=message,
        affected_ids=list(affected),
        retryable=retryable,
    )


def _scrub_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Remove validator-owned envelope fields from provider schemas."""
    forbidden = {"run_id", "schema_version", "producer_id", "lens_id"}
    output = copy.deepcopy(schema)
    if isinstance(output.get("properties"), dict):
        for key in forbidden:
            output["properties"].pop(key, None)
    if isinstance(output.get("required"), list):
        output["required"] = [key for key in output["required"] if key not in forbidden]
    for value in output.values():
        if isinstance(value, dict):
            value.update(_scrub_schema(value))
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    item.update(_scrub_schema(item))
    return output


def _bind_payload(
    payload: dict[str, Any],
    *,
    output_model: type[BaseModel],
    context: EvaluationContext,
    producer_id: str | None = None,
    lens_id: str | None = None,
) -> dict[str, Any]:
    bound = copy.deepcopy(payload)
    name = output_model.__name__
    if name == "AnalystReport":
        bound.update(
            {
                "run_id": context.run_id,
                "schema_version": context.pipeline_version,
                "producer_id": producer_id,
                "lens_id": lens_id,
            }
        )
    elif name == "DebateArgument":
        bound.update({"run_id": context.run_id, "producer_id": producer_id})
    elif name == "ResearchManagerOutput":
        bound["run_id"] = context.run_id
    return bound


def _model_metadata(result: ModelResult, stage: str) -> dict[str, str | int | float | None]:
    return {
        "stage": stage,
        "provider": result.provider,
        "model": result.model,
        "prompt_hash": result.prompt_hash,
        "config_hash": result.config_hash,
        "cost": str(result.cost) if result.cost is not None else None,
        "currency": result.currency,
        "elapsed_seconds": round(result.elapsed_seconds, 4),
    }


class IdeaPipeline:
    """Run either the single-agent baseline or the multi-agent topology."""

    def __init__(
        self,
        model_client: ModelClient,
        *,
        mode: str = "multi",
        store: IdeaStore | None = None,
        lens_checklists: Mapping[str, Sequence[str]] | None = None,
        max_top_rows: int = 5,
        config_schema_version: str = "inline",
        now: datetime | None = None,
    ) -> None:
        if mode not in {"single", "multi"}:
            raise ValueError("mode must be 'single' or 'multi'")
        self.model_client = model_client
        self.mode = mode
        self.store = store
        self.lens_checklists = dict(lens_checklists or DEFAULT_LENS_CHECKLISTS)
        self.max_top_rows = max_top_rows
        self.execution_config = ExecutionConfig(
            schema_version=config_schema_version,
            mode=mode,
            max_top_rows=max_top_rows,
            lens_checklists=self.lens_checklists,
        )
        self.execution_config_hash = sha256_hex(self.execution_config)
        self.now = now
        self._tracker: _BudgetTracker | None = None
        self._context: EvaluationContext | None = None
        self._metadata: list[dict[str, str | int | float | None]] = []
        self._stages: list[StageRecord] = []
        self._errors: list[RunMessage] = []
        self._warnings: list[RunMessage] = []
        self._fatal_failure = False
        self._current_claims = []
        self._current_disputes = []
        self._current_gaps = []
        self._current_debate: DebateOutput | None = None
        self._current_adjudication: ResearchManagerOutput | None = None
        self._current_ledger = None
        self._prior_claim_ids: set[str] = set()
        self._prior_test_ids: set[str] = set()

    async def run(self, input_: EvaluationInput | EvaluationContext) -> RunArtifact:
        context = (
            input_
            if isinstance(input_, EvaluationContext)
            else validate_context(input_, now=self.now)
        )
        self._context = context
        self._tracker = _BudgetTracker(context.run_budget)
        self._metadata = []
        self._stages = []
        self._errors = []
        self._warnings = []

        self._fatal_failure = False
        self._current_claims = []
        self._current_disputes = []
        self._current_gaps = []
        self._current_debate = None
        self._current_adjudication = None
        self._current_ledger = None
        if self.store is not None:
            self._prior_claim_ids = self.store.prior_claim_ids(context.idea_id)
            self._prior_test_ids = self.store.prior_test_ids(context.idea_id)
        else:
            self._prior_claim_ids = set()
            self._prior_test_ids = set()
        try:
            self._checkpoint(RunStatus.PARTIAL)
            if self.mode == "single":
                claims, disputes, gaps, ledger = await self._run_single()
            else:
                claims, disputes, gaps, ledger = await self._run_multi()
            self._current_claims = list(claims)
            self._current_disputes = list(disputes)
            self._current_gaps = list(gaps)
            self._current_ledger = ledger
            self._tracker.check_time()
        except StageFailure as exc:
            self._fatal_failure = True
            self._errors.append(
                _message(exc.stage, "STAGE_FAILED", str(exc), retryable=exc.retryable)
            )
            self._stages.append(
                StageRecord(stage=exc.stage, status="BLOCKED")
            )
        except BudgetExceeded as exc:
            self._fatal_failure = True
            self._errors.append(_message("execution", "BUDGET_EXCEEDED", str(exc)))
            self._stages.append(StageRecord(stage="execution", status="BLOCKED"))
        except Exception as exc:
            self._fatal_failure = True
            self._errors.append(_message("execution", "UNEXPECTED_FAILURE", str(exc)))
            self._stages.append(StageRecord(stage="execution", status="BLOCKED"))

        claims = self._current_claims
        disputes = self._current_disputes
        gaps = self._current_gaps
        ledger = self._current_ledger
        if self._tracker.cost_unknown:
            self._warnings.append(
                _message("execution", "MODEL_COST_UNKNOWN", "one or more model responses did not report cost")
            )
        if self._tracker.currency_mismatch:
            self._warnings.append(
                _message("execution", "MODEL_COST_CURRENCY", "model cost currency did not match the run budget currency")
            )

        status = self._status_for(ledger)
        artifact = self._artifact(
            status,
            claims=claims,
            disputes=disputes,
            gaps=gaps,
            debate=self._current_debate,
            adjudication=self._current_adjudication,
            ledger=ledger,
        )
        if status is RunStatus.COMPLETE and (
            self._tracker.cost_unknown or self._tracker.currency_mismatch
        ):
            artifact = artifact.model_copy(update={"run_status": RunStatus.PARTIAL})
        artifact = self._with_integrity(artifact)
        if self.store is not None:
            self.store.write_run(artifact, final=True)
        return artifact

    async def _run_single(self):
        assert self._context is not None
        baseline_questions = self._baseline_question_ids()
        report, _ = await self._call(
            "baseline",
            "Produce one evidence-bounded analyst report. Answer the checklist and propose candidate claims only; do not assign canonical claim IDs or write research-manager prose.",
            {
                "context": prepare_model_input(self._context),
                "required_question_ids": list(baseline_questions),
                "prior_claim_ids": sorted(self._prior_claim_ids),
                "prior_test_ids": sorted(self._prior_test_ids),
            },
            AnalystReport,
            producer_id="baseline",
            lens_id="baseline",
        )
        self._complete_stage("baseline", report)
        self._checkpoint(RunStatus.PARTIAL)
        valid_reports, report_errors = filter_valid_checklist_reports(
            [report], {"baseline": baseline_questions}
        )
        self._errors.extend(report_errors)
        if not valid_reports:
            raise StageFailure(
                "baseline",
                "baseline analyst output failed closed-world checklist validation",
            )
        registry = register_reports(
            self._context,
            valid_reports,
            prior_claim_ids=self._prior_claim_ids,
        )
        self._current_claims = list(registry.claims)
        self._current_disputes = list(registry.disputes)
        self._current_gaps = list(registry.evidence_gaps)
        self._errors.extend(registry.errors)
        self._warnings.extend(registry.warnings)
        self._checkpoint(RunStatus.PARTIAL)
        try:
            manager, _ = await self._call(
                "research-manager",
                "Adjudicate only the registered claim graph. Return linked statements, gaps, alternatives, and test proposals. Do not invent facts, canonical IDs, or a build recommendation.",
                {
                    "context": prepare_model_input(self._context),
                    "claims": [claim.model_dump(mode="json") for claim in registry.claims],
                    "evidence_gaps": [gap.model_dump(mode="json") for gap in registry.evidence_gaps],
                    "prior_claim_ids": sorted(self._prior_claim_ids),
                    "prior_test_ids": sorted(self._prior_test_ids),
                },
                ResearchManagerOutput,
            )
        except Exception as exc:
            raise StageFailure("research-manager", str(exc), retryable=True) from exc
        gaps, manager_errors = validate_research_manager_output(
            self._context, registry, manager
        )
        self._errors.extend(manager_errors)
        if manager_errors:
            raise StageFailure(
                "research-manager",
                "research-manager output failed closed-world validation",
            )
        self._current_adjudication = manager
        registry.evidence_gaps.extend(gaps)
        self._current_gaps = list(registry.evidence_gaps)
        self._complete_stage("research-manager", manager)
        self._checkpoint(RunStatus.PARTIAL)
        ledger_result = build_ledger(
            self._context,
            registry,
            manager.test_proposals,
            alternatives=manager.alternatives,
            max_top_rows=self.max_top_rows,
            prior_test_ids=self._prior_test_ids,
        )
        self._errors.extend(ledger_result.errors)
        self._warnings.extend(ledger_result.warnings)
        self._complete_stage("ledger", ledger_result.ledger)
        self._current_ledger = ledger_result.ledger
        self._checkpoint(RunStatus.PARTIAL)
        return registry.claims, registry.disputes, registry.evidence_gaps, ledger_result.ledger

    def _baseline_question_ids(self) -> tuple[str, ...]:
        """Use one explicit baseline checklist for fair topology comparisons."""
        if "baseline" in self.lens_checklists:
            return tuple(self.lens_checklists["baseline"])
        question_ids: list[str] = []
        seen: set[str] = set()
        for questions in self.lens_checklists.values():
            for question_id in questions:
                if question_id not in seen:
                    seen.add(question_id)
                    question_ids.append(question_id)
        return tuple(question_ids)

    async def _run_multi(self):
        assert self._context is not None
        lens_ids = tuple(self.lens_checklists)
        tasks = [self._run_lens(lens_id) for lens_id in lens_ids]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        reports: list[AnalystReport] = []
        for lens_id, response in zip(lens_ids, responses):
            if isinstance(response, Exception):
                self._errors.append(
                    _message("analyst", "LENS_UNAVAILABLE", f"lens {lens_id} unavailable: {response}", [lens_id], retryable=True)
                )
            else:
                reports.append(response)
        if not reports:
            raise StageFailure("analyst", "all analyst lenses failed")
        self._complete_stage("analysts", reports)
        self._checkpoint(RunStatus.PARTIAL)
        valid_reports, checklist_errors = filter_valid_checklist_reports(
            reports, self.lens_checklists
        )
        self._errors.extend(checklist_errors)
        if not valid_reports:
            raise StageFailure(
                "analyst",
                "all analyst lenses failed closed-world checklist validation",
            )
        registry = register_reports(
            self._context,
            valid_reports,
            prior_claim_ids=self._prior_claim_ids,
        )
        self._current_claims = list(registry.claims)
        self._current_disputes = list(registry.disputes)
        self._current_gaps = list(registry.evidence_gaps)
        self._errors.extend(registry.errors)
        self._warnings.extend(registry.warnings)
        if not registry.claims:
            raise StageFailure("registry", "no analyst claims survived registry validation")
        self._complete_stage("registry", registry.claims)
        self._checkpoint(RunStatus.PARTIAL)

        try:
            debate = await self._run_debate(registry)
        except Exception as exc:
            raise StageFailure("debate", str(exc), retryable=True) from exc
        debate_errors = validate_debate_output(self._context, registry, debate)
        if debate_errors:
            self._errors.extend(debate_errors)
            raise StageFailure("debate", "debate output failed closed-world validation")
        self._current_debate = debate
        self._complete_stage("debate", debate)
        self._checkpoint(RunStatus.PARTIAL)

        disputes = _disputes_from_debate(debate)
        post_registry = register_reports(
            self._context,
            valid_reports,
            disputes=disputes,
            prior_claim_ids=self._prior_claim_ids,
        )
        self._errors.extend(post_registry.errors)
        self._warnings.extend(post_registry.warnings)
        if post_registry.errors:
            raise StageFailure("post-debate-registry", "post-debate registry failed")
        self._current_claims = list(post_registry.claims)
        self._current_disputes = list(post_registry.disputes)
        self._current_gaps = list(post_registry.evidence_gaps)
        self._complete_stage("post-debate-registry", post_registry.claims)
        self._checkpoint(RunStatus.PARTIAL)

        try:
            manager, _ = await self._call(
                "research-manager",
                "Adjudicate only the registered claim graph. Return linked statements, gaps, alternatives, and test proposals. Do not invent facts or a build recommendation.",
                {
                    "context": prepare_model_input(self._context),
                    "claims": [claim.model_dump(mode="json") for claim in post_registry.claims],
                    "disputes": [dispute.model_dump(mode="json") for dispute in post_registry.disputes],
                    "unknowns": [unknown.model_dump(mode="json") for unknown in self._context.unknowns],
                    "debate": debate.model_dump(mode="json"),
                    "prior_claim_ids": sorted(self._prior_claim_ids),
                    "prior_test_ids": sorted(self._prior_test_ids),
                },
                ResearchManagerOutput,
            )
        except Exception as exc:
            raise StageFailure("research-manager", str(exc), retryable=True) from exc
        new_gaps, manager_errors = validate_research_manager_output(
            self._context, post_registry, manager
        )
        self._errors.extend(manager_errors)
        if manager_errors:
            raise StageFailure("research-manager", "research-manager output failed closed-world validation")
        self._current_adjudication = manager
        post_registry.evidence_gaps.extend(new_gaps)
        self._current_gaps = list(post_registry.evidence_gaps)
        self._complete_stage("research-manager", manager)
        self._checkpoint(RunStatus.PARTIAL)

        ledger_result = build_ledger(
            self._context,
            post_registry,
            manager.test_proposals,
            alternatives=manager.alternatives,
            max_top_rows=self.max_top_rows,
            prior_test_ids=self._prior_test_ids,
        )
        self._errors.extend(ledger_result.errors)
        self._warnings.extend(ledger_result.warnings)
        self._complete_stage("ledger", ledger_result.ledger)
        self._current_ledger = ledger_result.ledger
        self._checkpoint(RunStatus.PARTIAL)
        return post_registry.claims, post_registry.disputes, post_registry.evidence_gaps, ledger_result.ledger

    async def _run_lens(self, lens_id: str) -> AnalystReport:
        assert self._context is not None
        report, _ = await self._call(
            f"analyst:{lens_id}",
            f"You are the {lens_id} analyst. Answer every checklist question exactly once. Use only supplied evidence, context, assumptions, or explicit model hypotheses. Return structured JSON only.",
            {
                "context": prepare_model_input(self._context),
                "lens_id": lens_id,
                "required_question_ids": list(self.lens_checklists[lens_id]),
                "prior_claim_ids": sorted(self._prior_claim_ids),
                "prior_test_ids": sorted(self._prior_test_ids),
            },
            AnalystReport,
            producer_id=lens_id,
            lens_id=lens_id,
        )
        return report

    async def _run_debate(self, registry: RegistryResult) -> DebateOutput:
        assert self._context is not None
        rounds: list[DebateRound] = []
        if self._context.run_budget.max_debate_rounds < 1:
            raise BudgetExceeded("multi-agent mode requires at least one debate round")
        registry_payload = [claim.model_dump(mode="json") for claim in registry.claims]
        for round_number in range(1, self._context.run_budget.max_debate_rounds + 1):
            common = {
                "context": prepare_model_input(self._context),
                "claims": registry_payload,
                "previous_rounds": [round_.model_dump(mode="json") for round_ in rounds],
                "round_number": round_number,
            }
            support, _ = await self._call(
                f"debate:support:{round_number}",
                "Build the strongest support case using only registered claim IDs and unknown IDs. Propose typed disputes when evidence conflicts.",
                {**common, "position": "support"},
                DebateArgument,
                producer_id="support",
            )
            oppose, _ = await self._call(
                f"debate:oppose:{round_number}",
                "Build the strongest oppose case using only registered claim IDs and unknown IDs. Propose typed disputes when evidence conflicts.",
                {
                    **common,
                    "position": "oppose",
                    "support_argument": support.model_dump(mode="json"),
                },
                DebateArgument,
                producer_id="oppose",
            )
            rounds.append(
                DebateRound(round_number=round_number, support=support, oppose=oppose)
            )
        summary, _ = await self._call(
            "debate:summary",
            "Summarize agreement, disagreement, and unresolved unknowns using only existing IDs.",
            {
                "context": prepare_model_input(self._context),
                "claims": registry_payload,
                "rounds": [round_.model_dump(mode="json") for round_ in rounds],
            },
            DebateSummary,
        )
        return DebateOutput(
            run_id=self._context.run_id,
            rounds=rounds,
            agreement_claim_refs=summary.agreement_claim_refs,
            disagreement_claim_refs=summary.disagreement_claim_refs,
            unresolved_unknown_refs=summary.unresolved_unknown_refs,
        )

    async def _call(
        self,
        stage: str,
        system_prompt: str,
        input_payload: dict[str, Any],
        output_model: type[BaseModel],
        *,
        producer_id: str | None = None,
        lens_id: str | None = None,
    ) -> tuple[Any, ModelResult]:
        assert self._context is not None and self._tracker is not None
        schema = _scrub_schema(output_model.model_json_schema())
        attempts = self._context.run_budget.max_retries_per_stage + 1
        last_error: Exception | None = None
        for attempt in range(attempts):
            try:
                await self._tracker.reserve(stage)
                remaining = (
                    self._context.run_budget.max_wall_clock_minutes * 60
                    - (time.monotonic() - self._tracker.started)
                )
                if remaining <= 0:
                    raise BudgetExceeded(f"wall-clock budget exhausted before {stage}")
                result = await asyncio.wait_for(
                    self.model_client.complete(
                        stage=stage,
                        system_prompt=system_prompt,
                        input_payload=input_payload,
                        output_model=output_model,
                        output_schema=schema,
                    ),
                    timeout=remaining,
                )
                self._tracker.record(result)
                self._metadata.append(_model_metadata(result, stage))
                sanitized = sanitize_model_output(result.payload, self._context)
                if sanitized != result.payload:
                    self._warnings.append(
                        _message(
                            stage,
                            "MODEL_OUTPUT_REDACTED",
                            "model output contained a secret or excluded fragment and was rejected",
                            retryable=False,
                        )
                    )
                    raise StageFailure(
                        stage,
                        "model output contained a secret or excluded fragment",
                    )
                bound = _bind_payload(
                    sanitized,
                    output_model=output_model,
                    context=self._context,
                    producer_id=producer_id,
                    lens_id=lens_id,
                )
                return output_model.model_validate(bound), result
            except BudgetExceeded:
                raise
            except (ValidationError, ValueError, TypeError, KeyError, RuntimeError, asyncio.TimeoutError) as exc:
                last_error = exc
                if attempt + 1 >= attempts:
                    break
        assert last_error is not None
        raise StageFailure(
            stage,
            f"{stage} failed after {attempts} attempt(s): {last_error}",
            retryable=True,
        ) from last_error

    def _complete_stage(self, stage: str, payload: Any) -> None:
        now = datetime.now(timezone.utc)
        self._stages.append(
            StageRecord(
                stage=stage,
                status="COMPLETE",
                started_at=now,
                completed_at=now,
                artifact_hash=sha256_hex(payload),
            )
        )

    def _status_for(self, ledger) -> RunStatus:
        if self._fatal_failure:
            return RunStatus.BLOCKED
        if not self._stages:
            return RunStatus.BLOCKED
        if self._errors:
            return RunStatus.PARTIAL
        if ledger is None:
            return RunStatus.BLOCKED
        return RunStatus.COMPLETE

    def _artifact(
        self,
        status: RunStatus,
        *,
        claims,
        disputes,
        gaps,
        debate,
        adjudication,
        ledger,
    ) -> RunArtifact:
        assert self._context is not None
        return RunArtifact(
            schema_version="1",
            run_id=self._context.run_id,
            idea_id=self._context.idea_id,
            input_snapshot_id=self._context.input_snapshot_id,
            evaluated_at=self._context.evaluated_at,
            execution_config=self.execution_config,
            execution_config_hash=self.execution_config_hash,
            run_status=status,
            context=sanitize_context_for_artifact(self._context),
            claims=list(claims),
            disputes=list(disputes),
            evidence_gaps=list(gaps),
            debate=debate,
            adjudication=adjudication,
            ledger=ledger,
            stages=list(self._stages),
            errors=list(self._errors),
            warnings=list(self._warnings),
            model_metadata=sorted(
                self._metadata,
                key=lambda item: (str(item.get("stage")), str(item.get("prompt_hash"))),
            ),
            pipeline_version=self._context.pipeline_version,
        )

    def _checkpoint(self, status: RunStatus) -> None:
        if self.store is None or self._context is None:
            return
        artifact = self._artifact(
            status,
            claims=self._current_claims,
            disputes=self._current_disputes,
            gaps=self._current_gaps,
            debate=self._current_debate,
            adjudication=self._current_adjudication,
            ledger=self._current_ledger,
        )
        self.store.write_run(artifact, final=False)

    @staticmethod
    def _with_integrity(artifact: RunArtifact) -> RunArtifact:
        payload = artifact.model_dump(mode="json", exclude={"integrity_hash"})
        return artifact.model_copy(update={"integrity_hash": sha256_hex(payload)})


def _disputes_from_debate(debate: DebateOutput) -> list[Dispute]:
    disputes: list[Dispute] = []
    for round_ in debate.rounds:
        for argument in (round_.support, round_.oppose):
            for proposal in argument.dispute_proposals:
                seed = {
                    "producer": argument.producer_id,
                    "round": round_.round_number,
                    "proposal": proposal.model_dump(mode="json"),
                }
                dispute_id = f"dispute-{argument.producer_id}-{sha256_hex(seed)[:12]}"
                reason_claim_refs = proposal.reason_claim_refs or proposal.claim_refs[:1]
                disputes.append(
                    Dispute(
                        dispute_id=dispute_id,
                        claim_refs=proposal.claim_refs,
                        evidence_refs=proposal.evidence_refs,
                        reason=proposal.reason,
                        reason_claim_refs=reason_claim_refs,
                        unknown_refs=proposal.unknown_refs,
                        actor=argument.producer_id,
                    )
                )
    return disputes
