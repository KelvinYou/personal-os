# Office attention radar — technical design

[Status: OK] Implemented locally · 2026-11-08 · **Tier:** Design-Full · **Observation schema:** 2

This document owns the office's purpose, the observation v2 contract, the
attention-zone rules, the radar scene and the agent-wait metric. It supersedes
the scene identity in [skill employees](office-skill-employees.md) and freezes
[garden town](office-garden-town.md) / [courtyard](office-courtyard.md) as the
optional classic view. Execution, collaboration and run evidence keep their own
owners ([direct tasks](office-direct-tasks.md), [collaboration](office-collaboration.md),
[workbench](office-workbench.md)).

The room is the **Lab**, the first building of [the office town](office-world.md);
Finance stands beside it on the same floor. Its attention semantics and
observation contracts remain owned here.

## 1. Purpose and the question it answers

> Look for three seconds and know which agent is waiting for me, which are
> working, and which are ready for review.

Running agents in parallel makes human attention the bottleneck, not
generation: agents spend more time waiting for review than working (Superset,
Mergify, agentpatterns.ai, 2026). Anthropic's Agent View groups sessions only
by *needs input / working / done*. Pixel-office projects that earn trust map
movement to real tool activity; decorative wandering reads as a screensaver and
erodes trust when the picture disagrees with the system.

The previous direction drifted into two other products: a walkable game (garden
town, first/third person) and an execution console (tasks, board, posts). Both
remain available, but neither is the default anymore.

| Rule | Consequence |
|---|---|
| Position is status | A person's zone is their attention zone, never their skill |
| One person per live session | Skills become a badge; subagents are small linked people |
| Movement comes only from evidence | A walk happens when a zone or tool changes; no idle routines |
| Every source is first class | Codex and Claude Code are both observed, read-only |
| Time is a dimension | Today's activity can be replayed from recorded state changes |
| The office measures its own bottleneck | Agent wait on human is reported weekly |

Page pattern: overview (radar scene + attention queue) → detail (selected session) → evidence (timeline).
Reused components/assets: OfficeWorkspace shell, DataState, Select, Button, shared character builder, scene standard, PostsLibrary, OfficeWorkbench, DirectTask.
New design decisions: four attention zones, tool stations, subagent scale, a day timeline with replay, opt-in browser notifications, `/posts` route.

## 2. Architecture

```text
~/.codex/sessions/YYYY/MM/DD/*.jsonl      [UNCHANGED source]
  -> lib/office/monitor.py  CodexAdapter  [MODIFIED: tool kind, segments]
~/.claude/projects/<slug>*/<id>.jsonl     [NEW source, read-only]
~/.claude/projects/<slug>*/<id>/subagents/agent-*.jsonl
  -> lib/office/claude.py   ClaudeAdapter [NEW]
       -> lib/office/attention.py         [NEW: zone + wait rules, single owner]
       -> Monitor.snapshot  schema v2     [MODIFIED]
       -> data/runtime/ai-office/projection.json [cache, rebuildable]
  -> office_monitor.py --json -> /api/office/state -> office-contract.ts v2
       -> projectRadar (office-radar.ts)  [NEW view model]
       -> RadarScene / AttentionQueue / OfficeTimeline [NEW]
lib/office/waits.py  [NEW]  -> agent_wait.py (make agent-wait) + weekly_synthesis §4.6
```

Both adapters read the client's own records, exactly like the original Codex
observation. One project-scoped Claude Code hook adds exact permission waits
(§4.1); no other client configuration is changed.

## 3. Observation schema v2

Breaking change, owned by Python. `parseOfficeSnapshot` accepts only v2;
fixtures and browser mocks move to v2 in the same change.

Snapshot keys: `schema_version: 2`, `source_status`, `source: "local_transcripts" | "demo"`,
`source_coverage: {codex, claude}` each `"connected" | "unavailable"`, `observed_at`,
`poll_interval_ms`, `stale_after_seconds`, `warnings`, `sessions`.

Session keys (v1 keys plus four):

| Key | Values | Meaning |
|---|---|---|
| `runtime` | `codex`, `claude`, `demo` | Which client wrote the record |
| `parent_session_id` | id or null | Claude subagent → its parent session |
| `role_ids` | `[]` or `[skill]` | Claude `attributionSkill` when it matches `^[a-z0-9][a-z0-9:-]*$`; Codex stays empty |
| `attention` | `needs_you`, `working`, `review`, `done` | Zone (§4) |
| `attention_since` | ISO or null | When the session entered this zone |
| `tool` | `edit`, `read`, `command`, `web`, `agent`, `think`, `other`, null | Current station while working |
| `segments` | `[{at, state, attention, tool}]` | Change points, oldest first, bounded by `max_segments` |

Privacy is unchanged: only fixed labels, tool kinds, timestamps and ids leave
the adapter. No prompt, response, tool argument, tool output, title or path is
read into the projection. The Claude `ai-title` and message text are never parsed.

## 4. Attention rules (single owner: `lib/office/attention.py`)

