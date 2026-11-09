# Finance workbench — durable tasks and decision evidence

[Status: OK] Design-Full · Implemented locally · 2026-11-08

## Problem and acceptance

The Finance Office currently repeats the dashboard and offers a copyable prompt.
The owner cannot continue a financial task, confirm a movement, or retrieve a
saved decision after reload. Replace the prompt with funding tasks, a monthly
allocation worksheet and a cash-flow scenario comparison. Finance opens this
workbench by default; asset and notice desks remain available.

Acceptance comes from the owner's request to do all three proposed actions:
use one real funding flow as a case, replace the prompt-only workstation, and
audit policy before deciding the calculation scope. No broker/bank integration,
model execution, trade, automatic balance posting or policy-target invention.

## Owners and contracts

```text
Finance room [MODIFIED]
  -> /api/finance/workbench [NEW: guarded GET / POST]
  -> Python finance_workbench CLI [NEW: strict commands and snapshot]
       -> private workbench.jsonl [NEW: append-only revisions]
       -> transactions.jsonl [UNCHANGED: read-only evidence]
       -> policy.yaml [UNCHANGED: read-only targets]
```

| Contract | Owner | Consumers | Migration / test impact |
| --- | --- | --- | --- |
| Workflows, transitions and cash-only calculations | `scripts/lib/wealth/workbench.py` | CLI and private API | Additive schema v1; synthetic lifecycle/calculation tests |
| Snapshot JSON | Python Pydantic serialization schema | Generated TypeScript, runtime decoder, web panels | Separate from wealth v4; generated parity test |
| Recorded transactions | Existing activity model and journal | Source selector and linked purchase evidence | Never rewritten or posted twice |
| Policy | Private `policy.yaml`, strict nullable model | Policy audit, emergency-reserve worksheet | Missing/null/invalid remain distinct; no silent defaults |
| Valuation | Existing Python wealth report | Existing assets/notices | No change to valuation or returns |
| Local API boundary | Existing loopback/same-origin pattern | Workbench GET/POST | Reject cross-origin, oversized and malformed writes before spawning Python |

New data is private under `data/finance/`. Missing ledger means an empty board;
malformed ledger fails visibly. Default writes require existing savings/portfolio files in the private finance
directory and verification that the public parent ignores that destination.
An offline private working copy without nested Git metadata is supported; no Git
repository is initialized.
Tests use temporary roots and synthetic facts. Demo uses separate session-local
state and calculations; it cannot write the real ledger or read private policy.

## Business rules

- A funding task has independent steps: redeem, settle, FX, broker transfer,
  purchase and reconciliation. A confirmed purchase never confirms its funding.
- Planned, in-transit, confirmed and explicitly not-applicable are distinct.
  In-transit and confirmed money steps require positive original-currency amount
  and evidence. Unknown execution dates stay null. Reconciliation and skipped
  steps require an explanation; skipped is never presented as an executed leg.
- In-transit amounts remain per currency. They are not subtracted from holdings
  or advertised as spendable cash: overlap with recorded balances is unknown.
- Every write has a request id and expected revision; retries are idempotent,
  conflicting retries or stale revisions fail. Lock/read/validate/append/fsync
  occurs under one lock. Completed records remain in history and can be reopened
  with an explicit revised step rather than erasing evidence.
- Allocation uses an explicitly confirmed amount available after usual bills,
  a near-term reservation and the user's confirmed existing protected reserve.
  Python fills near-term needs first, then the emergency target gap. Any surplus
  stays unassigned; no security, investment ratio or FX rate is invented.
- Scenario inputs explicitly specify starting cash, income, expenses, a cash
  buffer, one-off cost, monthly expense increase, income interruption and horizon.
  Baseline and alternative use the same inputs except those chosen changes.
  Outputs are monthly cash balances, minimum/end balance and first buffer breach.
  No investment returns, tax estimation or success probability is implied.
- Saved worksheets retain inputs, results, source policy fingerprint and date.
  Reviewing/accepting a worksheet records a decision, never a financial execution.
  A changed policy blocks acceptance of an old allocation until regenerated.
- Configured policy values are not evidence that they are still current. The UI
  requires explicit assumption confirmation; missing targets remain listed.

## API and persistence details

`GET /api/finance/workbench` returns Python snapshot schema v1: `as_of`,
`ledger_state`, validated `workflows`, `policy` audit and `purchase_evidence`.
Wealth v4 and activity v1 are unchanged. GET never starts an agent or appends a
record. Responses are private/no-store. POST requires a matching local Origin,
JSON content and a body no larger than 64 KiB; client-supplied paths are rejected.
The fixed Python subprocess is bounded by time/output size and uses JSON stdin.

Synthetic create example:

```json
{"action":"create_flow","request_id":"sample-create","id":"sample-funding","title":"Sample funding evidence","source_event_id":"sample-buy"}
```

Synthetic step update (an unknown execution date stays null):

```json
{"action":"update_step","request_id":"sample-change","id":"sample-funding","expected_revision":1,"step_id":"redeem","status":"in_transit","amount":200,"currency":"MYR","occurred_on":null,"evidence":"Synthetic redemption receipt; settlement pending"}
```

