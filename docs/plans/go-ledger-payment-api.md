# Plan: Go Ledger and Payment API

[Status: OK] Planned — 2026-10-28. No phase is complete until its exit criteria are demonstrated.

Learn Go backend development by building a double-entry ledger and payment API whose correctness under concurrency, retries and partial failure is demonstrated with tests and load numbers. The finished project is an interview artifact for fintech backend roles. This document owns the checklist; [ROADMAP §4](../ROADMAP.md#4-其他线详细计划在各自文档里这里只登记状态) tracks its status.

Evidence for the choice of Go: a keyword count over the 2026-10-28 raw JDs in `market/jobs/raw/` found Go mentioned in 14/96 SG and 13/94 MY fintech-backend listings, against 6–8% of general SWE listings. This is a keyword count, not a systematic survey. `market/jobs/trends.json` does not extract Go as a skill, so it reports zero there.

## Boundaries

- **Separate repository, synthetic data only.** No employer code, schema, naming or internal incident details. Build only from public patterns: double-entry bookkeeping, idempotency keys, transactional outbox.
- **Does not replace ROADMAP §1 P0** (deploy the `ai-stock-analysis` FastAPI layer to the cloud). This project sits in the no-clock slot.
- **Overlaps [foundations Phase 2](ai-native-full-stack-foundations.md#phase-2--backend-and-data-correctness)**, which has the same exit criteria. Whether this project replaces that phase's practice vehicle is ROADMAP §5 Q6.
- **AI-native division of labour:**
  - The owner writes the schema, interfaces, and invariant and concurrency tests.
  - The agent implements against them.
  - Before merging, the owner explains every lock, transaction boundary and `context` choice without the agent's help.

## Phase 0 — Design

Status: planned. Suggested effort: 1–2 focused hours.

- [ ] Write a lite design doc (`/design-doc`) covering tables, idempotency semantics, the payment state machine and invariants.

Exit: every invariant is listed and maps to a planned test.

## Phase 1 — Double-entry core and idempotent transfer API

Status: planned. Suggested effort: 8 focused hours.

- [ ] Create `accounts`, `journal_entries` and `postings`.
  - Store amounts as integer minor units or `numeric`, never text or float.
  - Every journal entry's postings must sum to zero.
- [ ] `POST /transfers` requires an `Idempotency-Key`, backed by a table with a UNIQUE constraint.
  - Same key with the same body returns the original response.
  - Same key with a different body returns 422.
- [ ] Run tests against a real Postgres (docker compose or testcontainers), not mocks.

Exit:
- Replaying one request 100 times concurrently produces exactly one journal entry.
- An entry whose postings do not sum to zero is rejected.

## Phase 2 — Concurrency

Status: planned. Suggested effort: 8 focused hours.

- [ ] Send 1000 concurrent debits against one account; the account must never overdraw.
- [ ] Implement two strategies and compare their throughput and p99:
  - `SELECT ... FOR UPDATE` inside a transaction;
  - a conditional update (`WHERE balance >= amount`).
- [ ] Prevent deadlocks in two-account transfers by locking accounts in id order.

Exit:
- After the load test, every account's balance equals the sum of its postings.
- The README shows the strategy comparison with measured p99 numbers.

## Phase 3 — Outbox, webhooks and recovery

Status: planned. Suggested effort: 8–10 focused hours.

- [ ] Write the outbox row in the same transaction as the postings.
- [ ] Delivery worker:
  - claims rows with `FOR UPDATE SKIP LOCKED`, using a lease and `next_attempt_at`;
  - retries with exponential backoff;
  - dead-letters a row after N failures.
- [ ] Payment state machine includes `UNKNOWN`. On timeout, query the (mock) provider, then move to a terminal state.
- [ ] A daily reconciliation job checks each balance against the sum of its postings and reports mismatches.

Exit:
- If the worker is killed mid-delivery, the event still reaches a receiver that dedupes by event id (at-least-once delivery plus dedupe).
- `kill -9` during a transfer leaves no partial state.

## Phase 4 — AI consumer (optional)

Status: deferred until Phase 3 exit.

- [ ] An alert-triage agent consumes ledger events via `anthropic-sdk-go`.
  - Its tools are read-only.
  - Any action requires human approval.
  - A small labelled evaluation set reports accuracy, cost and latency.

## Progression

Suggested total effort: 25–35 focused hours, about 3–4 weekends. These are planning estimates. Scheduling is owned by coach-planner.

Defer Kafka, gRPC, Kubernetes and splitting into microservices until a phase's exit criteria cannot be met without them.

For interviews, describe the patterns, the trade-offs and the measured numbers. Do not mention employer specifics.

First step: run `go mod init`, then write the `CREATE TABLE postings` statement with its `CHECK` constraint.
