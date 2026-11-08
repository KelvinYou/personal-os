# Virtual Office — Delivery Record

[Status: OK] First local release implemented — 2026-11-01.

This document owns delivery status and verification. [The design and operating contract](../design/ai-office-monitor.md) owns source coverage, privacy, configuration and recovery. The completed project has been removed from the active ROADMAP table.

## Delivered outcome

The current, already-running Codex conversation appears as a worker in `/office` without restarting it or launching its task from the web. Four actual workspace sessions were observed. The default source is live local records; synthetic scenarios are explicitly separate. There is no task execution, permission reply or hosted deployment.

The office includes original procedural 3D office/people, four workers per room, room pagination, camera orbit/pan/zoom/reset/focus, session selection and filters, complete DOM session list, evidence details, recent normalized events, source health and freshness. Eight synthetic workers demonstrate multiple rooms. Unknown role/parent associations stay empty; ended turns are not labelled completed work.

## Phase completion

| Phase | Delivered evidence | Status |
|---|---|---|
| 0 — Source proof | Current writer 0.166.0 identified; official hooks reviewed; existing local transcript seam attached without hook/config trust changes; current session UUID matched in Chrome | OK |
| 1 — Office | User accepted the actual single-room render; integrated scene supports multiple workers, list, details and separate single/team/empty/error/partial demos | OK |
| 2 — Observation core | Bounded incremental reader, deterministic normalized projection, stale state, partial coverage, rotation/rewrite handling, private atomic cache, strict schema-v1 boundary and optional owner configuration | OK |
| 3 — Live connection | Real session activity reached uncached loopback API and browser; polling pauses hidden tabs; service outage retained prior data and reconnect restored it | OK |
| 4 — Local delivery | Python/API/contract regressions, browser recovery and accessibility checks, production build, operating documentation and command discovery | OK |

The proposed copied JSONL collector was replaced with a disposable normalized cursor cache: existing client records already provide source history. No hooks, ingestion writer, tokens or persistent background process are needed. This is a deliberate reduction in stored private data, not an unfinished collector.

## Verification record — 2026-11-01

Checkout base: `a17c6b9`; implementation remains uncommitted alongside unrelated existing work. No submodule pointer was changed by this feature. Final verification passed: `make test` (386 Python tests, 8 Node tests, web typecheck, 25 Mermaid blocks and knowledge checks), `npm --prefix web run build`, and `git diff --check`. `make doctor` reports no errors; its pre-existing warning is that ignored `data/` is not an independent Git repository. Flow graph matches current sources.

Production server bound to `127.0.0.1:3000`; native Chrome displayed the four-worker WebGL room and selected current session with updating evidence. Production route/API returned 200 with private/no-store caching; foreign Host/Origin returned 403 and POST returned 405. `make office-check` returned four sessions with the expected bounded-history partial-coverage warning.

| Scenario | Result and limits |
|---|---|
| Real attachment | Current conversation ID matched its visible worker; four workspace sessions showed working and historical ended-turn evidence |
| Refresh performance | Warm local API checks approximately 140–270ms; browser cadence configured at 3 seconds; observation, not an SLA |
| Outage and recovery | Stopped development server: unavailable banner, retained list, active worker unknown; restarted server: automatic refresh restored active worker and selection |
| Eight-worker demo | Two rooms of four, pagination and complete eight-session list; selected worker details agreed with scene |
| Demo isolation | Browser resource timing showed zero `/api/office/state` requests while in demo |
| WebGL loss | Forced context loss via browser extension: explicit interrupted renderer; DOM list and details remained usable; Reopen restored the room and selection |
| Reduced motion | DevTools `prefers-reduced-motion: reduce` disabled animation control; restoring no emulation restored normal control |
| Narrow layouts | Emulated 320px and 390px: document width equalled viewport width; office width at 320px was 300px; no horizontal overflow |
| Render responsiveness | Apple M4 Pro, four visible workers, native Chrome; 120 animation frames over 1.0005s, approximately 120fps, viewport 932×861; short sanity check only |
| Original visual review | Actual room inspected in light/dark themes; keyboard Select updated worker state and details; user approved visual direction |
| HTTP/privacy boundary | Local GET succeeds with private/no-store headers; foreign Host/Origin rejected 403, POST 405; source failure 503 without private diagnostics |