| Evidence | State | Attention |
|---|---|---|
| Explicit input request (Codex `request_user_input`; Claude `AskUserQuestion`, `ExitPlanMode`) | waiting | needs_you |
| Turn failed | error | needs_you |
| Claude tool call without result for ≥ `pending_tool_seconds` | working (or unknown once stale) | needs_you, label "Tool pending: approval or long run" |
| Fresh activity | working | working |
| Turn ended ≤ `review_window_seconds` ago | idle | review |
| Turn ended earlier, completed, or stale unknown | as observed | done |
| Pending/waiting older than `wait_cap_seconds` | as observed | done (abandoned, not waiting) |

The pending-tool rule is a heuristic and says so in its label: Claude Code
does not record an open permission prompt, and a long test run looks the same.
It applies only to sessions without the hook signal below.

### 4.1 Exact permission waits (hook signal, 2026-11-08)

`.claude/settings.json` runs `scripts/office_signal.py` on `SessionStart` and on
`Notification` with `permission_prompt | elicitation_dialog | elicitation_url_dialog`.
It appends `{session_id, kind: hooked|prompt, at}` to private
`data/runtime/ai-office/claude-signals.jsonl` (0600, rotated at 512 KB to the
newest 2000 lines). Message text, tool input, cwd and transcript path are
dropped. The script is stdlib-only, always exits 0 and is ignored when `data/`
is absent. Owner: `lib/office/signals.py`.

| Signal | Effect |
|---|---|
| `hooked` | The session reports prompts exactly: a pending tool stays *working* (a long run), no heuristic flag |
| `prompt` while the transcript is mid-turn | `input` change point → *needs you*, label "Waiting for your approval", since the prompt time |
| Next non-pending transcript point (tool result after approve/deny, interrupt, end) | Closes the wait; replay and the weekly metric include it |
| `prompt` outside a turn, or for a subagent file | Ignored |

Limits: Claude Code reads hooks when a session starts, so sessions already
running at install time keep the heuristic. An approved command's run time is
counted inside its wait, because no hook fires when the dialog is answered.

### 4.2 Phone push (ntfy, 2026-11-08)

The first real week showed long waits cluster when only 1–2 sessions are in
play (§5): the owner is away from the desk, where a browser notification is not
seen. The same hook therefore pushes to the phone when `office.push.enabled`.

| Trigger | Push |
|---|---|
| `permission_prompt` / `elicitation_*` and the transcript unchanged for `approval_delay_seconds` (default 90) | "Agent needs your approval" (high priority) |
| Claude Code `idle_prompt` (turn ended, about 60 s without input), when `idle_turns` | "Agent is waiting for you" |
| Claude Code `SessionStart`, when `finance_attention` and a Warning/Critical id in the wealth report's `attention[]` was not open at the last run (`scripts/finance_push.py`, state in `data/runtime/finance-push.json`; `make finance-push DRY=1` previews) | "Finance needs attention" |

- Text is fixed (`lib/office/push.py` `MESSAGES`): no session, name, path or command is sent. The random private `topic` is the only access control on public ntfy.sh; anyone holding it can read the fixed text.
- The hook hands delivery to a detached worker and returns (measured 0.32 s), so a slow network never delays the session. Worker failures are silent; `make office-push-test` reports them and prints the subscribe URL.
- TLS uses the OS trust store through `truststore`, so networks that inspect TLS work as they do for curl. Such a network can read the fixed text.
- Limits: an approved command still running after the delay also reads as unanswered, so the approval text says "may". `idle_prompt` also fires for sessions the owner has finished with. Codex sessions are not pushed.

Tool kinds: Edit/Write/MultiEdit/NotebookEdit/apply_patch → edit;
Read/Grep/Glob/LS → read; Bash/exec_command → command; WebSearch/WebFetch → web;
Agent/Task → agent; reasoning/thinking → think; anything else → other.

## 5. Agent wait on human (`lib/office/waits.py`)

A wait opens when a session needs the human (turn ended, explicit input
request) and closes at the next user prompt or matching reply in that session.
Waits longer than `wait_cap_seconds` count as *abandoned* and are excluded
from totals. The scanner reads a bounded date range of both sources with the
same adapters, so the live radar and the weekly metric share one definition.

`make agent-wait [DATE=YYYY-MM-DD]` prints the week; `make weekly` adds §4.6
with turns waited, total and median wait, p90, longest and abandoned count.
Both end with one Content Lab review line (finished package → owner decision);
its definition lives in `content_lab.review_waits` (office-world.md "Town attention").

**Sessions in play.** Each closed wait is bucketed (1, 2, 3, 4, 5+) by how many
sessions held the owner's attention when it opened: running agents (fresh
active/pending) plus sessions in needs-you or review (an input request under
`wait_cap_seconds`, an ended turn inside `review_window_seconds`), itself
included. The reading line compares the share of waits over
`wait_median_warning_seconds` at 1–2 versus 3+ in play: higher at 3+ means
review is the constraint (cap parallel sessions); higher at 1–2 means the tail
is time away, where a cap does nothing and a reachable alert helps. First real
week (2026-11-02): 24% long at 1–2 in play versus 12% at 3+, so time away.

