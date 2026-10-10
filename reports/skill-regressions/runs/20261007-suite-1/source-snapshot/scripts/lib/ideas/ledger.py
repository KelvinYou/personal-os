"""Deterministic assumption-ledger gate and validation-test ordering."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Sequence

from .canonical import sha256_hex
from .models import (
    CostEstimate,
    EvidenceGap,
    EvidenceStatus,
    EvaluationContext,
    GroundingStatus,
    ImpactIfFalse,
    Ledger,
    LedgerRow,
    LedgerState,
    Priority,
    Provenance,
    RunMessage,
    TestProposal,
)
from .registry import EVIDENCE_PRECEDENCE, GROUNDING_PRECEDENCE, RegistryResult


DEFAULT_MAX_TOP_ROWS = 5
_IMPACT_RANK = {
    ImpactIfFalse.FATAL: 0,
    ImpactIfFalse.MAJOR: 1,
    ImpactIfFalse.MINOR: 2,
    ImpactIfFalse.UNKNOWN: 3,
}
_STATE_RANK = {
    LedgerState.EVIDENCE_BLOCKED: 0,
    LedgerState.PROVISIONAL: 1,
    LedgerState.CONFLICTED: 2,
    LedgerState.INCONCLUSIVE: 3,
    LedgerState.NOT_RUN: 4,
    LedgerState.FALSIFIED: 5,
    LedgerState.VALIDATED: 6,
    LedgerState.UNPRIORITIZED: 7,
}


@dataclass
class LedgerBuildResult:
    ledger: Ledger
    errors: list[RunMessage] = field(default_factory=list)
    warnings: list[RunMessage] = field(default_factory=list)


def _message(code: str, message: str, affected: Sequence[str] = ()) -> RunMessage:
    return RunMessage(
        stage="ledger",
        code=code,
        message=message,
        affected_ids=list(affected),
        retryable=False,
    )


def _test_id(context: EvaluationContext, proposal: TestProposal) -> str:
    payload = proposal.model_dump(
        mode="json", exclude={"test_key", "proposed_priority"}
    )
    payload["idea_id"] = context.idea_id
    return f"test-{sha256_hex(payload)[:16]}"


def _claim_qualification(
    claim_ids: Sequence[str],
    gap_ids: Sequence[str],
    registry: RegistryResult,
) -> tuple[Provenance, GroundingStatus, EvidenceStatus]:
    claims_by_id = {claim.claim_id: claim for claim in registry.claims}
    claims = [claims_by_id[claim_id] for claim_id in claim_ids if claim_id in claims_by_id]
    evidence_statuses = [claim.evidence_status for claim in claims]
    grounding_statuses = [claim.grounding_status for claim in claims]
    if gap_ids:
        evidence_statuses.append(EvidenceStatus.MISSING)
        grounding_statuses.append(GroundingStatus.UNRESOLVED)

    if not evidence_statuses:
        return Provenance.NOT_APPLICABLE, GroundingStatus.UNRESOLVED, EvidenceStatus.MISSING

    evidence_status = max(evidence_statuses, key=EVIDENCE_PRECEDENCE.__getitem__)
    grounding_status = max(grounding_statuses, key=GROUNDING_PRECEDENCE.__getitem__)
    provenances = {claim.provenance for claim in claims}
    provenance = provenances.pop() if len(provenances) == 1 else Provenance.NOT_APPLICABLE
    if gap_ids:
        provenance = Provenance.NOT_APPLICABLE if not claims else provenance
    return provenance, grounding_status, evidence_status


def _complete_contract(proposal: TestProposal, claim_ids: Sequence[str], gap_ids: Sequence[str]) -> bool:
    return bool(
        (claim_ids or gap_ids)
        and proposal.impact_if_false is not ImpactIfFalse.UNKNOWN
        and proposal.discriminating_test
        and proposal.criterion
        and proposal.target_or_sample
        and proposal.owner
        and proposal.deadline
        and proposal.estimated_cost is not None
    )


def _priority(proposal: TestProposal, complete: bool) -> Priority:
    if not complete or proposal.impact_if_false is ImpactIfFalse.UNKNOWN:
        return Priority.UNPRIORITIZED
    if proposal.impact_if_false is ImpactIfFalse.FATAL:
        return Priority.P0
    if proposal.impact_if_false is ImpactIfFalse.MAJOR:
        return Priority.P1
    return Priority.P2


def _cost_sort_key(cost: CostEstimate | None, currencies: set[str]) -> tuple[int, object, int]:
    if cost is None or len(currencies) != 1:
        return (1, "", 0)
    user_minutes = cost.user_minutes if cost.user_minutes is not None else 10**9
    return (0, cost.amount, user_minutes)


def build_ledger(
    context: EvaluationContext,
    registry: RegistryResult,
    proposals: Sequence[TestProposal],
    *,
    alternatives=(),
    evidence_gaps: Sequence[EvidenceGap] | None = None,
    max_top_rows: int = DEFAULT_MAX_TOP_ROWS,
    prior_test_ids: Sequence[str] = (),
) -> LedgerBuildResult:
    """Validate proposals, assign deterministic IDs, and order the queue."""
    if max_top_rows < 1:
        raise ValueError("max_top_rows must be positive")

    claims_by_id = {claim.claim_id: claim for claim in registry.claims}
    gaps_by_id = {gap.gap_id: gap for gap in (evidence_gaps or registry.evidence_gaps)}
    currencies = {
        proposal.estimated_cost.currency
        for proposal in proposals
        if proposal.estimated_cost is not None
    }
    result = LedgerBuildResult(ledger=Ledger())
    rows: list[LedgerRow] = []
    seen_test_ids: set[str] = set()
    prior_test_id_set = set(prior_test_ids)

    for proposal in proposals:
        test_id = _test_id(context, proposal)
        if test_id in seen_test_ids:
            result.errors.append(_message("DUPLICATE_TEST", f"duplicate test contract: {test_id}", [test_id]))
            continue
        seen_test_ids.add(test_id)

        invalid_supersedes = (
            proposal.supersedes_test_id is not None
            and proposal.supersedes_test_id not in prior_test_id_set
        )
        if invalid_supersedes:
            result.errors.append(
                _message(
                    "SUPERSEDES_TEST_REFERENCE",
                    f"test {test_id} supersedes a test that is not present in an older run for this idea",
                    [test_id, proposal.supersedes_test_id or ""],
                )
            )

        valid_claim_ids = [claim_id for claim_id in proposal.claim_ids if claim_id in claims_by_id]
        valid_gap_ids = [gap_id for gap_id in proposal.gap_ids if gap_id in gaps_by_id]
        invalid_claims = sorted(set(proposal.claim_ids) - set(valid_claim_ids))
        invalid_gaps = sorted(set(proposal.gap_ids) - set(valid_gap_ids))
        if invalid_claims or invalid_gaps:
            result.errors.append(
                _message(
                    "INVALID_TEST_LINK",
                    f"test {test_id} has invalid claim/gap links",
                    [test_id, *invalid_claims, *invalid_gaps],
                )
            )

        complete = (
            _complete_contract(proposal, valid_claim_ids, valid_gap_ids)
            and not invalid_claims
            and not invalid_gaps
            and not invalid_supersedes
        )
        provenance, grounding_status, evidence_status = _claim_qualification(
            valid_claim_ids, valid_gap_ids, registry
        )
        if not complete:
            priority = Priority.UNPRIORITIZED
            state = LedgerState.UNPRIORITIZED
            result.warnings.append(
                _message(
                    "INCOMPLETE_TEST_CONTRACT",
                    f"test {test_id} is not executable until its links, impact, criterion, target, owner, deadline, and cost are complete",
                    [test_id],
                )
            )
        else:
            priority = _priority(proposal, complete)
            state = (
                LedgerState.PROVISIONAL
                if grounding_status is GroundingStatus.GROUNDED
                and evidence_status is EvidenceStatus.SUPPORTED
                else LedgerState.EVIDENCE_BLOCKED
            )

        rows.append(
            LedgerRow(
                test_id=test_id,
                priority=priority,
                state=state,
                assumption=proposal.assumption,
                claim_ids=valid_claim_ids,
                gap_ids=valid_gap_ids,
                provenance=provenance,
                grounding_status=grounding_status,
                evidence_status=evidence_status,
                impact_if_false=proposal.impact_if_false,
                discriminating_test=proposal.discriminating_test,
                criterion=proposal.criterion,
                target_or_sample=proposal.target_or_sample,
                owner=proposal.owner,
                deadline=proposal.deadline,
                estimated_cost=proposal.estimated_cost,
                proposed_priority=proposal.proposed_priority,
                supersedes_test_id=proposal.supersedes_test_id,
            )
        )

    if len(currencies) > 1:
        result.warnings.append(
            _message(
                "MIXED_COST_CURRENCIES",
                "test costs use multiple currencies; cost is not used as a cross-currency ordering signal",
            )
        )

    rows.sort(
        key=lambda row: (
            _IMPACT_RANK[row.impact_if_false],
            _STATE_RANK[row.state],
            row.deadline or date.max,
            _cost_sort_key(row.estimated_cost, currencies),
            row.test_id,
        )
    )
    top_candidates = [
        row for row in rows if row.priority is not Priority.UNPRIORITIZED
    ]
    top_rows = top_candidates[:max_top_rows]
    top_ids = {row.test_id for row in top_rows}
    result.ledger = Ledger(
        rows=top_rows,
        appendix_rows=[row for row in rows if row.test_id not in top_ids],
        alternatives=list(alternatives),
        evidence_gaps=list(evidence_gaps or registry.evidence_gaps),
    )
    return result
