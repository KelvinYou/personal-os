"""CommonMark renderer for immutable idea runs."""
from __future__ import annotations

from typing import Any

import yaml

from .models import LedgerRow, RunArtifact


def _cell(value: Any) -> str:
    if value is None or value == "":
        return "—"
    text = str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def _cost(row: LedgerRow) -> str:
    if row.estimated_cost is None:
        return "—"
    cost = f"{row.estimated_cost.amount} {row.estimated_cost.currency}"
    if row.estimated_cost.user_minutes is not None:
        cost += f"; {row.estimated_cost.user_minutes} user-min"
    return cost


def _row(row: LedgerRow) -> str:
    qualification = (
        f"{row.provenance.value} / {row.grounding_status.value} / "
        f"{row.evidence_status.value}"
    )
    links = ", ".join([*row.claim_ids, *row.gap_ids]) or "—"
    owner_deadline = _cell(row.owner)
    if row.deadline:
        owner_deadline += f" / {row.deadline.isoformat()}"
    return "| " + " | ".join(
        [
            _cell(row.test_id),
            _cell(row.priority.value),
            _cell(row.state.value),
            _cell(row.assumption),
            _cell(links),
            _cell(qualification),
            _cell(row.impact_if_false.value),
            _cell(row.discriminating_test),
            _cell(row.criterion),
            owner_deadline,
            _cell(_cost(row)),
        ]
    ) + " |"


def _safe_context(context: Any) -> dict[str, Any]:
    """Return the same safe context projection used for artifact hashing."""
    from .privacy import sanitize_context_for_artifact

    return sanitize_context_for_artifact(context).model_dump(
        mode="json", exclude_none=False
    )


def _claim_support(artifact: RunArtifact, claim: Any) -> str:
    evidence_by_id = {
        item.evidence_id: item for item in artifact.context.evidence
    }
    support: list[str] = []
    for evidence_id in claim.evidence_refs:
        item = evidence_by_id.get(evidence_id)
        if item is None or item.model_processing.value == "excluded":
            continue
        excerpt = (
            item.model_excerpt_or_observation
            if item.model_processing.value == "redacted"
            else item.excerpt_or_observation
        )
        support.append(f"{evidence_id}: {item.locator} — {excerpt}")
    return "<br>".join(support) or "—"


def _linked_statement(label: str, value: Any) -> list[str]:
    links = ", ".join([*value.claim_refs, *value.unknown_refs]) or "—"
    return [
        f"**{label}:** {_cell(value.statement)}  ",
        f"Links: `{_cell(links)}`",
        "",
    ]


