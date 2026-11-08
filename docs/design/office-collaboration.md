# Office collaboration — technical design

[Status: OK] Local collaboration implemented and verified · 2026-11-01.

## Outcome and scope

The office currently observes sessions. This extension adds a persistent task
board, explicit resource claims, handoffs, and an opt-in managed read-only team.
Existing sessions and their source records are never resumed, interrupted or
modified by this extension. Managed execution creates fresh Codex threads.

Design-Full, sized to the execution boundary: the new local write API can start
model work, so dispatch, concurrent state changes and failure recovery need
explicit contracts. The existing observation schema remains version 1.

## Architecture

```text
/office [MODIFIED: link only]
  -> /office/collaboration [NEW: task board]
     -> /api/office/collaboration [NEW: loopback + same-origin]
        -> office_collaboration.py [NEW: CLI + domain owner]
           -> data/office/collaboration.sqlite3 [NEW: private canonical state]
           -> office_team_runner.py [NEW: bounded worker process]
              -> official codex app-server [fresh threads, read-only]
```

One transactional Python owner serves both sessions using the CLI and the web.
The 3D scene and its observation adapter remain independent consumers.

Page pattern: detail with a task workbench. Reused assets: SectionCard,
DataState, Select and dashboard appearance. New decisions: explicit declared
resources versus unattributed observed listeners, task dependencies and a
read-only three-person team. Empty, loading, error, pending dispatch, running,
blocked, review and completed states remain distinct.

## State and API

`GET /api/office/collaboration` returns versioned tasks, resource claims and
recent handoff events. Existing observation sessions are fetched separately;
no titles, prompts or code are added to the sanitized observation snapshot.

`POST` accepts one allowlisted action: `create`, `claim`, `renew`, `handoff`, `finish`,
`resource`, `release`, `team`, or `cancel`. Mutations carry a request id for
idempotency; task updates carry a revision to reject stale writes. Concrete
creation: `{"action":"create","request_id":"uuid","title":"Review layout",
"description":"Inspect spacing","depends_on":[],"resources":[]}`.
Session claim: `{"action":"claim","request_id":"uuid","task_id":"uuid",
"revision":0,"session_id":"session-uuid"}`.

Dependencies must exist and must be completed before a task can be claimed.
Only the current assignee can hand off or finish a claimed task. Finishing
requires a written result. Handoff moves a task to `review`, records the result
and intended recipient, and releases resources; the recipient explicitly claims
it before proceeding. No session exit or ended turn completes a task.

Resource names are explicit `path:relative/path`, `port:3000`, or
`build:relative/path`; paths are normalized and overlapping path claims conflict.
Claims are advisory coordination, not filesystem locks. Expiry makes a claim
available but does not stop its former owner's process. Renew through
the task's `renew` action or recording a standalone resource again. Unknown
live listener ownership stays unknown.

Managed `team` creates a coordinator task. The runner obtains a structured
two-task plan, creates two worker tasks, executes them concurrently in fresh
read-only Codex threads, then asks the original coordinator to synthesize their
results. Parent ids, thread ids and events are explicit. There is no automatic
recursive delegation. Users start this model work deliberately; page loading
does not run inference. Cancelling a managed team is cooperative and interrupts
only runner-owned threads. A crashed runner must not appear successfully done.
Managed teams reject manual dependencies/resources: the first execution lane
is read-only. Coordinator-runner capacity remains occupied during cancellation
cleanup and is released only after its owned clients close.

## Privacy and execution

Tasks, user-authored prompts/results and events live only in private `data/`.
No real data is copied to fixtures or public docs. GET is private/no-store.
Writes require loopback Host, matching Origin and JSON content type; cross-site
requests are rejected before reading or writing state. No browser-supplied shell
command, executable, working directory, transport address or model override is
accepted. The bridge uses fixed argv and stdin JSON, never a shell.

App-server uses the installed official executable and existing login, default
model, `approvalPolicy: never`, and explicit read-only sandbox on thread and
turn creation. Any approval/tool-input server request is declined, never
silently approved. This first managed lane reviews and investigates; writing
development teams need isolated workspaces and a separate follow-up contract.

Limits and enablement belong to optional `office.collaboration` in the owner's
thresholds. No global daemon, hooks, Git commits or remote exposure are added.
Canonical state uses SQLite transactions and private directory permissions.
Existing installs without collaboration config show an explicit unavailable
state. No migration or backfill of observation data is required.

## Failure and recovery

