# Office direct tasks — execution contract

Current extension: [office workbench](office-workbench.md) adds durable run evidence and human acceptance. Full chat remains memory-only; the composer now defaults to Solo. Earlier acceptance records below describe their original revisions.

[Status: OK] Direct tasks implemented and locally verified · 2026-11-01.

[Status: Warning] Independent merge review and the visual gaps below remain open.

Design-Full boundary, kept concise: this adds local command execution and private
conversation content to a previously read-only page. User authorization: build
web task entry, live replies, work status and stop on `/office`.

## Outcome and architecture

```text
/office + DirectTask [MODIFIED: composer, replies, observed-worker selection]
  -> /api/office/execution [NEW: local GET snapshot / POST actions]
    -> OfficeExecution [NEW: one process-owned session, bounded memory]
      -> official codex app-server [NEW: stdio, fresh owned thread]
    -> office_execution_config.py [NEW: validated private thresholds]
```

The server owns one web conversation shared by local tabs. Only explicit Send
starts inference; GET never starts Codex. Follow-ups use the owned thread.
Existing observation and collaboration APIs remain unchanged. Resumption is
restricted to the privately remembered web-owned thread after a stop. No
arbitrary thread resume, client executable, cwd, transport or model is accepted.

Page pattern: detail with an inline task composer. Reused assets: office styles,
DataState, existing character profiles and 3D scene. New decisions: collapse the
conversation during fullscreen, explicitly label the directly managed worker.
States: ready, starting, working, waiting for input, stopping, idle, interrupted,
error, unavailable and disconnected. Empty replies never establish success.

## API and lifecycle

GET returns `{schema_version:1, thread_id:null|string, turn_id:null|string,
status, activity, error:null|string, messages:[], input_request:null|object,
poll_interval_ms, max_prompt_chars, updated_at}`. Messages contain only id,
role (user/assistant), text. No reasoning or command output is exposed.

POST `{action:"send", request_id:"uuid", text:"Fix the header"}` starts or
continues the owned session. POST `{action:"stop", request_id:"uuid"}` interrupts
only the owned turn. POST `reset` closes the owned idle session; the next Send
creates a new thread. POST `answer` carries the pending input request id and
answers. Request ids deduplicate successful actions within bounded server
memory. Busy send/reset and stale answers return 409. Invalid/oversized bodies
return 400/413. Runtime/configuration failures return sanitized errors, never
fake successful results. A timed-out start is never automatically retried.

The busy flag is set synchronously before initialization. Events are filtered
by owned thread and active turn; early turn notifications are retained by
buffering notifications until the start RPC reply supplies the owned turn id. A stop during
startup prevents launch or interrupts a turn that has already started. Stop
closes the entire owned process tree, including detached tool children, even
when the server acknowledges interruption. The next Send resumes only the
remembered owned thread through a fresh process. A bounded turn deadline closes an unresponsive owned process and surfaces interruption/error.

## Execution and privacy

Both thread/start and turn/start explicitly enforce workspace-write and never
approval. The fixed workspace is the repository root; network is disabled.
Hooks are disabled for this owned process. The agent is instructed to preserve
unrelated work and not commit, push, deploy, send external messages or create
subagents unless the user's task expressly authorizes it. Sandbox enforcement
belongs to Codex; inherited project full-access defaults are overridden.
Unexpected permission requests are declined and shown as an actionable error.
User-input requests can be answered in the web conversation.

Host must be loopback, Origin must match for writes, Sec-Fetch-Site must not be
cross-site, Content-Type must be JSON. Check before starting processes or
reading state. No CORS grant. Responses are private/no-store. Fixed executable
and argv, JSON on stdin; never a shell. Raw runtime stderr/RPC errors are hidden.
Private prompts/replies stay in process memory and Codex's own private session
store. They never enter the observation API, public fixtures or public docs.

`OfficeExecutionCfg` in `office.execution` owns enablement and budgets. Missing
configuration disables execution while observation continues. No historical
migration/backfill. A web-server restart drops the in-memory connection and
conversation view; Codex retains its own history. No automatic reattachment or
replay after server restart. Closing a browser tab does not cancel work. Stop is
explicit and cannot undo edits already made. Reset does not delete Codex's source history.

## Implementation sequence and acceptance

1. Protocol tracer: fresh thread, live reply, continuation; deterministic fake
   executable with payload expectations based on official App Server docs.
2. Isolation, duplicate send, stop race, timeout, user input and process loss.
3. Local API checks and private configuration; enable only this requested lane.
4. Inline UI + managed character, types/tests/build, real bounded edit and
   follow-up/stop smoke, desktop/320px/390px browser and fullscreen checks.

