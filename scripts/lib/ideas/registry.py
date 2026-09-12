"""Closed-world claim/evidence registry.

The registry is the only component allowed to assign provenance, grounding,
and evidence status.  Model output is treated as a proposal and invalid
objects are excluded with a structured validation message.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence

from .formulas import FormulaError, evaluate_formula
from .models import (
    AnalystReport,
    ClaimCandidate,
    ClaimKind,
    Dispute,
    EvidenceGap,
    EvidenceItem,
    EvidenceStatus,
    EvaluationContext,
    GroundingStatus,
    LensQuestionStatus,
    RegisteredClaim,
    RunMessage,
    Provenance,
    Alternative,
    DebateOutput,
    ResearchManagerOutput,
)


EVIDENCE_PRECEDENCE = {
    EvidenceStatus.SUPPORTED: 0,
    EvidenceStatus.NOT_APPLICABLE: 1,
    EvidenceStatus.STALE: 2,
    EvidenceStatus.FRESHNESS_UNKNOWN: 3,
    EvidenceStatus.MISSING: 4,
    EvidenceStatus.CONFLICTED: 5,
}

GROUNDING_PRECEDENCE = {
    GroundingStatus.GROUNDED: 0,
    GroundingStatus.ASSUMPTION_DEPENDENT: 1,
    GroundingStatus.MODEL_DEPENDENT: 2,
    GroundingStatus.UNRESOLVED: 3,
}


def _duplicates(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return sorted(duplicates)


@dataclass(frozen=True)
class _CandidateRecord:
    claim_id: str
    producer_id: str
    candidate: ClaimCandidate


@dataclass
class RegistryResult:
    claims: list[RegisteredClaim] = field(default_factory=list)
    disputes: list[Dispute] = field(default_factory=list)
    evidence_gaps: list[EvidenceGap] = field(default_factory=list)
    errors: list[RunMessage] = field(default_factory=list)
    warnings: list[RunMessage] = field(default_factory=list)


def _message(code: str, message: str, affected: Iterable[str] = ()) -> RunMessage:
    return RunMessage(
        stage="registry",
        code=code,
        message=message,
        affected_ids=list(affected),
        retryable=True,
    )


def _claim_id(producer_id: str, candidate_key: str) -> str:
    return f"claim-{producer_id}-{candidate_key}"


def _resolve_ref(
    reference: str,
    *,
    canonical_ids: set[str],
    aliases: Mapping[str, str],
) -> str | None:
    if reference in canonical_ids:
        return reference
    return aliases.get(reference)


def _freshness_status(item: EvidenceItem, as_of) -> EvidenceStatus:
    if item.observed_or_effective_at == "unknown":
        return EvidenceStatus.FRESHNESS_UNKNOWN
    if item.temporal_status.value in {"forecast", "planned"}:
        return EvidenceStatus.FRESHNESS_UNKNOWN
    if item.freshness_window == "not_applicable":
        return EvidenceStatus.SUPPORTED
    age_days = (as_of - item.observed_or_effective_at).days
    if age_days < 0:
        return EvidenceStatus.FRESHNESS_UNKNOWN
    if age_days > item.freshness_window:
        return EvidenceStatus.STALE
    return EvidenceStatus.SUPPORTED


def _worst_evidence(statuses: Iterable[EvidenceStatus]) -> EvidenceStatus:
    statuses = list(statuses)
    if not statuses:
        return EvidenceStatus.NOT_APPLICABLE
    return max(statuses, key=EVIDENCE_PRECEDENCE.__getitem__)


def _worst_grounding(statuses: Iterable[GroundingStatus]) -> GroundingStatus:
    statuses = list(statuses)
    if not statuses:
        return GroundingStatus.UNRESOLVED
    return max(statuses, key=GROUNDING_PRECEDENCE.__getitem__)


def _basis(candidate: ClaimCandidate) -> list[str]:
    choices = {
        "evidence_refs": candidate.evidence_refs,
        "context_refs": candidate.context_refs,
        "user_assumption_refs": candidate.user_assumption_refs,
        "derivation_refs": candidate.derivation_refs,
    }
    return [name for name, refs in choices.items() if refs]


def _validate_report_header(context: EvaluationContext, report: AnalystReport, result: RegistryResult) -> bool:
    if report.run_id != context.run_id:
        result.errors.append(
            _message("RUN_ID_MISMATCH", f"{report.producer_id} report belongs to another run", [report.producer_id])
        )
        return False
    if report.schema_version != context.pipeline_version:
        result.errors.append(
            _message(
                "SCHEMA_VERSION_MISMATCH",
                f"{report.producer_id} report schema {report.schema_version} does not match pipeline {context.pipeline_version}",
                [report.producer_id],
            )
        )
        return False
    return True


def _validate_candidate_shape(
    candidate: ClaimCandidate,
    *,
    producer_id: str,
    context: EvaluationContext,
    known_disputes: set[str],
    prior_claim_ids: set[str],
    result: RegistryResult,
) -> bool:
    basis = _basis(candidate)
    if len(basis) > 1:
        result.errors.append(
            _message(
                "MIXED_BASIS",
                f"claim {candidate.candidate_key} uses multiple provenance bases",
                [candidate.candidate_key],
            )
        )
        return False
    if not basis and candidate.claim_kind is not ClaimKind.HYPOTHESIS:
        result.errors.append(
            _message(
                "UNMARKED_GUESS",
                f"claim {candidate.candidate_key} has no reference and is not a hypothesis",
                [candidate.candidate_key],
            )
        )
        return False
    if candidate.claim_kind is ClaimKind.DERIVED:
        if not candidate.derivation_refs or candidate.formula is None:
            result.errors.append(
                _message(
                    "INVALID_DERIVATION",
                    f"derived claim {candidate.candidate_key} requires derivation_refs and formula",
                    [candidate.candidate_key],
                )
            )
            return False
        if candidate.quantity is not None:
            result.errors.append(
                _message(
                    "DERIVED_QUANTITY_OVERRIDE",
                    f"derived claim {candidate.candidate_key} cannot provide a model-computed quantity",
                    [candidate.candidate_key],
                )
            )
            return False
        if set(candidate.formula.operands) != set(candidate.derivation_refs):
            result.errors.append(
                _message(
                    "FORMULA_REFERENCE_MISMATCH",
                    f"derived claim {candidate.candidate_key} formula operands must match derivation_refs",
                    [candidate.candidate_key],
                )
            )
            return False
    elif candidate.formula is not None:
        result.errors.append(
            _message(
                "UNEXPECTED_FORMULA",
                f"non-derived claim {candidate.candidate_key} cannot carry a formula",
                [candidate.candidate_key],
            )
        )
        return False
    if candidate.supersedes_claim_id is not None and candidate.supersedes_claim_id not in prior_claim_ids:
        result.errors.append(
            _message(
                "SUPERSEDES_CLAIM_REFERENCE",
                f"claim {candidate.candidate_key} supersedes a claim that is not an older run for this idea",
                [candidate.candidate_key, candidate.supersedes_claim_id],
            )
        )
        return False

    context_ids = {field.context_ref for field in context.context_fields}
    assumption_ids = {
        assumption.user_assumption_id for assumption in context.user_assumptions
    }
    evidence_by_id = {item.evidence_id: item for item in context.evidence}
    unknown_ids = {unknown.unknown_id for unknown in context.unknowns}
    checks = (
        (candidate.context_refs, context_ids, "CONTEXT_REFERENCE"),
        (candidate.user_assumption_refs, assumption_ids, "ASSUMPTION_REFERENCE"),
        (candidate.evidence_refs, set(evidence_by_id), "EVIDENCE_REFERENCE"),
        (candidate.unknown_refs, unknown_ids, "UNKNOWN_REFERENCE"),
        (candidate.dispute_refs, known_disputes, "DISPUTE_REFERENCE"),
    )
    for refs, known, code in checks:
        missing = sorted(set(refs) - known)
        if missing:
            result.errors.append(
                _message(
                    code,
                    f"claim {candidate.candidate_key} references unknown IDs: {', '.join(missing)}",
                    [candidate.candidate_key, *missing],
                )
            )
            return False
    if any(evidence_by_id[ref].model_processing.value == "excluded" for ref in candidate.evidence_refs):
        result.errors.append(
            _message(
                "EXCLUDED_EVIDENCE",
                f"claim {candidate.candidate_key} cites evidence excluded from model processing",
                [candidate.candidate_key],
            )
        )
        return False
    return True


def _validate_gap(
    gap: EvidenceGap,
    *,
    context: EvaluationContext,
    canonical_ids: set[str],
    aliases: Mapping[str, str],
    result: RegistryResult,
) -> EvidenceGap | None:
    unknown_ids = {unknown.unknown_id for unknown in context.unknowns}
    missing_unknowns = sorted(set(gap.unknown_ids) - unknown_ids)
    if missing_unknowns:
        result.errors.append(
            _message("UNKNOWN_REFERENCE", f"gap {gap.gap_id} references unknown IDs: {', '.join(missing_unknowns)}", [gap.gap_id, *missing_unknowns])
        )
        return None
    resolved_claims: list[str] = []
    for reference in gap.affected_claim_ids:
        resolved = _resolve_ref(reference, canonical_ids=canonical_ids, aliases=aliases)
        if resolved is None:
            result.errors.append(
                _message("CLAIM_REFERENCE", f"gap {gap.gap_id} references unknown claim {reference}", [gap.gap_id, reference])
            )
            return None
        resolved_claims.append(resolved)
    return gap.model_copy(update={"affected_claim_ids": resolved_claims})


def _validate_dispute(
    dispute: Dispute,
    *,
    context: EvaluationContext,
    canonical_ids: set[str],
    aliases: Mapping[str, str],
    result: RegistryResult,
) -> Dispute | None:
    resolved_claims: list[str] = []
    for reference in dispute.claim_refs:
        resolved = _resolve_ref(reference, canonical_ids=canonical_ids, aliases=aliases)
        if resolved is None:
            result.errors.append(_message("CLAIM_REFERENCE", f"dispute {dispute.dispute_id} references unknown claim {reference}", [dispute.dispute_id, reference]))
            return None
        resolved_claims.append(resolved)
    evidence_ids = {item.evidence_id for item in context.evidence}
    missing_evidence = sorted(set(dispute.evidence_refs) - evidence_ids)
    if missing_evidence:
        result.errors.append(_message("EVIDENCE_REFERENCE", f"dispute {dispute.dispute_id} references unknown evidence: {', '.join(missing_evidence)}", [dispute.dispute_id, *missing_evidence]))
        return None
    excluded_evidence = sorted(
        evidence_id
        for evidence_id in dispute.evidence_refs
        if next(item for item in context.evidence if item.evidence_id == evidence_id).model_processing.value
        == "excluded"
    )
    if excluded_evidence:
        result.errors.append(
            _message(
                "EXCLUDED_EVIDENCE",
                f"dispute {dispute.dispute_id} cites evidence excluded from model processing: {', '.join(excluded_evidence)}",
                [dispute.dispute_id, *excluded_evidence],
            )
        )
        return None
    reason_claims: list[str] = []
    for reference in dispute.reason_claim_refs:
        resolved = _resolve_ref(reference, canonical_ids=canonical_ids, aliases=aliases)
        if resolved is None:
            result.errors.append(_message("CLAIM_REFERENCE", f"dispute {dispute.dispute_id} has an unknown reason claim {reference}", [dispute.dispute_id, reference]))
            return None
        reason_claims.append(resolved)
    unknown_ids = {unknown.unknown_id for unknown in context.unknowns}
    missing_unknowns = sorted(set(dispute.unknown_refs) - unknown_ids)
    if missing_unknowns:
        result.errors.append(_message("UNKNOWN_REFERENCE", f"dispute {dispute.dispute_id} references unknown IDs: {', '.join(missing_unknowns)}", [dispute.dispute_id, *missing_unknowns]))
        return None
    if not reason_claims and not dispute.unknown_refs:
        result.errors.append(_message("UNLINKED_DISPUTE_REASON", f"dispute {dispute.dispute_id} must link its reason to a claim or unknown", [dispute.dispute_id]))
        return None
    return dispute.model_copy(update={"claim_refs": resolved_claims, "reason_claim_refs": reason_claims})


def register_reports(
    context: EvaluationContext,
    reports: Sequence[AnalystReport],
    *,
    disputes: Sequence[Dispute] = (),
    prior_claim_ids: Sequence[str] = (),
) -> RegistryResult:
    """Register analyst claims and return a closed-world canonical graph."""
    result = RegistryResult()
    evidence_by_id = {item.evidence_id: item for item in context.evidence}
    known_disputes = {dispute.dispute_id for dispute in disputes}
    if len(known_disputes) != len(disputes):
        result.errors.append(_message("DUPLICATE_DISPUTE", "dispute IDs must be unique"))

    candidates: list[_CandidateRecord] = []
    aliases: dict[str, str] = {}
    alias_collisions: set[str] = set()
    claim_ids: set[str] = set()
    for report in reports:
        if not _validate_report_header(context, report, result):
            continue
        candidate_keys = [candidate.candidate_key for candidate in report.claims]
        duplicate_keys = _duplicates(candidate_keys)
        if duplicate_keys:
            result.errors.append(_message("DUPLICATE_CLAIM", f"{report.producer_id} has duplicate candidate keys: {', '.join(duplicate_keys)}", [report.producer_id, *duplicate_keys]))
        for candidate in report.claims:
            claim_id = _claim_id(report.producer_id, candidate.candidate_key)
            if claim_id in claim_ids:
                result.errors.append(_message("DUPLICATE_CLAIM", f"canonical claim ID already exists: {claim_id}", [claim_id]))
                continue
            if not _validate_candidate_shape(
                candidate,
                producer_id=report.producer_id,
                context=context,
                known_disputes=known_disputes,
                prior_claim_ids=set(prior_claim_ids),
                result=result,
            ):
                continue
            claim_ids.add(claim_id)
            candidates.append(_CandidateRecord(claim_id, report.producer_id, candidate))
            qualified = f"{report.producer_id}:{candidate.candidate_key}"
            aliases[qualified] = claim_id
            if candidate.candidate_key in aliases and aliases[candidate.candidate_key] != claim_id:
                alias_collisions.add(candidate.candidate_key)
            else:
                aliases[candidate.candidate_key] = claim_id
    for collision in alias_collisions:
        aliases.pop(collision, None)

    by_id = {record.claim_id: record for record in candidates}
    dependency_map: dict[str, list[str]] = {}
    valid_records: list[_CandidateRecord] = []
    for record in candidates:
        dependencies: list[str] = []
        for reference in record.candidate.derivation_refs:
            resolved = _resolve_ref(reference, canonical_ids=set(by_id), aliases=aliases)
            if resolved is None:
                result.errors.append(_message("DERIVATION_REFERENCE", f"claim {record.claim_id} references unknown derivation {reference}", [record.claim_id, reference]))
                break
            dependencies.append(resolved)
        else:
            dependency_map[record.claim_id] = dependencies
            valid_records.append(record)

    state: dict[str, RegisteredClaim] = {}
    visiting: set[str] = set()
    conflicted_claims: set[str] = set()

    def visit(claim_id: str) -> RegisteredClaim | None:
        if claim_id in state:
            return state[claim_id]
        if claim_id in visiting:
            result.errors.append(_message("DERIVATION_CYCLE", f"derivation cycle reaches {claim_id}", [claim_id]))
            return None
        record = by_id.get(claim_id)
        if record is None or record not in valid_records:
            return None
        visiting.add(claim_id)
        candidate = record.candidate
        basis = _basis(candidate)
        quantity = candidate.quantity
        if candidate.derivation_refs:
            dependencies = [visit(dep) for dep in dependency_map.get(claim_id, [])]
            if any(dependency is None for dependency in dependencies):
                visiting.remove(claim_id)
                result.errors.append(_message("DERIVATION_INPUT", f"claim {claim_id} has an unavailable derivation input", [claim_id]))
                return None
            resolved_dependencies = [dependency for dependency in dependencies if dependency is not None]
            if any(dependency.quantity is None for dependency in resolved_dependencies):
                visiting.remove(claim_id)
                result.errors.append(_message("FORMULA_INPUT_MISSING", f"claim {claim_id} formula input has no quantity", [claim_id]))
                return None
            assert candidate.formula is not None
            quantities = {
                reference: dependency.quantity
                for reference, dependency in zip(
                    candidate.derivation_refs, resolved_dependencies
                )
                if dependency.quantity is not None
            }
            try:
                quantity = evaluate_formula(candidate.formula, quantities)
            except FormulaError as exc:
                visiting.remove(claim_id)
                result.errors.append(_message("INVALID_FORMULA", f"claim {claim_id}: {exc}", [claim_id]))
                return None
            evidence_status = _worst_evidence(dependency.evidence_status for dependency in resolved_dependencies)
            grounding_status = _worst_grounding(dependency.grounding_status for dependency in resolved_dependencies)
            provenance = Provenance.DERIVED
        elif candidate.evidence_refs:
            evidence_status = _worst_evidence(
                _freshness_status(evidence_by_id[ref], context.as_of)
                for ref in candidate.evidence_refs
            )
            grounding_status = (
                GroundingStatus.GROUNDED
                if evidence_status is EvidenceStatus.SUPPORTED
                else GroundingStatus.UNRESOLVED
            )
            provenance = Provenance.CITED
        elif candidate.context_refs or candidate.user_assumption_refs:
            evidence_status = EvidenceStatus.NOT_APPLICABLE
            grounding_status = GroundingStatus.ASSUMPTION_DEPENDENT
            provenance = Provenance.USER_ASSUMED
        else:
            evidence_status = EvidenceStatus.MISSING
            grounding_status = GroundingStatus.MODEL_DEPENDENT
            provenance = Provenance.MODEL_GUESSED

        if candidate.unknown_refs:
            grounding_status = GroundingStatus.UNRESOLVED

        registered = RegisteredClaim(
            claim_id=claim_id,
            producer_id=record.producer_id,
            candidate_key=candidate.candidate_key,
            statement=candidate.statement,
            evidence_refs=list(candidate.evidence_refs),
            context_refs=list(candidate.context_refs),
            user_assumption_refs=list(candidate.user_assumption_refs),
            derivation_refs=list(dependency_map.get(claim_id, [])),
            unknown_refs=list(candidate.unknown_refs),
            dispute_refs=list(candidate.dispute_refs),
            claim_kind=candidate.claim_kind,
            provenance=provenance,
            evidence_status=evidence_status,
            grounding_status=grounding_status,
            quantity=quantity,
            formula=candidate.formula,
            supersedes_claim_id=candidate.supersedes_claim_id,
        )
        state[claim_id] = registered
        visiting.remove(claim_id)
        return registered

    for record in valid_records:
        visit(record.claim_id)

    validated_disputes: list[Dispute] = []
    seen_disputes: set[str] = set()
    for dispute in disputes:
        if dispute.dispute_id in seen_disputes:
            continue
        seen_disputes.add(dispute.dispute_id)
        validated = _validate_dispute(dispute, context=context, canonical_ids=set(state), aliases=aliases, result=result)
        if validated is not None:
            validated_disputes.append(validated)
            conflicted_claims.update(validated.claim_refs)
            for claim in state.values():
                if set(claim.evidence_refs) & set(validated.evidence_refs):
                    conflicted_claims.add(claim.claim_id)

            for claim in state.values():
                if dispute.dispute_id in claim.dispute_refs:
                    conflicted_claims.add(claim.claim_id)

    # Conflict propagates through derived claims.
    changed = True
    while changed:
        changed = False
        for claim in state.values():
            if claim.claim_id in conflicted_claims:
                continue
            if set(claim.derivation_refs) & conflicted_claims:
                conflicted_claims.add(claim.claim_id)
                changed = True
    for claim_id in conflicted_claims:
        claim = state.get(claim_id)
        if claim is not None:
            state[claim_id] = claim.model_copy(
                update={
                    "evidence_status": EvidenceStatus.CONFLICTED,
                    "grounding_status": GroundingStatus.UNRESOLVED,
                }
            )

    result.claims = [state[record.claim_id] for record in valid_records if record.claim_id in state]
    result.disputes = validated_disputes

    for report in reports:
        for question in report.checklist:
            if question.status is LensQuestionStatus.ADDRESSED:
                missing = [
                    reference
                    for reference in question.claim_ids
                    if _resolve_ref(
                        reference,
                        canonical_ids=set(state),
                        aliases=aliases,
                    )
                    is None
                ]
                if missing:
                    result.errors.append(
                        _message(
                            "CHECKLIST_CLAIM_REFERENCE",
                            f"checklist question {question.question_id} references unknown claims: {', '.join(missing)}",
                            [question.question_id, *missing],
                        )
                    )
            elif question.status is LensQuestionStatus.UNKNOWN:
                if question.unknown_id not in {
                    unknown.unknown_id for unknown in context.unknowns
                }:
                    result.errors.append(
                        _message(
                            "CHECKLIST_UNKNOWN_REFERENCE",
                            f"checklist question {question.question_id} references an unknown unknown",
                            [question.question_id, question.unknown_id or ""],
                        )
                    )

    seen_gaps: set[str] = set()
    for report in reports:
        for gap in report.evidence_gaps:
            if gap.gap_id in seen_gaps:
                result.errors.append(_message("DUPLICATE_GAP", f"duplicate evidence gap: {gap.gap_id}", [gap.gap_id]))
                continue
            seen_gaps.add(gap.gap_id)
            validated_gap = _validate_gap(gap, context=context, canonical_ids=set(state), aliases=aliases, result=result)
            if validated_gap is not None:
                result.evidence_gaps.append(validated_gap)

    return result


def validate_checklists(
    reports: Sequence[AnalystReport],
    required_question_ids: Mapping[str, Sequence[str]],
) -> list[RunMessage]:
    """Ensure each configured lens answers every required question exactly once."""
    errors: list[RunMessage] = []
    for report in reports:
        errors.extend(_checklist_errors(report, required_question_ids))
    return errors


def _checklist_errors(
    report: AnalystReport,
    required_question_ids: Mapping[str, Sequence[str]],
) -> list[RunMessage]:
    errors: list[RunMessage] = []
    if report.lens_id not in required_question_ids:
        return [
            _message(
                "CHECKLIST_LENS",
                f"lens {report.lens_id} is not configured for this run",
                [report.lens_id],
            )
        ]

    required = set(required_question_ids[report.lens_id])
    actual = [question.question_id for question in report.checklist]
    duplicates = _duplicates(actual)
    if duplicates:
        errors.append(
            _message(
                "DUPLICATE_CHECKLIST",
                f"lens {report.lens_id} repeats question IDs: {', '.join(duplicates)}",
                [report.lens_id, *duplicates],
            )
        )
    if set(actual) != required:
        missing = sorted(required - set(actual))
        extra = sorted(set(actual) - required)
        detail = []
        if missing:
            detail.append(f"missing={','.join(missing)}")
        if extra:
            detail.append(f"extra={','.join(extra)}")
        errors.append(
            _message(
                "CHECKLIST_COVERAGE",
                f"lens {report.lens_id} checklist mismatch ({'; '.join(detail)})",
                [report.lens_id, *missing, *extra],
            )
        )
    for question in report.checklist:
        if question.status is LensQuestionStatus.ADDRESSED and not question.claim_ids:
            errors.append(
                _message(
                    "CHECKLIST_LINK",
                    f"addressed question {question.question_id} has no claim IDs",
                    [report.lens_id, question.question_id],
                )
            )
    return errors


def filter_valid_checklist_reports(
    reports: Sequence[AnalystReport],
    required_question_ids: Mapping[str, Sequence[str]],
) -> tuple[list[AnalystReport], list[RunMessage]]:
    """Return only reports that passed closed-world checklist validation.

    Checklist errors are not advisory: an invalid report must not contribute
    claims, gaps, or downstream test proposals to the registry.
    """
    valid_reports: list[AnalystReport] = []
    errors: list[RunMessage] = []
    for report in reports:
        report_errors = _checklist_errors(report, required_question_ids)
        errors.extend(report_errors)
        if not report_errors:
            valid_reports.append(report)
    return valid_reports, errors


def _validate_claim_and_unknown_links(
    *,
    claim_refs: Sequence[str],
    unknown_refs: Sequence[str],
    claim_ids: set[str],
    unknown_ids: set[str],
    stage: str,
    label: str,
) -> list[RunMessage]:
    errors: list[RunMessage] = []
    missing_claims = sorted(set(claim_refs) - claim_ids)
    missing_unknowns = sorted(set(unknown_refs) - unknown_ids)
    if missing_claims:
        errors.append(
            RunMessage(
                stage=stage,
                code="CLAIM_REFERENCE",
                message=f"{label} references unknown claims: {', '.join(missing_claims)}",
                affected_ids=[label, *missing_claims],
            )
        )
    if missing_unknowns:
        errors.append(
            RunMessage(
                stage=stage,
                code="UNKNOWN_REFERENCE",
                message=f"{label} references unknown unknowns: {', '.join(missing_unknowns)}",
                affected_ids=[label, *missing_unknowns],
            )
        )
    if not claim_refs and not unknown_refs:
        errors.append(
            RunMessage(
                stage=stage,
                code="UNLINKED_STATEMENT",
                message=f"{label} must link to a claim or unknown",
                affected_ids=[label],
            )
        )
    return errors


def validate_debate_output(
    context: EvaluationContext,
    registry: RegistryResult,
    debate: DebateOutput,
) -> list[RunMessage]:
    """Validate the debate's closed-world references without adjudicating it."""
    claims = {claim.claim_id for claim in registry.claims}
    unknowns = {unknown.unknown_id for unknown in context.unknowns}
    errors: list[RunMessage] = []
    if debate.run_id != context.run_id:
        errors.append(_message("RUN_ID_MISMATCH", "debate output belongs to another run"))
    for round_ in debate.rounds:
        if round_.support.round_number != round_.round_number:
            errors.append(
                _message(
                    "ROUND_NUMBER_MISMATCH",
                    f"support argument round does not match round {round_.round_number}",
                    [f"support-{round_.round_number}"],
                )
            )
        if round_.oppose.round_number != round_.round_number:
            errors.append(
                _message(
                    "ROUND_NUMBER_MISMATCH",
                    f"oppose argument round does not match round {round_.round_number}",
                    [f"oppose-{round_.round_number}"],
                )
            )
        if round_.support.position != "support" or round_.oppose.position != "oppose":
            errors.append(
                _message(
                    "POSITION_MISMATCH",
                    f"round {round_.round_number} must contain support and oppose arguments",
                    [str(round_.round_number)],
                )
            )
        for argument in (round_.support, round_.oppose):
            errors.extend(
                _validate_claim_and_unknown_links(
                    claim_refs=argument.claim_refs,
                    unknown_refs=argument.unknown_refs,
                    claim_ids=claims,
                    unknown_ids=unknowns,
                    stage="debate",
                    label=f"{argument.producer_id}-round-{argument.round_number}",
                )
            )
            for proposal in argument.dispute_proposals:
                errors.extend(
                    _validate_claim_and_unknown_links(
                        claim_refs=proposal.claim_refs,
                        unknown_refs=proposal.unknown_refs,
                        claim_ids=claims,
                        unknown_ids=unknowns,
                        stage="debate",
                        label=proposal.dispute_id,
                    )
                )
                missing_evidence = sorted(
                    set(proposal.evidence_refs)
                    - {item.evidence_id for item in context.evidence}
                )
                if missing_evidence:
                    errors.append(
                        _message(
                            "EVIDENCE_REFERENCE",
                            f"dispute proposal {proposal.dispute_id} references unknown evidence: {', '.join(missing_evidence)}",
                            [proposal.dispute_id, *missing_evidence],
                        )
                    )
    for label, refs in (
        ("agreement", debate.agreement_claim_refs),
        ("disagreement", debate.disagreement_claim_refs),
    ):
        missing = sorted(set(refs) - claims)
        if missing:
            errors.append(_message("CLAIM_REFERENCE", f"{label} references unknown claims: {', '.join(missing)}", missing))
    missing_unknowns = sorted(set(debate.unresolved_unknown_refs) - unknowns)
    if missing_unknowns:
        errors.append(_message("UNKNOWN_REFERENCE", f"debate summary references unknown unknowns: {', '.join(missing_unknowns)}", missing_unknowns))
    return errors