| Condition | Behaviour |
|---|---|
| Concurrent claim / stale revision / active resource overlap | 409; preserve first owner |
| Repeated request id | Return original result; do not dispatch twice |
| Invalid payload / unknown action | 400 without mutation |
| Missing configuration / unreadable store | 503; no fake empty success |
| App-server startup, auth or model error | Managed task blocked with bounded diagnostic code |
| Timeout / cancellation | Interrupt owned turn, close owned process; never complete task |
| Partial child failure | Coordinator blocked; retain completed child evidence |
| Runner crash | Expired heartbeat shown as interrupted/blocked; no automatic duplicate retry |

## Implementation and validation sequence

1. Task lifecycle and transactional ownership: tests first, then implementation.
2. Resource conflicts, handoffs, dependencies and idempotency: incremental tests.
3. Official app-server client and managed team runner: protocol fixture and
   deterministic fake executable, then a real bounded read-only team smoke.
4. API and workbench: API boundary tests, typecheck, isolated build and browser
   creation/claim/handoff/rotation checks. Keep existing running servers intact.
5. Review privacy, compatibility, cancellation and incomplete-run handling;
   record actual verification and remaining gaps here.

## Alternatives and open decisions

Reading transcripts cannot send tasks. Attaching another writer to the desktop
client's live thread is not needed and risks interrupting existing work. Fresh
managed threads plus an explicit pull workflow for independent sessions are the
chosen first release. Existing first-party thread tools were inspected: they
can coordinate within this agent session but are not an authenticated backend
interface exposed to the local web application.

No blocking product question remains under the user's instruction to build.
Non-blocking follow-ups: enable write-capable isolated worktrees only after a
separate review; add 3D meeting animations only from explicit handoff events.

## Verification and operating record — 2026-11-01

The final web build passed with `NEXT_DIST_DIR=.next-collaboration-review`.
The preview is bound to `127.0.0.1:3002`; existing services on 3000, 3001 and
the concurrent direct-task preview were preserved. Launch from `web/` with
`NEXT_DIST_DIR=.next-collaboration-review npm run start -- --hostname 127.0.0.1 --port 3002`.
The private owner configuration enables collaboration with explicit budgets.
No Git staging, commits, submodule changes or background daemon were added.

Full Python discovery passed 400 tests; all 28 current web tests passed.
Focused Office tests were repeated after the final runtime cleanup guard.
Production build includes type validation; `git diff --check` passed.
Tests use temporary synthetic stores and executables, never private records.

Two real managed teams completed coordinator planning, two parallel worker
turns, and coordinator synthesis using the installed official Codex CLI. Their
static findings exposed renewal, managed-child publication, cancellation
capacity, stale recovery and process-cleanup defects. These were corrected
with focused regressions. The leader-exits-first test confirms cleanup of a
surviving same-process-group child, with bounded waits. Real model output
remains evidence rather than an automatic approval of its own implementation.

Chrome verified real task creation and claim; Safari displayed the persisted
board, managed parent/child outcomes and private resource declarations.
The actual HTTP boundary verified handoff -> recipient claim -> result-based
completion and resource release. Foreign/missing Origin writes returned 403;
API tests cover malformed/oversized payloads, unknown actions and conflicts.
Native Safari text-entry automation was unreliable, so handoff/completion were
verified over HTTP rather than claimed as a fully automated browser flow.

| Contract owner -> consumer | Result |
|---|---|
| Optional private thresholds -> Python configuration -> CLI | Compatible with existing Office settings and concurrent direct-task settings |
| SQLite board -> CLI -> local write API -> web workbench | Revision, idempotency, dependencies, handoff recipient and resource checks agree |
| Official App Server -> runner -> explicit task/thread linkage | Fresh read-only threads only; runtime confirms the requested sandbox |
| Existing observation -> 3D scene | Schema 1 unchanged; cosmetic workers are not treated as authenticated users |
| Public code/tests/docs -> private tasks/results | Personal content stays in `data/office/`; public fixtures are synthetic |

[Status: Warning] Resource claims are advisory and must be renewed. Session
identity is declared in this single-user localhost tool, not an authentication
boundary. Existing desktop sessions join explicitly using the copied prompt or
CLI; they are not silently taken over. Phone layouts, long-duration load,
PID-reuse recovery and detached descendants that deliberately leave the owned
process group are not certified. Write-capable teams and 3D meeting choreography
remain separate follow-ups, not implied by a completed read-only task.

## Native task teams — implementation contract (2026-11-01)