`save_allocation` / `save_scenario` accept `id`, `request_id`, `title` and typed
`inputs`; Python calculates and persists the result. `review` accepts `id`,
`request_id`, `expected_revision`. Every successful POST returns a fresh snapshot.
Invalid fields/evidence/date/precision return 400; absent record 404; stale
revision, conflicting request or changed allocation policy 409; unavailable or
malformed saved evidence 503. Errors never contain raw financial payloads.

Demo uses `?mode=demo`. POST carries `{history:[...],command:{...}}`, or history
alone to restore a session. At most 30 commands are replayed against the synthetic
fixture in a temporary directory; no real ledger/policy/settings are read.
Scenario horizon and income interruption support up to 60 months; cash worksheet
inputs use explicit MYR cents, while movement evidence retains its reported
original currency. These are bounded worksheet/runtime
limits, not investment thresholds or personalised policy defaults.

The private ledger stores full typed revisions with a canonical command digest.
A repeated successful request returns its prior event without a duplicate append;
command conflicts fail. Snapshot rebuilding validates every line and revision
sequence. No migration/backfill is needed. The private initial task links one
existing purchase and does not manufacture its predecessor movements.

## UI and failure states

Page pattern: task queue → selected task and next step → saved results/evidence.
Reuse Button, Input, Textarea, Select, SectionCard, DataState, StatusBadge,
PrivacyProvider/Money/Private and existing world navigation. No new scene geometry.
The financial dashboard remains the detailed holdings view.

Loading, empty, failed read, invalid input, saving, conflict/reload, partial policy,
draft, reviewed and completed states are explicit. Inputs are disabled while
amounts are hidden. Errors retain the user's draft; a lost response can be retried
with the same request id. Refreshed server evidence replaces optimistic state only
after the append succeeds. No success toast precedes durable storage.

## Implementation and verification sequence

1. TDD: create/reload a funding task, independent purchase evidence, idempotent
   and conflicting revisions, invalid evidence, malformed ledger and concurrency.
2. TDD: nullable policy, emergency worksheet and scenario arithmetic against
   independent cash examples; persisted result review and source-change checks.
3. Generated contract, bounded CLI/API bridge and API tests for isolation/errors.
4. UI with real save/reload/review, synthetic browser mutations and conflict paths;
   update verify-web's Finance/Office maps and drive real masked-data reads.
5. Initialize one real task from the existing transaction journal without marking
   unknown steps complete. Save a private policy audit listing missing inputs.

Run focused gates per slice, then make test/design-check and affected browser
journeys. Inspect 1440/390/320 and dark screenshots. Financial write acceptance
must check persisted evidence and unchanged journal/holdings, not only UI text.

## Open questions and limits

No blocking implementation decision. The owner will supply unknown movement
facts, target ratios and current planning assumptions through the resulting UI
or their private files. These missing facts block affected conclusions, not
delivery of a workbench that correctly asks for them. The initial real task is
an evidence-reconciliation case, not a retrospective claim that the proposed
funding route actually happened.


## Local acceptance record

[Status: OK] Funding evidence and cash-only planning are implemented locally.
No trades, transfers, model runs, automatic postings or policy-target edits were
performed. One real purchase-evidence task and a private policy audit were added.
Hashes verify the five existing holdings/balance/journal/history/policy source
files are unchanged. This private working copy has no nested Git metadata; its
existing finance directory is ignored by the public parent and was not reinitialised.

- `make test`: 494 Python tests, 110 web unit/contract tests and typecheck passed.
- `make design-check` and `git diff --check`: passed; two existing chart-series
  contrast warnings remain. Generated workbench schema parity passed.
- New workflow journeys passed against the actual Next/Python demo command path:
  independent funding evidence, durable replay/reload, allocation calculations and
  review, cash scenarios with independently expected amounts, 320/390 dark/reflow.
- API tests prove local-origin/JSON/body-size guards, conflicts and sanitized
  failures; Python tests prove concurrent revision rejection, idempotency,
  malformed sources, explicit unknowns, source-policy changes and cents precision.
- The broad 14-test scene run passed 13. Classic-town's existing pixel-equality
  focus test failed once, then passed unchanged in an isolated rerun. No movement,
  camera or character code was changed by this extension. Both results are kept;
  this remains a test-stability warning rather than a claim of an all-green run.
- Real-data verify-web reads passed for the workbench, monthly/scenario forms,
  390 dark / 320 light and the street's open-task notice. Amounts remained masked;
  every captured real journey recorded zero API writes and zero page errors.
  Screenshots were opened. Scene geometry/assets and navigation are unchanged.

Evidence: ignored `web/test-results/verify-web/finance-workbench-evidence.json`,
`workbench-private-integrity.json`, per-journey screenshots/evidence.json and
`web/test-results/finance-workbench-browser-full/`. The private policy audit is
`data/finance/policy-audit-2026-11-08.md`; all nine unset policy fields remain null.
Legacy portfolio monthly savings remains outside these calculations; the policy
monthly capacity is a displayed reference, never substituted for current available
funds. No commit, deployment or historical record rewrite was requested.
