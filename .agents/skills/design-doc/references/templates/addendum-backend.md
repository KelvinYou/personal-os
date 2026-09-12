# Backend Addendum

Attach to a Design-Lite or Design-Full doc when the backend change involves new persistence, new integrations, concurrency, or async work. Skip it when the backend change is a passthrough field.

Include only the subsections with real content.

---

## Backend Design

### Service & layering

Which services/modules change, and which layer owns the new logic (controller / service / domain / repository). If a rule could plausibly live in two places, say why you chose one — that's the decision a reviewer wants to see.

### Data model

New or changed tables, columns, indexes, with types, nullability, and defaults. For each new query on a large table, the index that serves it. Foreign keys and cascade behaviour. Enum values and how new ones get added later.

### Transactions & consistency

What's inside one transaction and what isn't. Where the boundary sits relative to any external call — a payment call inside a DB transaction is a common and expensive mistake.

What happens on partial failure: compensating action, outbox, reconciliation job, or accepted inconsistency with a stated window.

### Idempotency & concurrency

For anything that creates, charges, or transfers: the idempotency key, its scope, and how long it's retained. What two concurrent identical requests produce.

Locking or optimistic-concurrency strategy for contended rows, and what the loser of the race sees.

### External integrations

Each dependency: what's called, timeout, retry policy, and whether the retry is safe (is the call idempotent?). Behaviour when it's down — fail open or fail closed, and why that's the right choice for this operation.

Circuit breaker or rate limit, if any.

### Async work

New jobs, queues, events, or schedules. Ordering guarantees you rely on, delivery semantics (at-least-once means you need idempotency), and how failures are retried and eventually surfaced. What happens to messages produced during a deploy.

### Migrations

Order relative to code deploy. Whether the migration is online, how long it runs on production data volumes, whether it locks. Rollback plan — and, honestly, whether rollback is still possible after it runs.

Expand/contract phasing when a column changes type or meaning.

### Authorization

Who may call each new operation, checked where, and against what. Note any check that currently exists only in the client and is now being moved or duplicated server-side.

### Observability

Logs, metrics, and traces that would let someone debug this at 2am — and the specific alert that would catch it failing. Note anything sensitive that must not be logged.

### Performance

Expected request volume and the queries per request. Anything N+1, anything unbounded (a query with no limit, a list that grows forever), anything on a hot path.
