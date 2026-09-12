"""Deterministic preflight validation for idea evaluation inputs."""
from __future__ import annotations

from datetime import date, datetime
from typing import Iterable
from uuid import uuid4

from .canonical import sha256_hex
from ..clock import KL_TIMEZONE, now_kl
from .models import EvaluationContext, EvaluationInput, EvidenceItem


class ContextValidationError(ValueError):
    """Raised when a run cannot safely enter model execution."""


def _duplicates(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return sorted(duplicates)


def _require_unique(label: str, values: Iterable[str]) -> None:
    duplicates = _duplicates(values)
    if duplicates:
        raise ContextValidationError(
            f"duplicate {label} identifiers: {', '.join(duplicates)}"
        )


def _ensure_aware(value: datetime, label: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ContextValidationError(f"{label} must include a timezone")


def _validate_evidence_dates(
    evidence: list[EvidenceItem], *, evaluated_at: datetime, input_: EvaluationInput
) -> None:
    evaluated_date = evaluated_at.astimezone(KL_TIMEZONE).date()
    for item in evidence:
        if item.retrieved_at > evaluated_date:
            raise ContextValidationError(
                f"evidence {item.evidence_id} was retrieved after evaluated_at"
            )
        if input_.historical_replay and item.retrieved_at > input_.as_of:
            raise ContextValidationError(
                f"evidence {item.evidence_id} is look-ahead for historical as_of"
            )
        if (
            isinstance(item.observed_or_effective_at, date)
            and item.observed_or_effective_at > evaluated_date
            and item.temporal_status.value not in {"forecast", "planned"}
        ):
            raise ContextValidationError(
                f"evidence {item.evidence_id} has a future effective date without forecast/planned status"
            )
        if (
            input_.historical_replay
            and isinstance(item.observed_or_effective_at, date)
            and item.observed_or_effective_at > input_.as_of
        ):
            raise ContextValidationError(
                f"evidence {item.evidence_id} has future effective information in historical replay"
            )


def _validate_supersedes(evidence: list[EvidenceItem]) -> None:
    by_id = {item.evidence_id: item for item in evidence}
    for item in evidence:
        previous_id = item.supersedes_evidence_id
        if previous_id is None:
            continue
        previous = by_id.get(previous_id)
        if previous is None:
            raise ContextValidationError(
                f"evidence {item.evidence_id} supersedes unknown evidence {previous_id}"
            )
        if previous.retrieved_at >= item.retrieved_at:
            raise ContextValidationError(
                f"evidence {item.evidence_id} must supersede an older evidence item"
            )


def validate_context(
    input_: EvaluationInput,
    *,
    now: datetime | None = None,
) -> EvaluationContext:
    """Validate user-owned context and assign validator-owned run metadata."""
    evaluated_at = now or now_kl()
    _ensure_aware(evaluated_at, "evaluated_at")
    evaluated_date = evaluated_at.astimezone(KL_TIMEZONE).date()

    if not input_.unknowns_declared:
        raise ContextValidationError(
            "unknowns_declared must be true; an empty unknown list must be explicit"
        )
    if input_.as_of > evaluated_date:
        raise ContextValidationError("as_of cannot be later than evaluated_at")
    if input_.as_of < evaluated_date:
        if not input_.historical_replay or not input_.historical_replay_reason:
            raise ContextValidationError(
                "a historical as_of requires historical_replay and a reason"
            )
    if input_.historical_replay and not input_.historical_replay_reason:
        raise ContextValidationError(
            "historical_replay requires historical_replay_reason"
        )
    if input_.consent.granted_at > evaluated_at:
        raise ContextValidationError("consent cannot be granted after evaluated_at")
    if input_.consent.expires_at is not None and input_.consent.expires_at <= evaluated_at:
        raise ContextValidationError("model-processing consent is expired")

    _require_unique("context", (field.context_ref for field in input_.context_fields))
    _require_unique(
        "user assumption",
        (assumption.user_assumption_id for assumption in input_.user_assumptions),
    )
    _require_unique("evidence", (item.evidence_id for item in input_.evidence))
    _require_unique("unknown", (unknown.unknown_id for unknown in input_.unknowns))
    _validate_evidence_dates(
        input_.evidence, evaluated_at=evaluated_at, input_=input_
    )
    _validate_supersedes(input_.evidence)

    for assumption in input_.user_assumptions:
        if assumption.recorded_at > evaluated_date:
            raise ContextValidationError(
                f"user assumption {assumption.user_assumption_id} is recorded in the future"
            )
        if assumption.expires_at is not None and assumption.expires_at < assumption.recorded_at:
            raise ContextValidationError(
                f"user assumption {assumption.user_assumption_id} expires before it was recorded"
            )
        if assumption.expires_at is not None and assumption.expires_at <= evaluated_date:
            raise ContextValidationError(
                f"user assumption {assumption.user_assumption_id} is expired"
            )

    snapshot_id = sha256_hex(input_)
    payload = input_.model_dump(mode="python", exclude_none=False)
    payload.update(
        {
            "run_id": f"run-{uuid4().hex}",
            "evaluated_at": evaluated_at,
            "input_snapshot_id": snapshot_id,
        }
    )
    return EvaluationContext.model_validate(payload)