Physical-phone performance, long-duration memory stability and every combination of appearance/accessibility preferences have not been certified. A dependency-origin Three.Clock deprecation warning was observed; no application rendering failure resulted. No broad performance claim follows from the short frame sample.

## Contract review

| Owner → consumer | Result | Status |
|---|---|---|
| Private thresholds → Python schema/monitor | Optional `office` block; existing consumers remain compatible; example parity verified | OK |
| Codex source → private projection | Read-only, bounded, workspace-scoped, atomic and disposable; no raw prompts/arguments/results/reasoning copied | OK |
| Python snapshot → server/browser → scene/list | Synthetic Python fixture, exact field validation, duplicate/source/version rejection | OK |
| Runtime evidence → displayed state | Activity, ended turns and freshness supported; tool failure separate from session failure | OK |
| Permission waits / roles / parent linkage | Input-wait mapping synthetic-tested; real permission wait and associations unverified and visibly unassigned | Warning |
| Existing audit, finance and submodules | No change to existing meanings or child repository pointers | OK |

## Operation

- `make office` starts the local office at `http://127.0.0.1:3000/office`; Ctrl-C stops the server.
- `make office-check` reports live source coverage; partial history is an explicit warning, not an empty successful office.
- `/office?mode=demo&scenario=team` opens eight synthetic workers without private-source queries.
- `make test` checks Python, web contracts/API, types and existing integration checks; `npm --prefix web run build` verifies production output.
- Owner settings live in `data/config/thresholds.yaml`; the operational example is `templates/thresholds.example.yaml`. Preserve other personal settings.
- Cache lives in ignored `data/runtime/ai-office/`; it can be removed while the reader is stopped and rebuilt from source. No canonical task history is owned here.

## Remaining coverage and optional future work

The local transcript layout is a client detail; re-verify it after Codex upgrades. No heartbeat establishes process liveness. Active evidence expires to unknown. Actual permission-request lifecycle, explicit role/parent associations, safe artifact viewers, Claude integration, historical replay, task execution, cross-machine use and hosted access require separate work. They are outside this completed local observation release.

## Office immersion revision — 2026-11-01

User review requested fullscreen, named virtual people and a more realistic office. Review found the fixed detail column limited room space, robot silhouettes lacked personal identity, and workstations lacked shared-office zoning. The revision adds browser fullscreen with an expanded-view fallback, collapsible details, stable cosmetic names/appearance, seated people, desk partitions, a glazed meeting area, whiteboard, coffee counter and wall clock. All art remains original code-built geometry.

Contract impact: source UUID → cosmetic character profile → scene/list/details changes presentation only; snapshot schema, runtime evidence, role attribution and privacy are unchanged. Shared Select gains an optional portal container; default consumers are unchanged. No backend migration is required.

Native Chrome acceptance: fullscreen entered with browser exit notice, four named people and meeting/coffee areas rendered; selecting Noah Sage opened details for demo-session-02; the fullscreen filter dropdown displayed and selecting Waiting for you retained exactly that worker; Escape restored normal layout. The full-screen dropdown placement defect found in review was corrected by placing its portal inside the fullscreen root. Short prior robot frame measurements do not establish this revised scene's performance.

The office preview/build uses `.next-office-review` on port 3001 to avoid interference with another concurrently running local page. Other preview work and navigation edits are preserved.

Revision gates passed: web typecheck, all 13 current web tests (including the concurrent home-viewer tests), isolated production build and `git diff --check`. Backend projection semantics were unchanged, so the previously passing Python suite was not repeated for this visual revision.

## Spacious mixed-avatar revision — 2026-11-01

