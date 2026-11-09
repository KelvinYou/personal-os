# AI Office Monitor — Design and Operating Contract

[Status: OK] Local read-only observation implemented and verified against the current Codex session. Platform and source-format limits remain explicit below.

**Updated:** 2026-11-01 · **Tier:** Design-Lite · **Schema:** 1

Current direction and observation schema v2 (Claude Code source, attention zones, replay, wait metric): [attention radar](office-attention-radar.md). Sections below describe the original Codex-only v1 release.

[The implementation plan](../plans/virtual-office.md) owns phase status. This document owns architecture, coverage and operating semantics.

The additive [collaboration extension](office-collaboration.md) owns task
ownership, handoffs, advisory resource claims and fresh read-only managed teams
at `/office/collaboration`. It does not change this observation projection or
grant control over the sessions observed here. Execution exclusions below
describe the original observation release.

Current presentation extension: [host movement and camera controls](office-player-controls.md)
allows the same `kelvin.ai` host to stand and walk under explicit user input,
with first-person, third-person and overview cameras. This supersedes the fixed
seated-host description of the original release below. Decorative motion pause
and reduced motion do not disable explicit player input; hidden/blurred controls
clear movement. Player movement creates no observation or execution evidence.

## 1. Outcome and scope

The user works in the existing Codex client and opens `/office` to observe corresponding local sessions as 3D workers. There is no need to launch work from the office or restart the current session. One room contains up to four workers; additional sessions are available through room pagination and a complete DOM list. Selection, state filters, camera orbit/pan/zoom/focus, recent events and a separate synthetic demo are implemented.

Task execution, approval replies, cancellation, cross-machine access, hosted deployment, Claude integration, walkable avatars and office construction are outside this release. Roles and parent linkage remain unassigned when the source provides no explicit association. A skill definition is not a running process.

## 2. Research and source choice

Upstream references reviewed on 2026-11-01:

