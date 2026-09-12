# Section Catalog

Per-section guidance for composing a doc that fits the change. Read the entries for the sections you're including — each one says what belongs, what "enough detail" means, and the failure mode that gets a doc sent back.

## Contents

1. [Context / Background](#context--background)
2. [Scope & Non-goals](#scope--non-goals)
3. [Current Architecture](#current-architecture)
4. [Proposed Architecture](#proposed-architecture)
5. [API Changes](#api-changes)
6. [Functional Changes](#functional-changes)
7. [Business Logic](#business-logic)
8. [Error Handling](#error-handling)
9. [Data / Database Changes](#data--database-changes)
10. [Security & Compliance](#security--compliance)
11. [Testing Strategy](#testing-strategy)
12. [Impact & Risks](#impact--risks)
13. [Alternatives & Trade-offs](#alternatives--trade-offs)
14. [Rollout / Deployment](#rollout--deployment)
15. [Open Questions](#open-questions)

---

## Context / Background

**Include:** always.

**Enough detail:** a reader who has never seen the ticket knows why this exists and what happens if it doesn't ship. Name the driver — customer complaint, regulatory deadline, incident, scaling limit — because the driver decides which trade-offs are acceptable later in the doc.

**Failure mode:** restating the ticket title in longer words. "We need to enhance the withdrawal flow" says nothing. What is broken, for whom, and how often?

**Failure mode:** asserting numbers with no source. If you write "this affects 30% of users", either cite where that came from or drop the number.

---

## Scope & Non-goals

**Include:** always, even in a one-page plan.

**Enough detail:** a numbered list or table of what's changing, at the granularity of "function" or "user-visible capability". A reviewer should get it in 30 seconds.

Non-goals are the higher-value half: list the things a reviewer would reasonably assume are included. That's what stops the review from expanding into a redesign.

**Failure mode:** scope written as implementation tasks ("add field to DTO") instead of capabilities ("support batch withdrawal"). Tasks belong in the plan, not the scope.

---

## Current Architecture

**Include:** when the reviewer doesn't already work in this system daily, or when the *limitation* of the current design is the argument for the change.

**Skip:** when the reviewer knows it better than you do. Two lines of recap beats a diagram they drew.

**Enough detail:** a small diagram of the path this change touches — not the whole system — plus limitations stated as facts with names attached ("limit calculation lives in `WithdrawalForm.tsx` and is duplicated in the mobile client"), not as complaints ("the current code is messy").

---

## Proposed Architecture

**Include:** any tier above Plan.

**Enough detail:** three things, in this order.

1. A diagram marking `[NEW]` and `[MODIFIED]`. The markers are the highest-signal element in the whole doc.
2. **One sentence naming the design intent.** This is what the architect quotes back to you. "The design introduces a centralized rule validation layer so withdrawal rules aren't duplicated across clients."
3. A Component | Change | Reason table. Reason is the column that gets read.

**Failure mode:** a diagram with no intent sentence. Boxes show *what*; the reader needs *why this shape*.

**Failure mode:** describing the new design without contrasting it against the current one, leaving the reader to diff two pictures themselves.

---

## API Changes

**Include:** whenever a contract changes — new endpoint, new field, changed semantics, changed error.

**Enough detail:** concrete JSON for request and response, including the error shape. For modified endpoints, before/after limited to the changed fields. Auth requirement per endpoint. And an explicit **backward-compatibility verdict**:

- *Additive, no consumer impact* — say it, so nobody has to work it out.
- *Breaking* — name every consumer, the migration path, and the deadline.

**Failure mode:** "New API needed." A reviewer cannot evaluate an endpoint that doesn't have a shape.

**Failure mode:** leaving backward compatibility as "TBD". That's the review's blocking question; unanswered, it ends the review.

**Failure mode:** a changed field whose *meaning* shifts while the type stays the same — the most dangerous kind of breaking change, and the easiest to miss. Call it out loudly.

---

## Functional Changes

**Include:** when the change spans several distinct functions and a single architecture section would blur them.

**Enough detail:** per function — current behaviour, proposed behaviour, reason, and technical changes by layer. Three to six lines each. Depth belongs in Business Logic and Error Handling, not here.

**Failure mode:** an essay per function that repeats the architecture section. Five functions × one paragraph beats five functions × one page.

---

## Business Logic

**Include:** when behaviour depends on state (country, tier, verification, balance, time) or when money and entitlements are involved.

**Enough detail:** rules as pseudocode or a decision table — prose hides ambiguity, tables expose it. Then, for each rule, **where it is enforced** and **whether a client can bypass it**. That's an architect's first question about any rule.

Cover the boundaries: exactly at the limit, zero, negative, missing state, and the default for a user whose state isn't in your table.

**Failure mode:** "the system will validate eligibility". Which rule, evaluated where, against which data, and what happens when it fails?

---

## Error Handling

**Include:** whenever anything can time out, partially succeed, or be retried.

**Enough detail:** a scenario → expected behaviour → surfaced-as table. Prioritise the failures that leave **inconsistent state** over the ones that produce a tidy error message. Money moved but record not written is the case worth a paragraph.

For each retry: is the operation idempotent? If not, retrying is a bug, not a mitigation.

**Failure mode:** listing only 4xx validation errors and calling it error handling.

---

## Data / Database Changes

**Include:** any schema change, new persistence, or change to what existing columns mean.

**Enough detail:** tables/columns/indexes with types, nullability, defaults. The index serving each new query on a large table. Migration: required, online or locking, expected duration at production volume, rollback path. Backfill: what existing rows get, and what a half-migrated state looks like to a reader.

**Failure mode:** "migration required: yes" with no duration, no locking answer, and no rollback. On a large table those three facts are the entire risk.

**Failure mode:** adding a nullable column and never saying what `null` means to consumers.

---

## Security & Compliance

**Include:** auth, PII, KYC, money, regulated behaviour, anything user-supplied that reaches a query or a downstream system.

**Enough detail:** name the control and where it's enforced. "Amount validated server-side in `WithdrawalValidator` against the country rule before the payment call" is a control. "We will validate input" is a heading.

Cover: who may call this and where that's checked; what sensitive data is stored or logged; the audit trail for regulated actions; the specific regulatory rule this maps to.

**Failure mode:** a bullet list of security nouns (authentication, authorization, validation) with no verbs. It signals the section was copied, and reviewers stop trusting the rest of the doc.

---

## Testing Strategy

**Include:** when the change is hard to test — state matrices, migrations, external dependencies, concurrency.

**Skip:** when it's the team's ordinary unit + e2e coverage. Saying "we'll write tests" adds nothing.

**Enough detail:** name what makes *this* change hard to verify, then the specific cases. Contract tests for any changed API. A dry-run plan for any migration.

---

## Impact & Risks

**Include:** whenever the change touches a flow that already runs in production.

**Enough detail:** impacted surfaces named concretely (services, clients, jobs, dashboards, other teams' consumers). Risks paired with mitigations — an unmitigated risk is a worry, not a risk assessment. Each risk phrased as something that could actually happen, not a category ("data inconsistency" → "a withdrawal succeeds at the payment provider but the local record fails to write").

Add a **regression scope** paragraph. This is where a "small" change gets its honest cost, and it's often the most useful paragraph in the document for product and QA.

---

## Alternatives & Trade-offs

**Include:** when the choice was genuinely open. When it wasn't, one line — "the obvious alternative, X, was ruled out by constraint Y" — is better than a manufactured comparison.

**Enough detail:** two or three options, honest cons for your preferred one, then a recommendation whose reasoning ties back to the driver in Context. Include "do nothing" as a baseline when the change is expensive.

**Failure mode:** straw-man options that exist to make the chosen one look good. Reviewers spot this instantly and it costs you credibility for the whole doc.

**Failure mode:** listing options with no recommendation. The doc is your engineering judgment; state it and let the reviewer disagree.

---

## Rollout / Deployment

**Include:** when the change can't ship instantly or can't be reversed cheaply — migrations, multi-service deploys, client releases.

**Enough detail:** feature flag and its name; deploy order across services and whether either side can run against the other's old version; migration timing relative to deploy; rollback strategy, including whether rollback remains possible after the migration; the monitoring signal that would tell you to roll back.

**Failure mode:** "rollback: revert the deploy" for a change that ran a destructive migration. If rollback isn't real, say so and design forward-fix instead.

---

## Open Questions

**Include:** always. Every design doc has them; a doc without them usually means they haven't surfaced yet.

**Enough detail:** phrased as decisions you need from the reviewer, with your proposed default where you have one. Mark blocking vs non-blocking.

This is the highest-leverage section in an architect review, because it converts your unknowns into their decisions. It's also where honest assumptions belong: if you couldn't read the current schema or confirm a consumer, record it here rather than inventing a plausible detail.

**Failure mode:** vague questions ("should we think about performance?"). Ask something answerable: "Is a 200ms p99 on the validate endpoint acceptable, given it blocks the submit button?"