Owner → consumer map: private thresholds → Python validation → Node runtime;
official JSON-RPC → execution state → private UI; existing transcript adapter →
scene; privately owned thread id → automatic room selection. Observation schema v1 stays unchanged; no finance/daily-log change.

Alternatives: transcript reading cannot execute; attaching to the active desktop
thread risks two writers. Fresh web-owned threads provide explicit ownership.
The existing read-only team board serves a different operation and is preserved.

Open questions: none blocking. Persistent web history and isolated worktree
execution are follow-ups. Independent permission/isolation acceptance remains
required before merge; this task does not request a commit or merge.

Source: [official App Server](https://learn.chatgpt.com/docs/app-server), inspected
2026-11-01; installed CLI 0.164.0 is the runtime acceptance target.


## Local acceptance record — 2026-11-01

Base HEAD `a17c6b90aef1fc03294b940ee40a79a601138223`, uncommitted working
changes. Existing concurrent collaboration/home/office work was preserved.
Production preview uses `.next-office-direct`, bound to `127.0.0.1:3003`;
other servers were not replaced. The owner's execution block is enabled;
the public example remains disabled.

- `make test`: 399 Python tests, 28 Node tests, web typecheck, Mermaid and
  knowledge gates passed. Final execution tests include fresh/continued threads,
  foreign-event filtering, duplicate requests, startup cancellation, private
  runtime failure, deadlines, input answers, permission refusal, detached-child
  cleanup and resuming only the stopped owned thread.
- Isolated production build and `git diff --check` passed. `make flows`
  regenerated the derived graph for the new config adapter.
- Native Chrome, macOS, desktop: actual web Send created an ignored disposable
  acceptance file and read it back; a second instruction changed the same file
  using prior conversation context. Reload during execution retained both the
  same thread and messages; the 3D room selected its observed worker.
- Stop defect reproduced before the fix: `turn/interrupt` ended generation while
  the test sleep process stayed alive. A deterministic detached-child regression
  failed before cleanup and passed after it. On the final runtime, web Stop
  removed the real sleep process before its deadline; a follow-up resumed the
  same owned thread and returned the requested reply. Existing sessions remained
  outside the execution API's control.
- Dark desktop fullscreen showed the room, composer, transcript and Stop button.
  At emulated 390px, DOM measurement reported viewport/page width both 390px,
  direct panel 366px. 320px, light-theme and enlarged-text acceptance remain
  unverified after native browser focus changed during inspection. No responsive
  certification follows from the single measured width.
- Browser-only execution is covered through native Chrome. The SOP's automated
  Playwright full-flow check was not run: this session exposes native computer
  use rather than a supported browser automation surface. Real question/permission
  prompts are protocol-tested with synthetic executables, not triggered in live
  model work. These are acceptance gaps for merge, not a claim of full release.

Canonical model history stays with Codex. The web view is bounded, memory-only
and shared by local tabs. Server restart clears that view; no automatic replay
or existing-desktop-thread takeover occurs. Stop cannot undo prior file edits.

## Native team integration — 2026-11-01

The send payload now optionally accepts `collaboration: "solo" | "team"`.
Omission preserves solo behavior. The web composer defaults to an explicit Team
choice; Send authorizes the coordinator to request two read-only investigation
subtasks and synthesize their results. Native Codex orchestration owns delegation.
The separate managed Python board remains a fixed read-only workflow.

The additive v1 execution snapshot includes `task` and `agents`. The current
run has a separate task id even when continuing the same root thread. Owned
parent-turn events establish membership; child completion additionally requires
matching `rootTurnId`. Private child results never enter the public-safe
observation projection or the root conversation stream. A missing final result,
failed/interrupted child or missing two-agent evidence produces `incomplete`.
Any still-active known children are stopped with the owned runtime when the
parent finishes early. Stop and timeout preserve the completed evidence.

Room reconciliation lives in `web/lib/office-room.ts`: exact thread id gives one
participant, with owned runtime evidence preferred to a duplicate transcript.
Disconnected execution cannot borrow a misleading live state from an old local
record. The room now uses permanent skill employees; sessions and native team
participants are work records, not additional people. Selecting a task member
focuses its assigned skill employee when available; full native participant
results remain in the task panel. Starting a task never switches the scene back
to session identities. See [the skill employee contract](office-skill-employees.md).


The installed CLI 0.164.0 exposes `subAgentActivity` and
`turn/completed.rootTurnId`; the implementation also handles the generated
`collabAgentToolCall` shape. Parent ids are never inferred from display names.
These contracts and the verification record are maintained in
[office collaboration](office-collaboration.md#native-task-teams--implementation-contract-2026-11-01).