| Reference | Relevant approach | Decision |
|---|---|---|
| [Claw3D](https://github.com/iamlukethedev/Claw3D) | 3D office and gateway/custom runtime seams | Reuse the visual idea within the existing dashboard, rather than introduce a second runtime UI |
| [Pixel Agents](https://github.com/pixel-agents-hq/pixel-agents) | Hooks with transcript inference | Expose source coverage and distinguish observation from runtime certainty |
| [Claude Office](https://github.com/W17ant/Claude-Office) | Hook events drive office animations | Keep event interpretation separate from animation; no chat database is introduced |
| [Official Codex hooks](https://learn.chatgpt.com/docs/hooks) | Lifecycle hooks exist; non-managed definitions require trust review; transcript format is explicitly unstable | Inspect the supported interface first, then use the existing session's local records as a read-only adapter without changing or trusting hooks |
| [React Three Fiber](https://r3f.docs.pmnd.rs/getting-started/installation) | Fiber 9 pairs with React 19 | Pin the implemented compatible major versions |

The inspected current session metadata identifies a Codex writer at 0.166.0; the separately installed CLI reports 0.164.0. Observation reads the session records, not that CLI's execution interface. The record layout is a client detail and must be re-verified after client upgrades. No official connector available in this session exposed local coding-session lifecycle coverage.

## 3. Owners and data flow

```text
Existing Codex rollout JSONL [READ ONLY, client-owned]
            |
            v
scripts/lib/office/monitor.py [NEW: normalization, ordering, freshness]
            |                        |
            |                        v
            |          data/runtime/ai-office/projection.json [NEW, PRIVATE]
            v
scripts/office_monitor.py --json [NEW]
            |
            v
web/lib/office.ts -> /api/office/state [NEW: validated, uncached, local]
            |
            v
/office [MODIFIED: live source + independent demo, 3D/list/detail]
```

The office projects evidence into space; it does not own task execution. Existing finance, audit, daily-log and flow owners keep their semantics. `scripts/lib/schema.py::OfficeCfg` owns the optional operational configuration in the owner's private thresholds file.

A private cursor/snapshot cache replaces the initially proposed copied event log. The client already owns immutable source history, so a second raw transcript/event store would duplicate private data. The projection stores only source-file identities, byte offsets, integrity digests, opaque session identifiers and bounded normalized events. It is disposable and rebuilt on demand.

## 4. Verified event coverage

| Observed source record | Mapping | Evidence and limits |
|---|---|---|
| `session_meta` with UUID and matching `cwd` | Discover one worker | Exact workspace or child path; sibling prefixes excluded |
| `event_msg.task_started` | Working | Observed in the current real session |
| `event_msg.task_complete` | Turn ended / idle | Observed in previous turns and other real sessions; not proof of completed work |
| `response_item.reasoning` | Thinking / working | Only event kind and time are used; reasoning content is ignored |
| Function/custom tool calls | Generic read/edit/command/tool activity | Explicit known tool names only; wrapped calls can remain generic |
| Completed command/file/MCP item | Observed tool activity/outcome | Nonzero command exit or explicit failed status is a tool error, not session failure |
| `request_user_input` call and matching reply | Waiting, then working | Mapping tested with synthetic events; this client's real permission wait has not been captured |
| `turn_aborted` / `task_failed` | Interrupted idle / explicit failure | Mappings covered by synthetic tests; no runtime-wide failure coverage claim |
| Permission requests, parent linkage, skill-role identity | Not established by this source | Never infer from file names, skill definitions or elapsed time |
| Silence or expired active evidence | Unknown | No runtime heartbeat or process-liveness claim |

Final assistant text alone does not establish completion. An asynchronous question does not establish that the session stopped working. A recorded ended turn remains a historical fact even after its timestamp ages; a formerly working/waiting session becomes unknown when freshness expires. Source clock drift beyond the configured window is visible.

Malformed/oversized records, bounded-history bootstrapping, discovery/session caps and unreadable formats produce explicit partial coverage. The adapter skips image-sized lines without allowing them to hide later recent events. Unreadable sources fail explicitly. Browser refresh failures retain the previous snapshot under an unavailable-source banner and mark formerly active workers unknown until reconnect.

## 5. Snapshot API and compatibility

`GET /api/office/state` is a Node route with dynamic rendering and `Cache-Control: private, no-store, max-age=0`. It accepts no file paths or task commands. Host must be loopback; a supplied Origin must match it. There is no CORS grant or write handler. Invalid origin/host returns 403, unsupported method returns 405, unavailable/invalid source output returns a fixed 503 error without raw diagnostics.

The exact synthetic schema-v1 shape is in [the Python-produced boundary fixture](../../tests/fixtures/office/snapshot.json). Python owns state derivation; [the browser-safe contract](../../web/lib/office-contract.ts) validates version, identity uniqueness, field sets, types and source consistency both server-side and before UI consumption. Unknown fields are rejected so unexpected raw content cannot silently cross the boundary.

`source_status: connected` means the local source is readable, not that an agent process has a live heartbeat. `partial` means the reader returned records with declared coverage gaps. Every session includes source evidence, state, last event time, coverage, tool outcome, bounded events and optional role/parent/artifact fields. Those optional associations are empty/null until supported; artifact paths are never invented.

This is an additive boundary. Existing threshold files remain valid without `office`; live office observation then reports unavailable until that block is configured. There is no historical daily-log, finance or audit migration.

## 6. Storage, ordering and privacy

- Discover bounded recent date folders, including the next UTC date for client-local midnight, and filter metadata to the workspace.
- Read bounded byte windows incrementally. Partial last lines retry when complete; giant records are skipped with a coverage warning. No full-history rescan on each request.
- A locked writer atomically replaces a private projection. Source inode, prefix fingerprint and cursor anchor detect replacement/truncation/rewrite. Event identities plus byte cursors prevent replay duplicates; older timestamps cannot overwrite newer evidence. Duplicate source files do not create duplicate workers.
- The cache directory uses mode 0700 and its files use 0600. Symlink redirects of managed cache files are refused; CLI storage must remain inside the ignored private data tree.
- Prompts, titles, instructions, reasoning, source code, command arguments/results, account data and arbitrary source paths never enter the snapshot or cache. Activity labels come from a fixed allowlist. No real session record is used in public fixtures.
- The current checkout's `data/` is an ignored private folder, not an independent Git checkout. No repository is initialized, committed or published by this feature. Public child repositories and their pointers are unchanged by the office work.

## 7. Running, configuration and recovery

Start with `make office`, then open `http://127.0.0.1:3000/office`. `make office-check` validates observation and prints a concise coverage summary. `scripts/office_monitor.py --json` exposes the same sanitized projection used by the API. Demo mode is available at `/office?mode=demo`; `/office?mode=demo&scenario=team` shows eight synthetic workers over two rooms. Other direct scenarios are `single`, `empty`, `error` and `partial`.

The existing configured owner received an `office` block appended to `data/config/thresholds.yaml`, preserving the rest of the file. For a new checkout, copy only that operational block from `templates/thresholds.example.yaml` into the owner's reviewed thresholds file; do not replace existing personal settings or set owner approval flags automatically. The block is optional for every other feature.

| Setting | Purpose |
|---|---|
| `poll_interval_ms` | Browser refresh cadence after a valid snapshot |
| `stale_after_seconds` | Maximum silence before an active state becomes unknown |
| `history_days` | Recent source discovery and projection retention window |
| `max_sessions` / `max_candidates` | Bound source discovery and visible session projection |
| `max_read_bytes` / `max_record_bytes` | Bound incremental reads and individual record parsing |
| `recent_events` | Bound each session's event history |

The reader runs only on requests or `office-check`. The Codex client continues owning and writing its own records while the web app is closed. Reopening the office catches up from bounded recent records. Hidden tabs stop polling and animation; showing the tab refreshes evidence. Requests have bounded timeouts; stale/out-of-order responses cannot replace a newer client result. Initial setup failures offer manual Refresh; an established reader retries using its configured cadence.

If the source is missing, fix local session access or private configuration and Refresh. If the cache is corrupt, source evidence can rebuild it; it contains no canonical task data. There is no background service to uninstall. Stop the web server with Ctrl-C. Disabling observation does not alter the original Codex session, hooks or permissions.

## 8. Rendering and failure states

The expanded procedural office and seated virtual people are built with pinned Three.js/Fiber/Drei packages and no external art, fonts or HDR assets. Static room geometry is memoized. Four workers share a room; further workers stay accessible through pagination/list selection. Opaque source session IDs preserve character identity across refreshes. `web/lib/office-character.ts` derives cosmetic names, skin/hair/clothing palettes and male/female avatar presentations from the opaque ID. Female silhouettes include a shoulder-length bob, ponytail or bun and a tailored blouse; presentations remain stable across refreshes. The user-selected Malaysian Chinese cast uses romanized Chinese names and dark hair; these are cosmetic presets, not inferred source demographics. Timber sunshades, ceiling fans, woven chair details, terracotta pots and locally rendered KL/kopi/teh signs provide the office art direction. These aliases are display identities, not inferred real people or skill roles; full source identity stays in details. The L-shaped floor fits within an 18.2 × 12.2 scene-unit envelope and includes a shared four-seat facing workstation island, circulation aisles, a central desk screen, separate glazed meeting area, founder office, whiteboard, coffee point and permanent lounge. The desk halves meet edge-to-edge; two seats face the other two. Each workstation includes two external monitors and a procedural open silver MacBook Pro with keyboard, trackpad and notched display. Details start collapsed to give the room the available page width. Unknown/error workers do not act out ongoing work. Idle workers spend most decorative routine time seated at their desks reading, with occasional routed trips to drink at the pantry or sit and eat in the lounge. Travel eases at waypoints, turns smoothly, and transitions in height between seated/standing poses; working/waiting workers stay at their desks. Paused, reduced-motion and hidden-tab modes stop movement. Walking is decorative and does not change source state. Name labels project actual character positions, and camera focus resolves the current character transform. `kelvin.ai` is a fixed seated office host in the founder room, with its desk and visitor seats rotated 90 degrees toward the employee area; it is not a synthetic live session, does not enter session counts and has no fabricated runtime state.

The existing DashboardNav, Select, DataState, appearance settings and local tokens are reused. DOM labels are projected from 3D coordinates in the same React tree, avoiding nested-root mounting. Session details remain DOM content. The list is independently usable if WebGL is missing, rendering fails or context is lost; context loss provides a room-reopen action. Reduced motion and hidden-tab handling gate the Three.js render loop and animation.

Loading, no source, empty office, no filter matches, partial coverage, prior-snapshot retention and renderer loss have distinct presentation paths. Demo state never mixes with real evidence and performs no local observation requests.

Fullscreen uses the browser Fullscreen API with a viewport-filling fallback if denied. Entry hides the detail panel; selecting a person opens it again. Escape/exit restores the page. Filters and source selection retain their semantics. Shared Select accepts an optional portal container so its menu remains inside the fullscreen element; other callers retain the default portal. The office's preview can use the existing `NEXT_DIST_DIR` option with `.next-office-review` and a free port when another local page is building.

## 9. Verification and review

Focused Python tests cover source attachment, strict workspace scoping, interleaved sessions, duplicate/out-of-order records, input-wait correlation, partial writes, giant records, replacement/rewrite, clock-driven staleness, concurrency, permissions, privacy and configuration compatibility. Node tests consume the Python-produced synthetic fixture, reject schema/source drift and duplicate identities, exercise eight-worker/empty/partial demos, and test the actual API route with a mocked source. `make test` includes those Node tests as well as existing Python, diagram, knowledge and type checks.

Real integration evidence on 2026-11-01: the current conversation's opaque ID matched a worker in the browser; four real workspace sessions were observed, including a working session and historical ended turns. Local API responses updated in roughly 140–270ms after warm-up during the development check; the configured browser cadence was 3 seconds. This is a local observation, not an SLA. Stopping the observation web service produced the explicit unavailable-source banner, retained sessions and an unknown active worker. Restarting the service automatically restored the same selected session and its active state in the browser.

The original visual sample was reviewed in native Chrome in both themes. The integrated multi-worker view and current-session details were also inspected. Broader physical-phone, long-duration memory stability and source-version compatibility remain limits rather than established claims. Final browser checks and their measured limits are recorded in the implementation plan.

Contract review: [Status: OK] owner configuration → Python normalizer → sanitized snapshot → exact TypeScript validation → 3D/list/detail agree; existing consumers remain compatible. [Status: Warning] local transcript format, permission waits and role/parent attribution have the explicit coverage limits above. No public/private migration, submodule update or Git commit is part of this delivery.

## 10. Visual sample record

Historical record of the first visual slice. The current implementation and coverage are described above; this section does not describe the released monitor.

[Status: Warning] Interactive visual prototype implemented on 2026-11-01; user acceptance and live monitoring remain pending.

**Run:** `npm --prefix web run dev -- --hostname 127.0.0.1 --port 3000`, then open `http://127.0.0.1:3000/office`. The visual sample does not require a private-data checkout. The existing `make web` remains available for the full local dashboard and its environment checks.

**Implementation:** `web/app/office/` owns the route and scoped CSS; `web/components/office/` owns the prototype, synthetic state definitions and procedural Three.js models/textures. The dashboard navigation adds an Office entry. React Three Fiber 9.8.2, Drei 10.7.9, Three.js 0.187.0 and its matching type package are pinned. All scene models and wood grain are generated locally from code; there are no downloaded art assets, external fonts, HDR environments or private example records.

**UI reuse:** overview plus detail pattern; existing DashboardNav, appearance settings and Select. The renderer failure surface uses DataState. The scene is dynamically loaded on the client; the DOM list works independently. A projected DOM label stays in the existing React tree, avoiding the nested-root warning observed with Drei Html during initial verification.

**Scenarios:** working, waiting for the user, resting and unknown source status are explicit demo controls. A resting turn is not labelled completed work. Source and page labels identify simulated events and no live connection. The prototype sends no runtime commands and implements no backend observation endpoint.

**Verification:** production build/type validation and the existing two interface-reuse regression checks passed. Native Chrome screenshots in the implementation session show the actual WebGL room, selected worker, zoomed camera, waiting state, event disclosure and light/dark appearances. Keyboard selection through the shared Select updates the worker label, details and event list together. At emulated widths 390 and 320, DevTools measurements returned equal viewport/document widths (390/390 and 320/320); the office workspace at 320 measured 300px. These are layout-containment checks, not physical-phone certification. Existing browser pinch scaling affected some mobile screenshots and was distinguished from document overflow.

**Remaining verification:** user visual acceptance, physical mobile performance, forced WebGL loss/recovery and OS reduced-motion emulation. Recovery and reduced-motion paths exist but are not established by source inspection alone. No frame-rate or memory-stability claim is made. A Three.Clock deprecation warning originates in the renderer dependency; it is not a verified runtime failure. Existing browser-extension diagnostics are separate from application errors.

**Contract review:** [Status: OK] synthetic state → local scene/list/detail is additive, in-memory and isolated from private data; no migration is needed. [Status: Warning] real runtime evidence, observation persistence and the proposed API are still unimplemented. Shared finance, flow and audit meanings are unchanged by this visual slice.