def render_run(artifact: RunArtifact) -> str:
    payload = artifact.model_dump(mode="json", exclude_none=False)
    payload["context"] = _safe_context(artifact.context)
    frontmatter = yaml.safe_dump(
        payload,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )
    ledger = artifact.ledger
    lines = [
        "---",
        frontmatter.rstrip("\n"),
        "---",
        "",
        f"# Startup-idea evaluation — `{artifact.idea_id}`",
        "",
        f"**Run:** `{artifact.run_id}`  ",
        f"**Status:** `{artifact.run_status.value}`  ",
        f"**As of:** `{artifact.context.as_of.isoformat()}`  ",
        f"**Input snapshot:** `{artifact.input_snapshot_id}`",
        "",
        "> `CITED` means supplied-source referenced; it does not mean independently verified.",
        "",
    ]
    lines.extend(["## Claims", ""])
    if artifact.claims:
        lines.extend(
            [
                "| Claim ID | Statement | Provenance | Grounding | Evidence status | Source / support | Other links |",
                "|---|---|---|---|---|---|---|",
            ]
        )
        for claim in artifact.claims:
            other_links = ", ".join(
                [
                    *claim.context_refs,
                    *claim.user_assumption_refs,
                    *claim.derivation_refs,
                    *claim.unknown_refs,
                    *claim.dispute_refs,
                ]
            ) or "—"
            lines.append(
                "| "
                + " | ".join(
                    [
                        _cell(claim.claim_id),
                        _cell(claim.statement),
                        _cell(claim.provenance.value),
                        _cell(claim.grounding_status.value),
                        _cell(claim.evidence_status.value),
                        _cell(_claim_support(artifact, claim)),
                        _cell(other_links),
                    ]
                )
                + " |"
            )
    else:
        lines.append("No claims survived registry validation.")
    if artifact.disputes:
        lines.extend(
            [
                "",
                "## Disputes",
                "",
                "| Dispute ID | Claim IDs | Evidence IDs | Reason | Actor |",
                "|---|---|---|---|---|",
            ]
        )
        for dispute in artifact.disputes:
            lines.append(
                "| "
                + " | ".join(
                    [
                        _cell(dispute.dispute_id),
                        _cell(", ".join(dispute.claim_refs)),
                        _cell(", ".join(dispute.evidence_refs)),
                        _cell(dispute.reason),
                        _cell(dispute.actor),
                    ]
                )
                + " |"
            )
    if artifact.adjudication is not None:
        lines.extend(["", "## Adjudication", ""])
        lines.extend(_linked_statement("Thesis", artifact.adjudication.thesis))
        lines.extend(
            _linked_statement(
                "Strongest counterexample",
                artifact.adjudication.strongest_counterexample,
            )
        )
        if artifact.adjudication.invalidation_conditions:
            lines.extend(["**Invalidation conditions:**", ""])
            for condition in artifact.adjudication.invalidation_conditions:
                links = ", ".join(
                    [*condition.claim_refs, *condition.unknown_refs]
                ) or "—"
                lines.append(f"- {_cell(condition.statement)} (`{_cell(links)}`)")
            lines.append("")

    if ledger is not None:
        lines.extend(
            [
                "",
                "## Assumption ledger",
                "",
                "| Test ID | Priority | State | Assumption | Claim IDs / Gap IDs | Provenance / grounding / evidence status | Impact if false | Discriminating test | Pass / fail / inconclusive criterion | Owner / deadline | Estimated cost |",
                "|---|---|---|---|---|---|---|---|---|---|---|",
            ]
        )
        lines.extend(_row(row) for row in ledger.rows)
        if ledger.appendix_rows:
            lines.extend(["", "### Appendix", ""])
            lines.extend(_row(row) for row in ledger.appendix_rows)

        lines.extend(["", "## Alternatives", ""])
        if ledger.alternatives:
            lines.append("| ID | Alternative | Why considered | Reason rejected/deferred | Links |")
            lines.append("|---|---|---|---|---|")
            for alternative in ledger.alternatives:
                links = ", ".join(
                    [
                        *alternative.why_claim_ids,
                        *alternative.why_unknown_ids,
                        *alternative.reason_claim_ids,
                        *alternative.reason_unknown_ids,
                    ]
                ) or "—"
                lines.append(
                    "| "
                    + " | ".join(
                        [
                            _cell(alternative.alternative_id),
                            _cell(alternative.alternative),
                            _cell(", ".join(alternative.why_claim_ids or alternative.why_unknown_ids)),
                            _cell(", ".join(alternative.reason_claim_ids or alternative.reason_unknown_ids)),
                            _cell(links),
                        ]
                    )
                    + " |"
                )
        else:
            lines.append("No alternatives were registered.")


    lines.extend(["", "## Evidence gaps", ""])
    if artifact.evidence_gaps:
        for gap in artifact.evidence_gaps:
            links = ", ".join([*gap.unknown_ids, *gap.affected_claim_ids])
            lines.append(
                f"- `{_cell(gap.gap_id)}` — {_cell(gap.why_load_bearing)} ({_cell(links)})"
            )
    else:
        lines.append("No evidence gaps were registered.")

    if artifact.errors:
        lines.extend(["", "## Errors", ""])
        lines.extend(
            f"- `{_cell(error.code)}` ({_cell(error.stage)}) — {_cell(error.message)}"
            for error in artifact.errors
        )
    if artifact.warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(
            f"- `{_cell(warning.code)}` ({_cell(warning.stage)}) — {_cell(warning.message)}"
            for warning in artifact.warnings
        )
    return "\n".join(lines) + "\n"