def _validate_alternative(
    alternative: Alternative,
    *,
    claim_ids: set[str],
    unknown_ids: set[str],
    stage: str,
) -> list[RunMessage]:
    errors = _validate_claim_and_unknown_links(
        claim_refs=[*alternative.why_claim_ids, *alternative.reason_claim_ids],
        unknown_refs=[*alternative.why_unknown_ids, *alternative.reason_unknown_ids],
        claim_ids=claim_ids,
        unknown_ids=unknown_ids,
        stage=stage,
        label=alternative.alternative_id,
    )
    if not (
        alternative.why_claim_ids
        or alternative.why_unknown_ids
    ):
        errors.append(_message("UNLINKED_ALTERNATIVE", f"alternative {alternative.alternative_id} has no reason for consideration", [alternative.alternative_id]))
    if not (
        alternative.reason_claim_ids
        or alternative.reason_unknown_ids
    ):
        errors.append(_message("UNLINKED_ALTERNATIVE", f"alternative {alternative.alternative_id} has no rejection/defer reason", [alternative.alternative_id]))
    return errors


def validate_research_manager_output(
    context: EvaluationContext,
    registry: RegistryResult,
    output: ResearchManagerOutput,
) -> tuple[list[EvidenceGap], list[RunMessage]]:
    """Validate RM links and return any newly registered, valid evidence gaps."""
    claims = {claim.claim_id for claim in registry.claims}
    unknowns = {unknown.unknown_id for unknown in context.unknowns}
    gaps = {gap.gap_id: gap for gap in registry.evidence_gaps}
    errors: list[RunMessage] = []
    if output.run_id != context.run_id:
        errors.append(_message("RUN_ID_MISMATCH", "research-manager output belongs to another run"))
    for label, linked in (
        ("thesis", output.thesis),
        ("strongest-counterexample", output.strongest_counterexample),
    ):
        errors.extend(
            _validate_claim_and_unknown_links(
                claim_refs=linked.claim_refs,
                unknown_refs=linked.unknown_refs,
                claim_ids=claims,
                unknown_ids=unknowns,
                stage="research-manager",
                label=label,
            )
        )
    for index, condition in enumerate(output.invalidation_conditions):
        errors.extend(
            _validate_claim_and_unknown_links(
                claim_refs=condition.claim_refs,
                unknown_refs=condition.unknown_refs,
                claim_ids=claims,
                unknown_ids=unknowns,
                stage="research-manager",
                label=f"invalidation-{index}",
            )
        )
    for alternative in output.alternatives:
        errors.extend(
            _validate_alternative(
                alternative,
                claim_ids=claims,
                unknown_ids=unknowns,
                stage="research-manager",
            )
        )
    for reference in [*output.candidate_claim_ids]:
        if reference not in claims:
            errors.append(_message("CLAIM_REFERENCE", f"research manager selected unknown claim {reference}", [reference]))
    valid_new_gaps: list[EvidenceGap] = []
    for gap in output.evidence_gaps:
        if gap.gap_id in gaps:
            errors.append(_message("DUPLICATE_GAP", f"research manager repeated gap {gap.gap_id}", [gap.gap_id]))
            continue
        registry_error_count = len(registry.errors)
        valid = _validate_gap(
            gap,
            context=context,
            canonical_ids=claims,
            aliases={},
            result=registry,
        )
        errors.extend(registry.errors[registry_error_count:])
        if valid is not None:
            valid_new_gaps.append(valid)
            gaps[valid.gap_id] = valid
    for reference in output.candidate_gap_ids:
        if reference not in gaps:
            errors.append(_message("GAP_REFERENCE", f"research manager selected unknown gap {reference}", [reference]))
    valid_gap_ids = set(gaps)
    for proposal in output.test_proposals:
        invalid_claims = sorted(set(proposal.claim_ids) - claims)
        invalid_gaps = sorted(set(proposal.gap_ids) - valid_gap_ids)
        if invalid_claims or invalid_gaps:
            errors.append(_message("INVALID_TEST_LINK", f"test {proposal.test_key} has invalid claim/gap links", [proposal.test_key, *invalid_claims, *invalid_gaps]))
    return valid_new_gaps, errors
