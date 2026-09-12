# Design-Lite Template

The default for feature enhancements. Optimised for a reviewer with 10 minutes.

Keep section numbering; drop any section the signal scan didn't earn. Sections 1, 2, 4, 7 and 9 are load-bearing — a doc without them isn't reviewable.

---

# [Feature Name] — Technical Design

**Author:** … **Status:** Draft | In Review | Accepted **Last updated:** YYYY-MM-DD
**Reviewers:** …

## 1. Context

Two to four sentences: why this is being done, and what happens if it isn't. Link the ticket. Name the driver — a customer complaint, a regulatory requirement, a scaling limit — because the driver determines which trade-offs are acceptable.

> The withdrawal flow currently enforces limits client-side, which lets Web and Mobile diverge and makes country-specific regulatory rules impossible to guarantee.

**Out of scope:** things a reviewer would reasonably assume are included but aren't. This prevents the review from drifting.

## 2. Scope

A table, so the reviewer knows what's changing in 30 seconds.

| # | Function | Change | Surface |
|---|---|---|---|
| 1 | Withdrawal Limit | Modify | Frontend + Backend |
| 2 | Withdrawal Confirmation | Modify | Frontend |
| 3 | Batch Withdrawal | New | Backend + API |

## 3. Current Architecture

Only if the reviewer doesn't already live in this system. A small diagram plus 1–2 concrete limitations. Limitations should be facts about the current code, not complaints.

```text
Frontend → Withdrawal API → Withdrawal Service → Payment Service → DB
```

**Current limitations**
- Limit calculation lives in `WithdrawalForm.tsx`, duplicated in the mobile client.
- No server-side rejection when a client submits an over-limit request.

## 4. Proposed Architecture

The most important section. Diagram with `[NEW]` / `[MODIFIED]` markers, then the design intent in one sentence, then key changes.

```text
Frontend ──→ POST /withdrawals/validate  [NEW]
             ↓
     Withdrawal Service  [MODIFIED]
             ↓
     Rule Engine  [NEW] ──→ DB
```

> The design introduces a centralized rule validation layer so withdrawal rules are enforced once, server-side, and stay consistent across clients.

| Component | Change | Reason |
|---|---|---|
| API | Add `POST /withdrawals/validate` | Pre-submit eligibility check |
| Backend | Move limit calculation server-side | Single source of truth across clients |
| Database | Add `withdrawal_rule` table | Country-specific limits become configurable |

## 5. API Changes

Never write "new API needed". Write the contract.

### New — `POST /api/withdrawals/validate`

**Purpose:** validate eligibility before submission, so the client renders the correct limit and error.

Request / Response as concrete JSON. Include the error shape, not just the happy path.

### Modified — `POST /api/withdrawals`

Show **before → after** for the changed fields only. Then state the verdict explicitly:

**Backward compatibility:** additive fields only; existing consumers unaffected. *(Or: breaking — mobile v3.2 and below must be migrated by <date>.)*

## 6. Function Changes

One short block per function. Resist writing an essay per function — the value is in *Reason*.

**Function 1 — Withdrawal Limit**
- **Current:** client determines the limit.
- **Proposed:** backend determines the limit from country + verification status.
- **Reason:** prevents duplicated business logic and makes regulatory rules centrally enforceable.

## 7. Trade-offs

Only for choices that were genuinely open. Two or three options, honest cons, then a recommendation with reasoning tied back to section 1's driver.

**Option A — enforce in frontend**
Pros: simple, fast to ship. Cons: duplicated logic; clients diverge; bypassable.

**Option B — enforce in backend**
Pros: centralized, consistent, auditable. Cons: extra API surface, higher effort.

**Recommendation:** Option B. Withdrawal rules are regulatory; consistency and non-bypassability outweigh the extra API work, and country-specific rules become a config change rather than two client releases.

If there was only one sane approach, say so in one line instead of inventing a straw-man option.

## 8. Impact & Risks

**Impacted areas:** list the concrete surfaces — Web withdrawal flow, mobile withdrawal flow, withdrawal history, payment service, existing rules.

**Risks → mitigation**, paired. An unmitigated risk is just a worry.

| Risk | Mitigation |
|---|---|
| Country-specific rules behave differently after centralization | Snapshot current per-country limits, assert parity in tests before cutover |
| API response change breaks existing consumers | Additive only; contract test against current mobile build |

**Regression scope:** name what must be re-tested and why. This is what turns "it's just a button" into a realistic estimate.

## 9. Open Questions

Decisions you need from the reviewer, phrased as questions with a proposed default where you have one.

1. Should the limit be configurable per country, or is a global default acceptable for v1? *(Proposal: per country, config-driven.)*
2. Should the rule be enforced at API layer or service layer?
3. Will Mobile consume the same endpoint in this release?

---

*Optional add-ons when the signal scan calls for them: Business Logic rules, Error Handling table, Data Changes, Security & Compliance, Rollout. Pull the fuller versions from `design-full.md`.*
