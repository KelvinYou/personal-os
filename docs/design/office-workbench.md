# Office workbench — Design-Lite

[Status: OK] Implemented and locally verified · 2026-11-03

## Outcome

The live office leads with actionable questions, blocked work and deliverables awaiting human review. Direct-task runs survive browser/server restarts as evidence records; restarting never resumes or dispatches model work. Existing collaboration tasks retain their canonical owner and controls.

Page pattern: overview → next action → evidence detail.
Reused components/assets: office room, task composer, SectionCard, DataState, collaboration database and board.
New design decisions: an attention inbox before the room, persistent run evidence with explicit human review, Solo by default.

## Owners and scope

```text
Owned App Server events [UNCHANGED source]
  -> OfficeExecution [MODIFIED: capture run evidence]
  -> Board.owned_runs in data/office/collaboration.sqlite3 [NEW table]
  -> /api/office/work [NEW: history + review]
  -> office workbench [NEW: attention + results]
Existing collaboration tasks [UNCHANGED]
  -> existing collaboration API -> workbench [NEW read-only projection]
```

| Contract | Owner | Consumers | Compatibility / migration | Verification |
| --- | --- | --- | --- | --- |
| Owned run records and review revisions | Python Board additive table | server bridge, work API, workbench | CREATE IF NOT EXISTS; existing tasks and observation v1 unchanged | temporary-db lifecycle/concurrency tests |
| Runtime final result and file references | OfficeExecution owned events | archive writer, current task | optional history_error; no transcript parsing | fake App Server tests |
| Questions | current execution input_request | inbox links to existing answer form | never replay archived questions | browser flow |
| Collaboration tasks | existing Board tasks | existing board and inbox links | no duplicate task creation or mutation | existing tests |
| Artifact reads | recorded owned file-change path | text preview endpoint | root confinement, no symlink escape, bounded text/plain; no arbitrary path input | API/path tests |

## Data and API

Records contain schema_version 1, task, runtime status, coordinator result, owned agents, recorded file-change paths, timestamps, revision and human review (pending / accepted / rework). No reasoning, command text, raw tool output, secret answers or observation transcripts are archived. Running records from a previous runtime show unknown current liveness, never success. No automatic execution recovery.

GET /api/office/work returns records. POST accepts only {action:"review", task_id, revision, review:"accepted"|"rework"}. Review requires a terminal run; acceptance requires a completed run and nonempty final result. Compare-and-swap revisions prevent stale tabs overwriting a review. Repeated identical review on the same latest record is harmless. A follow-up is a new run, not acceptance of the previous run. A send request ID also identifies its durable run. Reusing that ID after a server restart returns a conflict directing the user to history; it never dispatches the same request again.

GET /api/office/work/artifact?task_id=...&index=... reads only a file-change path retained in that run. Files are current workspace contents, explicitly not immutable historical versions. Result text remains durably available if a file moves or disappears. Binary/oversized/outside-root/unsafe files return an explicit error.

All new routes use same-origin loopback guards and private/no-store responses. Storage remains under ignored data/office. Existing database schema version remains 1 because the new table is additive and old clients ignore it. No backfill can recover prior memory-only replies.

## Failure behavior

| Scenario | Behavior |
| --- | --- |
| Initial archive write fails | Refuse dispatch; surface fixed error |
| Terminal archive write fails | Keep runtime result; show history_error and retry on later snapshot |
| Server restarts during a run | Retain last checkpoint as historical evidence; liveness unknown; no resume |
| History or board unavailable | Preserve last data with explicit unavailable/partial scope; never show all-clear |
| Run ends without final/team evidence | Incomplete, requires attention, cannot accept |
| Stale review revision | 409; refresh record before retry |

## Implementation and acceptance

1. Durable evidence and review: temporary SQLite tests first; migration and stale-write checks.
2. Runtime capture: fake App Server run survives replacement of OfficeExecution; resets preserve history; no foreign events.
3. Workbench and artifact access: inbox actions, result review, file preview and error states; API and browser acceptance.
4. Typecheck, focused office suites and production-build screenshots at desktop, 390px, 320px; inspect light/dark and keyboard controls.

## Trade-offs and open questions

The archive is an evidence table in the existing private store, not a second manual task board. Full chat persistence, desktop-session assignment, immutable file snapshots, scheduling and automation are deferred. No blocking product decision remains for this bounded implementation. Review feedback is recorded as rework; it does not silently start another model task.

## Acceptance and contract review

[Status: OK] Local GO. The owner-to-consumer matrix above covers the additive SQLite table, Python/TypeScript boundary, private storage and existing execution/board consumers. Observation v1, daily logs, finance, external sessions and skill definitions are unchanged. No Critical contract drift remains. Existing design acceptance records describe their historical revisions; architecture and the direct-task entry point now link this extension.

- Python: `python -m unittest tests.test_office_work tests.test_office_collaboration tests.test_office_app_server` — 19 passed. Includes temporary-store reopen, stale-review rejection, incomplete-result rejection, response budgets, private modes and the real stdin/JSON CLI boundary with synthetic configuration.
- Web: from `web/`, `node --test tests/office*.cjs` — 44 passed. Includes owned/foreign file-change attribution, refusing dispatch on archive failure, duplicate requests after runtime replacement, bounded file previews, local API controls and space for editing follow-up drafts.
- `npm --prefix web run typecheck` and isolated production build with `NEXT_DIST_DIR=.next-office-workbench` — passed.
- Production browser workbench flow: answer and focus, file preview, accept, request changes, reaccept, reload, prepare without dispatch, unavailable history, historical activity with unknown current liveness. Synthetic private endpoint evidence; no live model task was submitted.
- Existing task-team browser flow — passed with synthetic endpoints, three actual fixture participants, reload, keyboard controls and preserved scene interactions. Solo is the default; Team remains an explicit choice.
- Desktop 1440px, 390px and 320px at default zoom: no document overflow. Light/dark screenshots inspected. Result/composer anchors account for fixed navigation. Evidence: `/tmp/office-workbench-evidence/` and `/tmp/office-workbench-team-evidence/`.
- Installed production preview history/execution GETs — HTTP 200, schema v1, private/no-store. No inference dispatched by these checks.
- `scripts/check_mermaid.py ARCHITECTURE.md`, `scripts/flow_graph.py --check` and `git diff --check` — passed. Existing architecture diagrams were preserved; derived flow data was refreshed for the new Python adapter.

Verification targets the uncommitted working tree based on `a17c6b90aef1fc03294b940ee40a79a601138223`; no commit, merge or deployment was performed. The pre-existing dirty workspace was retained. Real model compliance and physical-phone performance are not established by synthetic acceptance. File previews show the current file; only result text and run evidence are durable historical records. The history response is bounded by the configured execution message budget and explicitly reports additional records.