[Status: Warning] Implementation and acceptance in progress. This section extends
rather than replaces the managed read-only board above. Design-Full is retained
because owned execution, cancellation and session isolation cross a permission boundary.

At initial inspection, the scene had only one observation list; no second
managed worker was rendered. Direct execution waited for transcript discovery
and lost task/agent relationships. The concurrent skill-roster change is
preserved in the main office; temporary participants use `/office/team`. Adding an execution list naively
would duplicate the same thread. Deduplicate at the presentation boundary,
not by suppressing canonical observations in Python.

```text
Web composer [MODIFIED: explicit Solo / Team choice]
  -> execution API [MODIFIED: optional collaboration mode]
    -> owned Codex App Server [EXISTING: native delegation]
      -> task + agents + lifecycle evidence [NEW: private execution projection]
        -> room projection [NEW: reconcile by exact thread id]
          -> /office/team scene, participant list, task detail [NEW]
Local transcript observation [UNCHANGED] -> room projection
```

Task is the user's requested work for one run; agent is a participant; thread
is the participant's conversation identity; turn is one execution attempt.
Parent/child identity comes only from owned runtime events, never timestamps,
cosmetic names, matching prompts, or skills. The runtime remains the orchestration
owner. A browser cannot choose or resume arbitrary threads. Native teams do not
create board records or imply advisory resource locks.

The existing send payload accepts optional `collaboration: "solo" | "team"`;
omission preserves solo behavior. Team mode explicitly requests two independent
read-only subagents and coordinator synthesis. The root retains existing
workspace-write permissions; child read-only instructions are a scope constraint,
not an independent sandbox. No new write-capable parallel development workflow
is claimed. Native capability is verified against installed CLI 0.164.0 generated
protocol and a real bounded delegation. If delegation is absent or incomplete,
the UI must say so rather than fabricate two characters or declare team success.

Execution response v1 gains additive `task` and `agents` fields. Task has an id,
instruction, collaboration mode, lifecycle status and start time. Each agent
has its own id, task id, thread id, parent id, role, assignment, status and bounded
result. Results and assignments stay in the private execution API. Observation
v1 stays unchanged. No disk migration/backfill; existing in-memory conversations
are reset by a server restart as before.

Room identity is exact thread id. Execution evidence wins over an observation
of that same thread, including when the execution connection is unavailable:
active owned workers become unknown, not falsely live from old transcript data.
The permanent skill roster stays in the main office. The current task links
to `/office/team`, a separate 3D view of temporary runtime participants. Local
observations remain evidence records rather than new permanent employees. Cosmetic character names do not establish agent identity.
A completed runtime turn is not proof the user's acceptance criteria passed.

| Failure | Required behavior |
|---|---|
| Duplicate Send / lost response | Existing request-id deduplication includes mode |
| Foreign thread or stale turn | Ignore; never reveal foreign content |
| Parent finishes while a child is active or no team appears | Mark task incomplete; no fabricated success |
| Child fails or is interrupted | Preserve evidence and expose incomplete work |
| Stop / deadline / runtime loss | Stop owned process tree; pending agents become interrupted or unknown |
| Observation fails | Owned runtime team still renders |
| Execution poll fails | Retain last evidence, mark active owned agents unknown |
| Reload / server restart | Reconnect to memory / explicit empty state; no automatic replay |

Page pattern: detail with inline composer and task participants.
Reused components/assets: office scene/characters/status, shared Select, existing
composer and conversation; existing observation parser remains strict.
New design decisions: the task team has its own 3D view; an explicit team choice
requests delegation, and real participant evidence drives labels and details.
States: ready, connecting, running, waiting, partial, stopped, error, completed
turn, unavailable, and demo remain distinct.

| Contract owner | Consumers | Version/migration | Verification |
|---|---|---|---|
| App Server owned events | execution projection, API | installed protocol; no source history edits | real smoke + protocol regression |
| Execution snapshot | composer, room reconciliation | additive v1; memory only | API and projection tests |
| Python observation v1 | observation view, reconciliation | unchanged | existing Python/TS fixture tests |
| Task/agent mapping | scene, list, detail | new browser projection | duplicate identity and disconnected tests |

Implementation order: (1) protocol probe and task/agent regression, (2) runtime
lifecycle and cancellation, (3) room identity regression and UI, (4) production
build, automated browser flow at desktop/390px/320px, real team smoke, contract
review. Financial/daily-log contracts, board schema and external integrations
are outside scope. No blocking product decision remains under the user's
instruction to do all three proposed steps.
