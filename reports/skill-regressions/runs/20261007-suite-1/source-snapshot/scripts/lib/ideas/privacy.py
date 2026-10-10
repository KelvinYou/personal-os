"""Small deterministic privacy boundary for model input and output."""
from __future__ import annotations

import re
from typing import Any

from .models import EvaluationContext, ModelProcessing


class PrivacyError(ValueError):
    """Raised when a payload contains an obvious secret or forbidden fragment."""


_SECRET = re.compile(
    r"(?i)(?:api[_-]?key|access[_-]?token|authorization|password|secret)\s*[:=]\s*[^\s,;]+"
)


def _redact_string(value: str, forbidden_fragments: tuple[str, ...] = ()) -> str:
    result = value
    for fragment in forbidden_fragments:
        if fragment and fragment in result:
            result = result.replace(fragment, "[REDACTED]")
    return _SECRET.sub("[REDACTED]", result)


def _walk(value: Any, forbidden_fragments: tuple[str, ...]) -> Any:
    if isinstance(value, str):
        return _redact_string(value, forbidden_fragments)
    if isinstance(value, list):
        return [_walk(item, forbidden_fragments) for item in value]
    if isinstance(value, dict):
        return {key: _walk(item, forbidden_fragments) for key, item in value.items()}
    return value


def prepare_model_input(context: EvaluationContext) -> dict[str, Any]:
    """Return only model-allowed evidence, with obvious secrets redacted."""
    payload = context.model_dump(mode="json", exclude_none=False)
    evidence: list[dict[str, Any]] = []
    for item in payload.get("evidence", []):
        if item.get("model_processing") == ModelProcessing.EXCLUDED.value:
            continue
        if item.get("model_processing") == ModelProcessing.REDACTED.value:
            approved = item.get("model_excerpt_or_observation")
            item["excerpt_or_observation"] = approved or "[redacted evidence]"
        item.pop("model_excerpt_or_observation", None)
        evidence.append(item)
    payload["evidence"] = evidence
    return _walk(payload, ())


def sanitize_context_for_artifact(context: EvaluationContext) -> EvaluationContext:
    """Build the persisted context projection without raw restricted evidence."""
    payload = sanitize_model_output(
        context.model_dump(mode="json", exclude_none=False), context
    )
    safe_evidence: list[dict[str, Any]] = []
    for item in payload.get("evidence", []):
        if item.get("model_processing") == ModelProcessing.EXCLUDED.value:
            # Keep a model-valid, auditable placeholder.  The original item
            # remains available only in the private input evidence file.
            safe_evidence.append(
                {
                    "evidence_id": item.get("evidence_id"),
                    "locator": "[excluded]",
                    "publisher_or_source": "[excluded]",
                    "observed_or_effective_at": "unknown",
                    "retrieved_at": context.as_of.isoformat(),
                    "scope": "[excluded]",
                    "excerpt_or_observation": "[excluded from run artifact]",
                    "freshness_window": "not_applicable",
                    "model_processing": ModelProcessing.EXCLUDED.value,
                    "temporal_status": "observed",
                    "supersedes_evidence_id": None,
                    "quality_note": "excluded from model processing and run rendering",
                }
            )
            continue
        if item.get("model_processing") == ModelProcessing.REDACTED.value:
            approved_excerpt = item.get(
                "model_excerpt_or_observation"
            ) or item.get("excerpt_or_observation") or "[redacted evidence]"
            item["excerpt_or_observation"] = approved_excerpt
            # Keep the approved projection so the persisted EvaluationContext
            # remains valid; prepare_model_input removes this field before a
            # provider call.
            item["model_excerpt_or_observation"] = approved_excerpt
        else:
            item.pop("model_excerpt_or_observation", None)
        safe_evidence.append(item)
    payload["evidence"] = safe_evidence
    return EvaluationContext.model_validate(payload)


def sanitize_model_output(payload: Any, context: EvaluationContext) -> Any:
    """Redact obvious secrets before structured output is validated/persisted."""
    excluded_fragments = tuple(
        item.excerpt_or_observation
        for item in context.evidence
        if item.model_processing is ModelProcessing.EXCLUDED
    )
    return _walk(payload, excluded_fragments)
