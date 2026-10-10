# Plan: AI-native Full-stack Foundations

[Status: OK] Planned — 2026-10-02. No phase is complete until its exit criteria are demonstrated.

Build independent judgment when using AI to write software, and learn to ship LLM features with measurable behaviour. This document owns the learning checklist; [ROADMAP §4](../ROADMAP.md#4-其他线详细计划在各自文档里这里只登记状态) tracks its status.

Use TypeScript, React/Next.js and PostgreSQL as the main learning stack. Keep Python for data work and model experiments. Diagnose existing knowledge first and skip topics whose exit criteria are already met.

This is a learning plan, not a change to Personal-OS architecture: its private Markdown/YAML sources and local-only dashboard remain governed by [ARCHITECTURE.md](../../ARCHITECTURE.md). Learning exercises use synthetic data in an isolated sandbox. Deployment practice supports the existing ROADMAP P0 backend/cloud milestone; it does not authorise deploying Personal-OS or publishing private data.

## Phase 1 — Execution and interface fundamentals

Status: planned. Suggested effort: 6–10 focused hours.

- [ ] Practise references/mutation, closures, promises, exception propagation, and compile-time types versus runtime validation.
- [ ] Diagnose React state snapshots, stale closures and out-of-order responses.
- [ ] Build accessible forms with explicit loading, empty, error and cancellation states.

Exit: predict an async failure before execution, reproduce it, explain the cause independently, and show a meaningful regression test. Repeat with changed inputs without consulting the earlier answer.

Resource: [Thinking in React](https://react.dev/learn/thinking-in-react).

## Phase 2 — Backend and data correctness

Status: planned. Suggested effort: 8–12 focused hours.

- [ ] Trace HTTP requests through validation, authentication, server-side authorisation, persistence and response handling.
- [ ] Practise SQL joins/NULL, schema design, constraints, indexes and query plans.
- [ ] Demonstrate transaction boundaries, concurrent updates, idempotency, retries and partial failure.
- [ ] Use a real test database for cases that mocks cannot establish.

Exit: demonstrate that concurrent or repeated requests preserve a stated invariant, unauthorised requests fail, and failures leave a defined recoverable state. Explain why a database transaction does not include arbitrary external API effects.

Resource: [PostgreSQL tutorial](https://www.postgresql.org/docs/current/tutorial.html).

## Phase 3 — Reliable LLM features

Status: planned. Suggested effort: 6–10 focused hours.

- [ ] Build structured extraction/classification; validate shape and assess factual correctness separately.
- [ ] Handle context limits, streaming, cancellation, timeouts, failed calls and per-request cost.
- [ ] Implement one read-only tool with server-enforced input validation and authorisation; treat retrieved text as untrusted input.
- [ ] Start retrieval with SQL or text search, preserve source attribution and access filters, and handle missing evidence explicitly.
- [ ] Add embeddings or autonomous decisions only after identifying a concrete limitation of the simpler workflow.

Exit: malformed output, unsupported claims, unauthorised tool requests and tool failures have defined behaviour; users can review generated content before saving it.

Resources: [AI SDK course](https://vercel.com/academy/ai-sdk), [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents).

## Phase 4 — Evaluation and operations

Status: planned. Suggested effort: 4–8 focused hours.

- [ ] Build a small evaluation set covering ordinary cases, ambiguity, unsupported claims, access violations and tool failure.
- [ ] Compare implementations using classification accuracy, unsupported claims, latency and cost; inspect failures and repeat variable model trials.
- [ ] Trace failed requests with structured logs, excluding secrets and sensitive payloads.
- [ ] Practise deployment, secrets, migrations and rollback within the existing P0 backend/cloud milestone; reuse its delivery checklist.

Exit: explain an implementation choice with evaluation evidence, diagnose a failed request from its trace, and demonstrate safe recovery from a failed deployment or migration. Code regression tests and model-quality evaluations remain distinct; Personal-OS's `make eval` audits agent sessions and is not this feature-evaluation gate.

Resource: [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents).

## Practice vehicle and progression

Use one synthetic support-ticket exercise throughout: form/database/list/detail → access checks and duplicate handling → AI classification/summary with editable preview → read-only ticket search and evaluations. Keep it bounded as a learning sandbox; reuse suitable existing project code rather than starting a second production product or replacing P0.

Advance by demonstrated exit criteria, not tutorial completion. Suggested effort is 24–40 focused hours, with roughly 60% on software foundations, 30% on LLM features and 10% on operations. These are planning estimates, not proficiency or market measurements. Scheduling remains owned by coach-planner and the private standing protocol.

First diagnostic: spend 30 minutes on a small TypeScript async function, predict an older response arriving last, reproduce the failure, fix it, and add one regression test. Form an explanation before asking AI to challenge it.

Defer framework collecting, multi-agent orchestration, fine-tuning and Kubernetes depth until a concrete requirement justifies them. This plan does not claim a systematic hiring survey or an independent assessment of current proficiency.
