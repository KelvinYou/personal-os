"""Provider-neutral model boundary for idea-pipeline stages."""
from __future__ import annotations

import copy
import json
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Callable, Mapping, Protocol

from pydantic import BaseModel

from .canonical import sha256_hex


@dataclass(frozen=True)
class ModelResult:
    payload: dict[str, Any]
    provider: str
    model: str
    prompt_hash: str
    config_hash: str
    cost: Decimal | None
    currency: str | None
    elapsed_seconds: float


class ModelClient(Protocol):
    async def complete(
        self,
        *,
        stage: str,
        system_prompt: str,
        input_payload: dict[str, Any],
        output_model: type[BaseModel],
        output_schema: dict[str, Any],
    ) -> ModelResult: ...


class ScriptedModelClient:
    """Deterministic fixture client used by tests and offline review."""

    def __init__(
        self,
        responses: Mapping[str, dict[str, Any]] | Callable[[str, dict[str, Any]], dict[str, Any]],
        *,
        model: str = "fixture",
        cost: Decimal = Decimal("0"),
        currency: str = "USD",
    ) -> None:
        self.responses = responses
        self.model = model
        self.cost = cost
        self.currency = currency
        self.calls: list[str] = []

    async def complete(
        self,
        *,
        stage: str,
        system_prompt: str,
        input_payload: dict[str, Any],
        output_model: type[BaseModel],
        output_schema: dict[str, Any],
    ) -> ModelResult:
        started = time.monotonic()
        self.calls.append(stage)
        if callable(self.responses):
            payload = self.responses(stage, input_payload)
        else:
            if stage in self.responses:
                payload = self.responses[stage]
            else:
                payload = self.responses.get("*")
        if payload is None:
            raise RuntimeError(f"fixture has no response for stage {stage}")
        if isinstance(payload, BaseModel):
            payload = payload.model_dump(mode="json")
        return ModelResult(
            payload=copy.deepcopy(payload),
            provider="scripted",
            model=self.model,
            prompt_hash=sha256_hex({"system": system_prompt, "input": input_payload}),
            config_hash=sha256_hex(output_schema),
            cost=self.cost,
            currency=self.currency,
            elapsed_seconds=time.monotonic() - started,
        )


