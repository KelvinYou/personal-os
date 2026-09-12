# Design-Full Template

For cross-service, migration-heavy, regulated, security-sensitive, or genuinely contested changes.

This is a superset of `design-lite.md`. Everything in Design-Lite still applies — same numbering intent, same "delete what the change didn't earn" rule. The sections below are the ones Design-Lite compresses or omits. A full doc that fills every heading regardless of relevance is a worse document than a lite one; length here buys *depth on the risky parts*, not coverage of all parts.

---

# [Feature Name] — Technical Design

**Author** · **Status** (Draft | In Review | Accepted | Superseded) · **Created** · **Last updated** · **Reviewers**

## 1. Overview

### Background
Why this is needed. Include the evidence — metrics, incidents, support volume, a regulatory deadline. A background section without evidence is an opinion.

### Objective
What "done" looks like, stated as an outcome rather than a task list.

### Goals / Non-goals
Non-goals matter more than goals: they're the things a reviewer would reasonably assume are in scope. Listing them prevents the review from expanding.

### Success metrics
How you'll know it worked, and who owns the number.

## 2. Current Architecture

Diagram, then the flow in prose only where the diagram is ambiguous. Then **current limitations**, stated as facts about the system with file/service names attached.

## 3. Proposed Architecture

Diagram with `[NEW]` / `[MODIFIED]` markers, design intent in one sentence, then the key-changes table (Component | Change | Reason). Reason is the column reviewers read.

## 4. API Changes

Per endpoint: method + path, purpose, request and response JSON, error responses, auth requirements.

For modified endpoints, show **before / after** for changed fields only and state a backward-compatibility verdict. If breaking: who consumes it, how they're migrated, and by when. "TBD" here is a blocker, not a detail.

## 5. Functional Changes

Per function: current behaviour → proposed behaviour → reason → technical changes split by layer (frontend / API / backend / data). Keep each block short; depth belongs in sections 6–9.

## 6. Business Logic

Rules stated explicitly. Prose hides ambiguity; pseudocode and tables expose it.

```text
IF verification_status = VERIFIED
    limit = country_config.verified_limit
ELSE IF verification_status = PENDING
    limit = country_config.base_limit
ELSE
    reject(NOT_VERIFIED)
```

Or a decision matrix when behaviour depends on more than one dimension:

| Country | Verified | Daily limit | Requires manual review |
|---|---|---|---|
| SG | Yes | 50,000 | No |
| SG | No | 1,000 | Yes |

State where each rule is **enforced**, and whether a client can bypass it. That's the question an architect asks first about any rule.

## 7. Error Handling

| Scenario | Expected behaviour | Surfaced as |
|---|---|---|
| Invalid amount | Reject before submission | `400 INVALID_AMOUNT`, inline field error |
| Downstream timeout | Retry ×2 with backoff, then fail closed | `503`, retryable banner |
| Insufficient balance | Reject | `409 INSUFFICIENT_BALANCE` |
| Partial write after payment call | Compensating action / reconciliation job | Logged + alerted |

Cover the unhappy paths that produce inconsistent state, not just the ones that produce a nice error message.

## 8. Security & Compliance

Only list controls that this change actually touches, and say **where** each is enforced:
authentication · authorization (who may call this, checked where) · input validation · sensitive-data handling and logging · audit trail · rate limiting / abuse · regulatory requirement and the rule it maps to.

"We will validate input" is not a control. "Amount is validated server-side in `WithdrawalValidator` against the country rule before the payment call" is.

## 9. Data / Database Changes

**Schema changes:** new tables, columns, indexes, with types and nullability. Note index choices for any query this adds on a large table.

**Migration:** required yes/no · online or requires downtime · expected duration · rollback path.

**Backfill:** does existing data need transforming? What's the default for rows written before the change? What does a partially-backfilled state look like to a reader?

**Retention / PII:** if new personal data is stored, its retention and deletion path.

## 10. Testing Strategy

Include only if the change needs testing beyond the team's normal coverage. When included, be specific about **what makes this change hard to test**: state combinations, country/tier matrices, external service behaviour, migration correctness.

Unit · integration · e2e/regression scope · contract tests for changed APIs · migration dry-run.

## 11. Impact & Risks

Impacted areas as concrete surfaces (services, clients, jobs, dashboards, other teams). Risks paired with mitigations, each risk phrased as a thing that could actually happen — not a category.

Include a **regression scope** paragraph: which existing flows must be re-verified and why. This is where a "small" change gets its honest cost.

## 12. Alternatives Considered

Two or three real options with honest pros and cons, then a recommendation whose reasoning ties back to the driver in section 1. Include the "do nothing" option when the cost of the change is significant — it's a legitimate baseline and reviewers respect that you considered it.

## 13. Rollout / Deployment

Feature flag (yes/no, flag name) · deployment order across services · migration timing relative to deploy · backward compatibility window · rollback strategy, including whether rollback is possible after the migration runs · monitoring and the alert that would tell you to roll back.

Deployment order matters whenever two services change together — state which ships first and whether either can run against the other's old version.

## 14. Open Questions

Decisions you need from the reviewer, each with a proposed default where you have a view. Distinguish *blocking* (can't start without an answer) from *non-blocking* (can be decided during implementation).