The user requested female characters and a larger, less crowded office. The floor expands from approximately 11.36 × 6.96 to 18.2 × 12.2 scene units (about 2.8× area). Workstation centres are 4.6 units apart horizontally and 4.2 between rows; desk/chair sizes remain unchanged. Meeting and coffee areas occupy separate zones, the lounge is always present, four desks remain visible even with fewer sessions, and circulation aisles separate workstations and shared spaces. The room viewport is taller and details start collapsed. Camera fitting and label anchors use the enlarged layout.

Cosmetic profiles now include distinct female silhouettes (bob, ponytail, bun) and male characters, with matching display-name choices; source identities and runtime roles retain their original meanings. Native Chrome verified the expanded floor plan in fullscreen with all four real sessions, visibly separated desks, sofa, meeting zone and coffee counter, including female hair silhouettes and male/female display names. No new liveness or task-completion semantics were introduced.

## Facing workstations, idle movement and KL office revision — 2026-11-01

Subsequent user direction supersedes the widely spaced individual desks above: four desk halves now form one facing workstation island, with shared central screen and two seats on each side. The enlarged floor is retained for circulation and shared rooms. `kelvin.ai` has a dedicated glazed founder room with desk, visitor chairs, rug and signage. The meeting room occupies the front-right zone and kopi/teh pantry the front centre.

Idle sessions now have standing/walking poses on an offset common-area route; other source states keep their original observation meanings. Moving labels use the actual scene transforms. Pause/reduced-motion/hidden-tab handling stops movement; camera focus resolves the current actor rather than a stale desk position. The fixed office host is excluded from the source session list/count and cannot manufacture source evidence.

The user requested a Malaysian Chinese cast and local feel. Cosmetic names now use Malaysian Chinese surnames and romanized given names; men and women have dark-hair presets. The art adds timber sunshades, ceiling fans, woven chair details, terracotta greenery, KL studio signage and a kopi/teh counter. All signs use code-generated local canvas textures, without downloaded art or fonts.

Native Chrome verified facing seats, the named seated host, female/male characters, changing idle positions with attached names, local signs, and a working Pause/Resume control. The route was adjusted around the common-area planter. Five actual source sessions were observed, separate from the host; only four are rendered per paginated room. These changes retain snapshot schema v1 and do not modify backend projection or source permissions.

## Natural routines, laptops and founder orientation — 2026-11-01

User review replaced continuous idle pacing with long desk-reading periods, occasional pantry water breaks and seated lounge meals. `web/lib/office-life.ts` owns this purely decorative timeline and routed travel; it does not own runtime activity. Different offsets distribute routines among people. Travel eases at waypoints, character turns interpolate, and root height transitions between sitting/standing. Books, cups and lunch props accompany the corresponding routines. Animation pause and reduced motion stop the routine clock.

The floor now has an L-shaped entry recess instead of a full rectangular slab; its bounding envelope remains 18.2 × 12.2. Facing employee desks are preserved and now include an open silver MacBook Pro alongside both monitors and an external keyboard. The boss desk/chair and visitor seats rotate 90 degrees so kelvin.ai faces the employee area; the glass boundary and doorway remain accessible.

A synthetic routine regression samples four workers over 700 seconds each: all four activity modes occur, most time is at the desk, positions stay within the office, and horizontal transitions do not teleport. The focused office/API/interface suite passes all 9 checks. Native Chrome inspected the L-shaped plan, opened laptops, seated idle reading, a pantry stop, and the rotated seated host. Eating is covered by the deterministic timeline test; no claim is made that these decorative activities are actual session work.

Final integration checks for this revision: focused scene-adjacent/API/interface suite 9/9, complete current web suite 21/21, and web typecheck passed. Concurrent execution-module work briefly blocked the full build with a TypeScript control-flow narrowing error; the post-await status check now reads through its existing snapshot method without changing the stop behavior. Existing execution regressions passed with the full web suite.

The final isolated production build passed and the server was restarted on 127.0.0.1:3001. Production `/office` and `/api/office/state` returned 200; the source remained codex_local_transcript with nine observed sessions at verification time. Browser visual checks above were performed against the matching development revision; a different task held the shared Chrome tab during the final production HTTP check.
