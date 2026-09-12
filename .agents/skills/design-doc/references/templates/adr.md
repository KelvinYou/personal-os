# ADR Template

For recording **one decision**. An ADR is narrower than a design doc on purpose: a design doc describes a system that stops being accurate once the code changes, while an ADR records a choice and its reasoning, which stays true for years.

Keep it to one page. Short ADRs get read; long ones get filed. Once accepted, don't edit it — if the decision changes, write a new ADR that supersedes it and link both ways.

File as `docs/design/adr/NNNN-short-title.md` with a zero-padded sequence number.

---

# ADR NNNN — [Decision in a short noun phrase]

**Status:** Proposed | Accepted | Superseded by ADR-NNNN
**Date:** YYYY-MM-DD · **Deciders:** …

## Context

The forces in play: the problem, the constraints, what's already true about the system, and what makes this a real choice rather than an obvious one. Two or three paragraphs at most.

State constraints explicitly — a reader in two years needs to know what boxed you in, because that's usually what changed.

## Decision

One paragraph, active voice, present tense: "We will enforce withdrawal limits in the backend rule engine, and clients will call `POST /withdrawals/validate` before enabling submit."

Say what was decided, not what was discussed.

## Alternatives Considered

Each option in two or three lines: what it was, and the specific reason it lost. "Rejected because it duplicates regulatory logic across two clients that ship on different release cadences" — not "rejected because it's worse".

Include the option a future reader would ask about, even if it was quickly dismissed.

## Consequences

Both directions, honestly.

**Positive:** what becomes easier or safer.
**Negative:** what becomes harder, slower, or more expensive — the cost you knowingly accepted.
**Follow-ups:** work this decision creates, and anything now blocked on it.

The negative consequences are the part future readers value most. An ADR with only upside reads as advocacy and doesn't get trusted.