## 6. Configuration

Optional keys under `office` in private thresholds, with schema defaults so
existing installations keep working:

| Key | Default | Range |
|---|---|---|
| `review_window_seconds` | 1800 | 60–86400 |
| `pending_tool_seconds` | 45 | 5–3600 |
| `wait_cap_seconds` | 14400 | 600–172800 |
| `max_segments` | 120 | 10–1000 |
| `claude_enabled` | true | bool |
| `push` (block) | absent = off | `enabled`, `server` (https), `topic` (20–64 url-safe chars), `approval_delay_seconds` 10–3600 (90), `idle_turns` (true), `finance_attention` (true); §4.2 |

## 7. Radar scene

The Lab building of [the office town](office-world.md). Its people never wander:
zones are floor pads, read front to back (the town around it and kelvin.ai's
walking are owned by the town design):

```text
            [ Done shelf ]          (back-left, dimmed)
 [ Working floor: desk · bookshelf · terminal rack · window · huddle table ]
 [ Review tray ]                [ NEEDS YOU ]   (front, warm accent, raised hand)
```

- Slots inside each zone are assigned in a stable order (oldest `attention_since` first).
- While working, a person stands at the station for `tool`; a tool change walks them there (walk speed from the scene standard).
- Needs-you people raise a hand and get a soft ring; reduced motion removes pulsing and walking (cuts).
- Subagents render at 0.7 scale beside their parent's slot, joined by a floor line.
- Labels show name, zone time ("waiting 12m") and the skill badge when attributed.
- §4 of the scene standard gains an *Office · radar* column (Overview only, people as interact targets). The classic town keeps every walk and camera rule.

Classic town: `/office?scene=town` (toggle in the toolbar). It is frozen: no
new features; existing browser specs run against it.

## 8. Page layout

1. Header + source bar (both sources' coverage, notifications toggle, classic toggle). With alerts on, a hidden tab keeps polling at the snapshot cadence so a new needs-you session still notifies (browsers may throttle hidden timers to about once a minute); with alerts off, hidden tabs stop polling.
2. Radar scene with the **attention queue** beside it: needs-you first, then review, oldest first, each with "waiting 12m". The queue replaces the empty "Meet your team" panel; selecting a row selects the person.
3. Day timeline under the scene: one lane per session, coloured by attention; a scrubber replays the scene at a past moment ("Replaying 14:05 · Back to live").
4. Office-owned runs (workbench) and the task composer move into a collapsed "Office tasks" section; collaboration keeps its route.
5. Posts move to `/posts`; the office keeps no posts button or board in the radar.

States: loading, live, partial coverage (one source unavailable), empty (no sessions today), error (last observation retained, active people become unknown), replay.

## 9. Contracts and verification

| Contract | Owner | Consumers | Verification |
|---|---|---|---|
| Observation v2 | `monitor.py` + `attention.py` | office_monitor CLI, state API, contract parser, fixtures | `tests/test_office.py`, `tests/test_office_claude.py`, `web/tests/office.test.ts` |
| Claude adapter | `lib/office/claude.py` | Monitor, waits | synthetic transcripts only; no real sessions in tests |
| Wait metric | `lib/office/waits.py` | `agent_wait.py`, `weekly_synthesis.py` | `tests/test_office_waits.py` |
| Radar view model | `web/lib/office-radar.ts` | scene, queue, timeline | `web/tests/office-radar.test.ts` (zones, slots, replay) |
| Scene | `radar-scene.tsx` | `/office` | `web/tests/browser/office-radar.spec.ts`, screenshots, scene standard §5 |
| Posts route | `app/posts/page.tsx` | nav | `office-posts.spec.ts` moved to `/posts` |

## 10. Known limits

- Permission waits are exact for Claude sessions started with the hook (§4.1, owner-approved 2026-11-08) and inferred for older sessions. Codex permission waits remain unobserved.
- Claude subagents are shown only while fresh (inside the review window) to keep the room readable; their wait is not counted (the parent waits).
- Codex subagent linkage is not recorded in the rollout; Codex parents stay null.
- Replay covers the history window (`history_days`) and segment cap only.

## Sources

- [Agent view in Claude Code](https://claude.com/resources/articles/agent-view-in-claude-code)
- [Agents in the Office](https://github.com/gukosowa/agents-in-the-office) · [Pixel Agents](https://github.com/pixel-agents-hq/pixel-agents)
- [Superset: roadmap to 100 agents](https://superset.sh/blog/roadmap-to-100-agents) · [Mergify: parallel agents](https://mergify.com/blog/how-agents-work-with-parallel-agents) · [agentpatterns.ai](https://www.agentpatterns.ai/workflows/parallel-agent-sessions/)
- [disler multi-agent observability](https://github.com/disler/claude-code-hooks-multi-agent-observability)