class DemoModelClient:
    """Credential-free model-shaped responses for local pipeline smoke tests."""

    def __init__(self, *, model: str = "demo") -> None:
        self.model = model
        self.calls: list[str] = []

    async def complete(
        self,
        *,
        stage: str,
        system_prompt: str,
        input_payload: dict[str, Any],
        output_model: type[BaseModel],
        output_schema: dict[str, Any],
    ) -> ModelResult:
        started = time.monotonic()
        self.calls.append(stage)
        context = input_payload.get("context", {})
        unknowns = context.get("unknowns", [])
        unknown_id = unknowns[0]["unknown_id"] if unknowns else None
        claims = input_payload.get("claims", [])
        claim_id = claims[0].get("claim_id") if claims else None

        if stage == "baseline":
            question_ids = input_payload.get(
                "required_question_ids", ["baseline-question"]
            )
            payload = {
                "checklist": [
                    {
                        "question_id": question_id,
                        "status": "UNKNOWN" if unknown_id else "NOT_APPLICABLE",
                        **({"unknown_id": unknown_id} if unknown_id else {"reason": "No unknowns were declared for this exploratory run."}),
                    }
                    for question_id in question_ids
                ],
                "claims": [
                    {
                        "candidate_key": "demo-demand-hypothesis",
                        "statement": "Target buyers have an urgent problem.",
                        "claim_kind": "hypothesis",
                    }
                ],
                "alternatives": [],
                "evidence_gaps": [],
                "test_proposals": [],
            }
        elif stage.startswith("analyst:"):
            lens_id = stage.split(":", 1)[1]
            question_ids = input_payload.get("required_question_ids", [f"{lens_id}-question"])
            payload = {
                "checklist": [
                    {
                        "question_id": question_id,
                        "status": "UNKNOWN" if unknown_id else "NOT_APPLICABLE",
                        **({"unknown_id": unknown_id} if unknown_id else {"reason": "No unknowns were declared for this exploratory run."}),
                    }
                    for question_id in question_ids
                ],
                "claims": [
                    {
                        "candidate_key": f"{lens_id}-hypothesis",
                        "statement": f"The {lens_id} hypothesis needs validation.",
                        "claim_kind": "hypothesis",
                    }
                ],
                "alternatives": [],
                "evidence_gaps": [],
                "test_proposals": [],
            }
        elif stage.startswith("debate:"):
            if stage.endswith("summary"):
                payload = {
                    "agreement_claim_refs": [claim_id] if claim_id else [],
                    "disagreement_claim_refs": [claim_id] if claim_id else [],
                    "unresolved_unknown_refs": [unknown_id] if unknown_id else [],
                }
            else:
                position = stage.split(":")[1]
                round_number = int(stage.split(":")[2])
                payload = {
                    "position": position,
                    "round_number": round_number,
                    "argument": f"The {position} case remains conditional on the registered evidence.",
                    "claim_refs": [claim_id] if claim_id else [],
                    "unknown_refs": [unknown_id] if unknown_id else [],
                    "dispute_proposals": [],
                }
        elif stage == "research-manager":
            payload = {
                "thesis": {
                    "statement": "The registered claims require a discriminating test.",
                    "claim_refs": [claim_id] if claim_id else [],
                    "unknown_refs": [unknown_id] if not claim_id and unknown_id else [],
                },
                "strongest_counterexample": {
                    "statement": "The load-bearing hypothesis may be false.",
                    "claim_refs": [claim_id] if claim_id else [],
                    "unknown_refs": [unknown_id] if not claim_id and unknown_id else [],
                },
                "invalidation_conditions": [],
                "evidence_gaps": [],
                "alternatives": [],
                "candidate_claim_ids": [claim_id] if claim_id else [],
                "candidate_gap_ids": [],
                "test_proposals": [
                    {
                        "test_key": "demo-discriminating-test",
                        "title": "Run a buyer test",
                        "assumption": "The load-bearing hypothesis is true.",
                        "claim_ids": [claim_id] if claim_id else [],
                        "gap_ids": [],
                        "impact_if_false": "MAJOR",
                        "discriminating_test": "Run five structured buyer interviews.",
                        "criterion": "Three meet the pre-registered response criterion.",
                        "target_or_sample": "Five target buyers.",
                        "owner": "User",
                        "deadline": context.get("as_of"),
                        "estimated_cost": {
                            "amount": "0",
                            "currency": "USD",
                            "user_minutes": 60,
                        },
                    }
                ],
            }
        else:
            raise RuntimeError(f"demo engine has no response for stage {stage}")

        return ModelResult(
            payload=payload,
            provider="demo",
            model=self.model,
            prompt_hash=sha256_hex({"system": system_prompt, "input": input_payload}),
            config_hash=sha256_hex(output_schema),
            cost=Decimal("0"),
            currency="USD",
            elapsed_seconds=time.monotonic() - started,
        )


class ClaudeAgentSDKClient:
    """Optional Claude Agent SDK adapter.

    The import is deliberately lazy.  Deterministic validation and the test
    suite do not require the SDK or an API credential.
    """

    def __init__(self, model: str = "sonnet") -> None:
        self.model = model

    async def complete(
        self,
        *,
        stage: str,
        system_prompt: str,
        input_payload: dict[str, Any],
        output_model: type[BaseModel],
        output_schema: dict[str, Any],
    ) -> ModelResult:
        try:
            from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "Claude model execution requires the optional claude-agent-sdk dependency"
            ) from exc

        started = time.monotonic()
        prompt = json.dumps(input_payload, ensure_ascii=False, sort_keys=True)
        options = ClaudeAgentOptions(
            model=self.model,
            system_prompt=system_prompt,
            tools=[],
            permission_mode="dontAsk",
            strict_mcp_config=True,
            setting_sources=[],
            output_format={"type": "json_schema", "schema": output_schema},
            max_turns=5,
        )
        final_message = None
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, ResultMessage):
                final_message = message
        if final_message is None:
            raise RuntimeError(f"{stage}: model returned no result")
        payload = getattr(final_message, "structured_output", None)
        if payload is None:
            text = getattr(final_message, "result", None)
            if not text:
                raise RuntimeError(f"{stage}: model returned no structured output")
            payload = json.loads(text)
        if not isinstance(payload, dict):
            raise RuntimeError(f"{stage}: model output must be an object")

        raw_cost = getattr(final_message, "total_cost_usd", None)
        cost = Decimal(str(raw_cost)) if raw_cost is not None else None
        return ModelResult(
            payload=payload,
            provider="claude-agent-sdk",
            model=self.model,
            prompt_hash=sha256_hex({"system": system_prompt, "input": input_payload}),
            config_hash=sha256_hex(output_schema),
            cost=cost,
            currency="USD" if cost is not None else None,
            elapsed_seconds=time.monotonic() - started,
        )
