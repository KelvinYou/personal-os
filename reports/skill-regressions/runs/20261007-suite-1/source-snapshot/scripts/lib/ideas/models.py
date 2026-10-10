"""Typed contracts for the startup-idea evaluation pipeline.

The models in this module are the boundary between user input, model output,
and the deterministic registry/ledger code.  They deliberately reject unknown
fields so a prompt or an accidental provider field cannot silently become part
of the persisted contract.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .canonical import sha256_hex


SAFE_ID_PATTERN = r"^[a-z0-9][a-z0-9-]*$"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ModelProcessing(str, Enum):
    ALLOWED = "allowed"
    REDACTED = "redacted"
    EXCLUDED = "excluded"


class TemporalStatus(str, Enum):
    OBSERVED = "observed"
    EFFECTIVE = "effective"
    FORECAST = "forecast"
    PLANNED = "planned"


class ClaimKind(str, Enum):
    FACT = "fact"
    ASSUMPTION = "assumption"
    HYPOTHESIS = "hypothesis"
    DERIVED = "derived"


class Provenance(str, Enum):
    CITED = "CITED"
    USER_ASSUMED = "USER-ASSUMED"
    DERIVED = "DERIVED"
    MODEL_GUESSED = "MODEL-GUESSED"
    NOT_APPLICABLE = "N/A"


class EvidenceStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    CONFLICTED = "CONFLICTED"
    STALE = "STALE"
    FRESHNESS_UNKNOWN = "FRESHNESS-UNKNOWN"
    MISSING = "MISSING"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class GroundingStatus(str, Enum):
    GROUNDED = "GROUNDED"
    ASSUMPTION_DEPENDENT = "ASSUMPTION-DEPENDENT"
    MODEL_DEPENDENT = "MODEL-DEPENDENT"
    UNRESOLVED = "UNRESOLVED"


class LensQuestionStatus(str, Enum):
    ADDRESSED = "ADDRESSED"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ImpactIfFalse(str, Enum):
    FATAL = "FATAL"
    MAJOR = "MAJOR"
    MINOR = "MINOR"
    UNKNOWN = "UNKNOWN"


class LedgerState(str, Enum):
    PROVISIONAL = "PROVISIONAL"
    EVIDENCE_BLOCKED = "EVIDENCE-BLOCKED"
    VALIDATED = "VALIDATED"
    FALSIFIED = "FALSIFIED"
    CONFLICTED = "CONFLICTED"
    INCONCLUSIVE = "INCONCLUSIVE"
    NOT_RUN = "NOT_RUN"
    UNPRIORITIZED = "UNPRIORITIZED"


class Priority(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    UNPRIORITIZED = "UNPRIORITIZED"


class RunStatus(str, Enum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    BLOCKED = "BLOCKED"
    REJECTED = "REJECTED"


class TestResultState(str, Enum):
    VALIDATED = "VALIDATED"
    FALSIFIED = "FALSIFIED"
    CONFLICTED = "CONFLICTED"
    INCONCLUSIVE = "INCONCLUSIVE"
    NOT_RUN = "NOT_RUN"


class FormulaOperation(str, Enum):
    ADD = "add"
    SUBTRACT = "subtract"
    MULTIPLY = "multiply"
    DIVIDE = "divide"
    MIN = "min"
    MAX = "max"
    RATIO = "ratio"


class DecisionGoal(StrictModel):
    question: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    trigger: str = Field(min_length=1)
    deadline: date | None = None


class ContextField(StrictModel):
    context_ref: str = Field(pattern=SAFE_ID_PATTERN)
    field: str = Field(min_length=1)
    value: str = Field(min_length=1)
    scope: str = Field(min_length=1)


class UserAssumption(StrictModel):
    user_assumption_id: str = Field(pattern=SAFE_ID_PATTERN)
    statement: str = Field(min_length=1)
    scope: str = Field(min_length=1)
    recorded_at: date
    owner: str = Field(min_length=1)
    expires_at: date | None = None
    review_date: date | None = None


class Unknown(StrictModel):
    unknown_id: str = Field(pattern=SAFE_ID_PATTERN)
    statement: str = Field(min_length=1)
    scope: str = Field(min_length=1)


class EvidenceItem(StrictModel):
    evidence_id: str = Field(pattern=SAFE_ID_PATTERN)
    locator: str = Field(min_length=1)
    publisher_or_source: str = Field(min_length=1)
    observed_or_effective_at: date | Literal["unknown"]
    retrieved_at: date
    scope: str = Field(min_length=1)
    excerpt_or_observation: str = Field(min_length=1)
    model_excerpt_or_observation: str | None = None
    freshness_window: int | Literal["not_applicable"]
    model_processing: ModelProcessing
    temporal_status: TemporalStatus = TemporalStatus.OBSERVED
    supersedes_evidence_id: str | None = Field(default=None, pattern=SAFE_ID_PATTERN)
    quality_note: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_processing_contract(self) -> EvidenceItem:
        if isinstance(self.freshness_window, int) and self.freshness_window < 0:
            raise ValueError("freshness_window must not be negative")
        if self.model_processing is ModelProcessing.REDACTED and not self.model_excerpt_or_observation:
            raise ValueError(
                "redacted evidence requires model_excerpt_or_observation"
            )
        return self


class Consent(StrictModel):
    actor: str = Field(min_length=1)
    scope: str = Field(min_length=1)
    granted_at: datetime
    expires_at: datetime | None = None


class RunBudget(StrictModel):
    max_model_calls: int = Field(ge=1)
    max_debate_rounds: int = Field(ge=0)
    max_retries_per_stage: int = Field(ge=0)
    max_model_cost: Decimal = Field(ge=Decimal("0"))
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    max_wall_clock_minutes: int = Field(ge=1)
    max_user_minutes: int = Field(ge=0)


class EvaluationInput(StrictModel):
    """User-owned input before preflight assigns run metadata."""

    idea_id: str = Field(pattern=SAFE_ID_PATTERN)
    as_of: date
    scope: str = Field(min_length=1)
    constraints: list[str] = Field(min_length=1)
    decision_goal: DecisionGoal
    context_fields: list[ContextField] = Field(min_length=1)
    user_assumptions: list[UserAssumption] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    unknowns: list[Unknown] = Field(default_factory=list)
    unknowns_declared: bool
    consent: Consent
    run_budget: RunBudget
    history_refs: list[str] = Field(default_factory=list)
    historical_replay: bool = False
    historical_replay_reason: str | None = None
    pipeline_version: str = "1"


class EvaluationContext(EvaluationInput):
    """Validated input with validator-owned identity and snapshot metadata."""

    run_id: str = Field(pattern=r"^run-[0-9a-f]{32}$")
    evaluated_at: datetime
    input_snapshot_id: str = Field(pattern=r"^[0-9a-f]{64}$")


class ExecutionConfig(StrictModel):
    """Immutable topology/configuration provenance for one pipeline run."""

    schema_version: str = Field(min_length=1)
    mode: Literal["single", "multi"]
    max_top_rows: int = Field(ge=1)
    lens_checklists: dict[str, list[str]] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_checklists(self) -> ExecutionConfig:
        for lens_id, question_ids in self.lens_checklists.items():
            if not re.fullmatch(SAFE_ID_PATTERN, lens_id):
                raise ValueError(f"unsafe lens ID: {lens_id}")
            if not question_ids or len(question_ids) != len(set(question_ids)):
                raise ValueError(f"lens {lens_id} requires unique checklist IDs")
            for question_id in question_ids:
                if not re.fullmatch(SAFE_ID_PATTERN, question_id):
                    raise ValueError(f"unsafe checklist ID: {question_id}")
        return self


class Quantity(StrictModel):
    """A scalar or closed interval with explicit unit and precision."""

    scalar: Decimal | None = None
    lower: Decimal | None = None
    upper: Decimal | None = None
    unit: str = Field(min_length=1)
    precision: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_shape(self) -> Quantity:
        scalar_set = self.scalar is not None
        interval_set = self.lower is not None or self.upper is not None
        if scalar_set == interval_set:
            raise ValueError("quantity must be either scalar or interval")
        if interval_set and (self.lower is None or self.upper is None):
            raise ValueError("quantity intervals require lower and upper")
        if self.lower is not None and self.upper is not None and self.lower > self.upper:
            raise ValueError("quantity lower must not exceed upper")
        return self


class FormulaSpec(StrictModel):
    operation: FormulaOperation
    operands: list[str] = Field(min_length=1)
    output_unit: str = Field(min_length=1)
    rounding: int = Field(ge=0)


class ClaimCandidate(StrictModel):
    candidate_key: str = Field(pattern=SAFE_ID_PATTERN)
    statement: str = Field(min_length=1)
    evidence_refs: list[str] = Field(default_factory=list)
    context_refs: list[str] = Field(default_factory=list)
    user_assumption_refs: list[str] = Field(default_factory=list)
    derivation_refs: list[str] = Field(default_factory=list)
    quantity: Quantity | None = None
    formula: FormulaSpec | None = None
    unknown_refs: list[str] = Field(default_factory=list)
    dispute_refs: list[str] = Field(default_factory=list)
    claim_kind: ClaimKind
    supersedes_claim_id: str | None = Field(default=None, pattern=SAFE_ID_PATTERN)


class RegisteredClaim(StrictModel):
    claim_id: str = Field(pattern=SAFE_ID_PATTERN)
    producer_id: str = Field(pattern=SAFE_ID_PATTERN)
    candidate_key: str = Field(pattern=SAFE_ID_PATTERN)
    statement: str = Field(min_length=1)
    evidence_refs: list[str] = Field(default_factory=list)
    context_refs: list[str] = Field(default_factory=list)
    user_assumption_refs: list[str] = Field(default_factory=list)
    derivation_refs: list[str] = Field(default_factory=list)
    unknown_refs: list[str] = Field(default_factory=list)
    dispute_refs: list[str] = Field(default_factory=list)
    claim_kind: ClaimKind
    provenance: Provenance
    evidence_status: EvidenceStatus
    grounding_status: GroundingStatus
    quantity: Quantity | None = None
    formula: FormulaSpec | None = None
    supersedes_claim_id: str | None = Field(default=None, pattern=SAFE_ID_PATTERN)


class Dispute(StrictModel):
    dispute_id: str = Field(pattern=SAFE_ID_PATTERN)
    claim_refs: list[str] = Field(min_length=1)
    evidence_refs: list[str] = Field(default_factory=list)
    reason: str = Field(min_length=1)
    reason_claim_refs: list[str] = Field(default_factory=list)
    unknown_refs: list[str] = Field(default_factory=list)
    actor: str = Field(min_length=1)
    user_resolution: str | None = None


class EvidenceGap(StrictModel):
    gap_id: str = Field(pattern=SAFE_ID_PATTERN)
    unknown_ids: list[str] = Field(min_length=1)
    affected_claim_ids: list[str] = Field(default_factory=list)
    why_load_bearing: str = Field(min_length=1)
    test_id: str | None = Field(default=None, pattern=SAFE_ID_PATTERN)


class LensQuestion(StrictModel):
    question_id: str = Field(pattern=SAFE_ID_PATTERN)
    status: LensQuestionStatus
    claim_ids: list[str] = Field(default_factory=list)
    unknown_id: str | None = Field(default=None, pattern=SAFE_ID_PATTERN)
    reason: str | None = None

    @model_validator(mode="after")
    def validate_answer(self) -> LensQuestion:
        if self.status is LensQuestionStatus.ADDRESSED and not self.claim_ids:
            raise ValueError("ADDRESSED lens questions require claim_ids")
        if self.status is LensQuestionStatus.UNKNOWN and not self.unknown_id:
            raise ValueError("UNKNOWN lens questions require unknown_id")
        if self.status is LensQuestionStatus.NOT_APPLICABLE and not self.reason:
            raise ValueError("NOT_APPLICABLE lens questions require reason")
        return self


class Alternative(StrictModel):
    alternative_id: str = Field(pattern=SAFE_ID_PATTERN)
    alternative: str = Field(min_length=1)
    why_claim_ids: list[str] = Field(default_factory=list)
    why_unknown_ids: list[str] = Field(default_factory=list)
    reason_claim_ids: list[str] = Field(default_factory=list)
    reason_unknown_ids: list[str] = Field(default_factory=list)


class AnalystReport(StrictModel):
    run_id: str = Field(pattern=r"^run-[0-9a-f]{32}$")
    schema_version: str = Field(min_length=1)
    producer_id: str = Field(pattern=SAFE_ID_PATTERN)
    lens_id: str = Field(pattern=SAFE_ID_PATTERN)
    checklist: list[LensQuestion] = Field(min_length=1)
    claims: list[ClaimCandidate] = Field(default_factory=list)
    alternatives: list[Alternative] = Field(default_factory=list)
    evidence_gaps: list[EvidenceGap] = Field(default_factory=list)
    test_proposals: list[TestProposal] = Field(default_factory=list)


class DisputeProposal(StrictModel):
    dispute_id: str = Field(pattern=SAFE_ID_PATTERN)
    claim_refs: list[str] = Field(min_length=1)
    evidence_refs: list[str] = Field(default_factory=list)
    reason: str = Field(min_length=1)
    reason_claim_refs: list[str] = Field(default_factory=list)
    unknown_refs: list[str] = Field(default_factory=list)


class DebateArgument(StrictModel):
    run_id: str = Field(pattern=r"^run-[0-9a-f]{32}$")
    producer_id: str = Field(pattern=SAFE_ID_PATTERN)
    position: Literal["support", "oppose"]
    round_number: int = Field(ge=1)
    argument: str = Field(min_length=1)
    claim_refs: list[str] = Field(default_factory=list)
    unknown_refs: list[str] = Field(default_factory=list)
    dispute_proposals: list[DisputeProposal] = Field(default_factory=list)


class DebateRound(StrictModel):
    round_number: int = Field(ge=1)
    support: DebateArgument
    oppose: DebateArgument


class DebateOutput(StrictModel):
    run_id: str = Field(pattern=r"^run-[0-9a-f]{32}$")
    rounds: list[DebateRound] = Field(min_length=1)
    agreement_claim_refs: list[str] = Field(default_factory=list)
    disagreement_claim_refs: list[str] = Field(default_factory=list)
    unresolved_unknown_refs: list[str] = Field(default_factory=list)


class DebateSummary(StrictModel):
    agreement_claim_refs: list[str] = Field(default_factory=list)
    disagreement_claim_refs: list[str] = Field(default_factory=list)
    unresolved_unknown_refs: list[str] = Field(default_factory=list)


class LinkedStatement(StrictModel):
    statement: str = Field(min_length=1)
    claim_refs: list[str] = Field(default_factory=list)
    unknown_refs: list[str] = Field(default_factory=list)


class ResearchManagerOutput(StrictModel):
    run_id: str = Field(pattern=r"^run-[0-9a-f]{32}$")
    thesis: LinkedStatement
    strongest_counterexample: LinkedStatement
    invalidation_conditions: list[LinkedStatement] = Field(default_factory=list)
    evidence_gaps: list[EvidenceGap] = Field(default_factory=list)
    alternatives: list[Alternative] = Field(default_factory=list)
    candidate_claim_ids: list[str] = Field(default_factory=list)
    candidate_gap_ids: list[str] = Field(default_factory=list)
    test_proposals: list[TestProposal] = Field(default_factory=list)


class CostEstimate(StrictModel):
    amount: Decimal = Field(ge=Decimal("0"))
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    user_minutes: int | None = Field(default=None, ge=0)
    note: str | None = None


class TestProposal(StrictModel):
    test_key: str = Field(pattern=SAFE_ID_PATTERN)
    title: str = Field(min_length=1)
    assumption: str = Field(min_length=1)
    claim_ids: list[str] = Field(default_factory=list)
    gap_ids: list[str] = Field(default_factory=list)
    impact_if_false: ImpactIfFalse
    discriminating_test: str | None = None
    criterion: str | None = None
    target_or_sample: str | None = None
    owner: str | None = None
    deadline: date | None = None
    estimated_cost: CostEstimate | None = None
    proposed_priority: Priority | None = None
    supersedes_test_id: str | None = Field(default=None, pattern=SAFE_ID_PATTERN)


class TestConfirmation(StrictModel):
    test_id: str = Field(pattern=SAFE_ID_PATTERN)
    run_id: str = Field(pattern=r"^run-[0-9a-f]{32}$")
    confirmed_at: datetime
    confirmed_by: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_timestamp(self) -> TestConfirmation:
        if self.confirmed_at.tzinfo is None or self.confirmed_at.utcoffset() is None:
            raise ValueError("confirmed_at must include a timezone")
        return self


class TestResult(StrictModel):
    test_id: str = Field(pattern=SAFE_ID_PATTERN)
    run_id: str = Field(pattern=r"^run-[0-9a-f]{32}$")
    state: TestResultState
    recorded_at: datetime
    recorded_by: str = Field(min_length=1)
    observation: str = Field(min_length=1)
    result_evidence_refs: list[str] = Field(default_factory=list)
    actual_cost: CostEstimate | None = None

    @model_validator(mode="after")
    def validate_timestamp(self) -> TestResult:
        if self.recorded_at.tzinfo is None or self.recorded_at.utcoffset() is None:
            raise ValueError("recorded_at must include a timezone")
        return self


class LedgerRow(StrictModel):
    test_id: str = Field(pattern=SAFE_ID_PATTERN)
    priority: Priority
    state: LedgerState
    assumption: str = Field(min_length=1)
    claim_ids: list[str] = Field(default_factory=list)
    gap_ids: list[str] = Field(default_factory=list)
    provenance: Provenance
    grounding_status: GroundingStatus
    evidence_status: EvidenceStatus
    impact_if_false: ImpactIfFalse
    discriminating_test: str | None = None
    criterion: str | None = None
    target_or_sample: str | None = None
    owner: str | None = None
    deadline: date | None = None
    estimated_cost: CostEstimate | None = None
    proposed_priority: Priority | None = None
    supersedes_test_id: str | None = Field(default=None, pattern=SAFE_ID_PATTERN)


class RunMessage(StrictModel):
    stage: str = Field(min_length=1)
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    affected_ids: list[str] = Field(default_factory=list)
    retryable: bool = False
    resolved: bool = False


class StageRecord(StrictModel):
    stage: str = Field(min_length=1)
    status: Literal["PENDING", "COMPLETE", "PARTIAL", "BLOCKED", "UNAVAILABLE"]
    started_at: datetime | None = None
    completed_at: datetime | None = None
    artifact_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class Ledger(StrictModel):
    rows: list[LedgerRow] = Field(default_factory=list)
    appendix_rows: list[LedgerRow] = Field(default_factory=list)
    alternatives: list[Alternative] = Field(default_factory=list)
    evidence_gaps: list[EvidenceGap] = Field(default_factory=list)


class RunArtifact(StrictModel):
    schema_version: str = Field(min_length=1)
    run_id: str = Field(pattern=r"^run-[0-9a-f]{32}$")
    idea_id: str = Field(pattern=SAFE_ID_PATTERN)
    input_snapshot_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    evaluated_at: datetime
    execution_config: ExecutionConfig | None = None
    execution_config_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    run_status: RunStatus
    context: EvaluationContext
    claims: list[RegisteredClaim] = Field(default_factory=list)
    disputes: list[Dispute] = Field(default_factory=list)
    evidence_gaps: list[EvidenceGap] = Field(default_factory=list)
    debate: DebateOutput | None = None
    adjudication: ResearchManagerOutput | None = None
    ledger: Ledger | None = None
    stages: list[StageRecord] = Field(default_factory=list)
    errors: list[RunMessage] = Field(default_factory=list)
    warnings: list[RunMessage] = Field(default_factory=list)
    model_metadata: list[dict[str, str | int | float | None]] = Field(default_factory=list)
    pipeline_version: str = Field(min_length=1)
    integrity_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_identity(self) -> RunArtifact:
        if self.run_status is RunStatus.REJECTED:
            raise ValueError(
                "REJECTED is a preflight outcome and cannot be persisted as a run"
            )
        if self.context.run_id != self.run_id:
            raise ValueError("run artifact run_id must match context.run_id")
        if self.context.idea_id != self.idea_id:
            raise ValueError("run artifact idea_id must match context.idea_id")
        if self.context.input_snapshot_id != self.input_snapshot_id:
            raise ValueError(
                "run artifact input_snapshot_id must match context.input_snapshot_id"
            )
        if (self.execution_config is None) != (self.execution_config_hash is None):
            raise ValueError(
                "execution_config and execution_config_hash must be provided together"
            )
        if (
            self.execution_config is not None
            and self.execution_config_hash != sha256_hex(self.execution_config)
        ):
            raise ValueError("execution_config_hash does not match execution_config")
        return self


# These models refer to TestProposal, which is intentionally declared later so
# the cost contract stays close to the test contract.  Resolve the references
# once the module has defined every type.
AnalystReport.model_rebuild()
ResearchManagerOutput.model_rebuild()
