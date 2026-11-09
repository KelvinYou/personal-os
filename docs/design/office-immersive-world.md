# Office: immersive world, live boards and Malaysia sky

[Status: Warning] Design-Lite · Phase 2 (fullscreen shell) implemented 2026-11-09; phases 1 and 3–6 open

## Outcome and scope

Make the default `/office` world the primary workspace. Enter fullscreen once and
read data, inspect people, answer owned-task questions, review results and use
Finance without leaving the world or scrolling down a dashboard. Both Lab and
Finance follow the same interaction model. The world has continuous green ground
and a sky that follows Malaysia time.

This document is English to follow the repository convention. Owner requirements:
complete fullscreen; green ground with minimal CPU/storage cost; light blue sky
in the morning and dark sky at night; Finance and Lab data and interactions inside
the world rather than department tabs opening content below the canvas.

| Included | Boundary |
| --- | --- |
| Native fullscreen plus viewport-filling fallback | Browser security UI remains browser-controlled; no automatic fullscreen on load |
| Persistent world boards in both buildings | Summaries are present before clicking; full tables/forms open inside the same fullscreen root |
| Full Lab and Finance workflows in world-mounted work panels | Existing execution, review, financial writes and confirmation rules retain their owners |
| Visually continuous green landscape | Existing walk boundary and collision world remain bounded |
| Local-time sky and fog, optional modest light adjustment | An artistic daily cycle; no weather service, geolocation or astronomical sunrise claim |
| Measure resource changes and cap fullscreen pixels | Negligible additional cost is a target, not a claim of literally zero computation |

Classic `/office?scene=town` stays frozen. Its existing fullscreen implementation
is a reference, not the implementation target. `/finance` and the accessible
non-3D Office view remain available as explicit alternatives.

## Current implementation and gaps

- `web/app/office/page.tsx` loads the wealth report and workbench summary for the
  default world; demo uses synthetic data. The workbench snapshot currently becomes
  only `financeNotice`, so richer board summaries need an explicit typed projection.
- `office-workspace.tsx` owns department, selection, replay and execution state.
  It renders `FinanceAside`/`RadarDetails` next to the canvas and Finance detail,
  timeline, `OfficeWorkbench` and `DirectTask` below it. `chooseStation()` calls
  `scrollIntoView()`. The default workspace has no fullscreen button.
- `radar-scene.tsx` already has both buildings, walking, F interaction, labels and
  projected anchors. It uses one Canvas, static sky/fog, existing lights,
  `dpr={[1, 1.75]}`, and conditional continuous/demand rendering.
- `town-landscape.tsx` draws a finite grass box and exposed soil box.
  `GROUND` in `office-departments.ts` also defines walk bounds: enlarging it would
  unintentionally change navigation and generated scenery.
- `RadarCamera` reframes when aspect-dependent `fit` changes. Fullscreen resizing
  must stop resetting the user's camera. `office-player.tsx:35` maps Escape to
  overview, but in native fullscreen the browser consumes Escape to exit and the
  page never receives it (see Escape below).
- Overview pan target is clamped to the town ground rectangle (landed separately,
  before this feature), so the reachable camera frustum is finite.
- Windowed `/office` today renders details below the canvas. Classic town's
  `town-workspace.tsx:40-56` already has fullscreen + portal handling; it has the
  same Escape gap and is a known pitfall, not just a reference.
- `web/` has no timezone handling today; the timezone owner is private
  `data/config/settings.yaml`.

## Proposed design

```text
/office server [MODIFIED: typed finance board projection; same source loads]
  -> OfficeWorkspace [MODIFIED: state and one privacy owner]
      -> ImmersiveWorldShell [NEW: fullscreen root, HUD, overlay host]
          -> RadarScene [MODIFIED: same persistent Canvas/player/camera]
              -> TownLandscape [MODIFIED: continuous low-poly green ground]
              -> WorldEnvironment [NEW: KL clock -> sky/fog/light properties]
              -> Lab + Finance world boards [NEW: world-anchored HTML]
          -> WorldWorkPanel [NEW: readable DOM panel, inside fullscreen root]
              -> existing details / timeline / tasks / composer / Finance views
```

One persistent workspace owns the world, data and actions. Boards make the world
informative without a click; readable work panels complete complex interactions
without leaving fullscreen. Avoid separate data-fetching or task-execution owners.

### Fullscreen and world shell

Use a dedicated root containing the Canvas, world HTML, HUD, notifications and
all interactive portals. A labelled `Fullscreen` button directly calls
`requestFullscreen()` from the user's gesture. Track pending/native/expanded/
windowed state; native state follows `fullscreenchange`, including browser exits.
If unsupported or rejected, retain an explicitly labelled expanded view with
`position: fixed`, `inset: 0`, `100dvh`, safe-area padding and restored body scroll
on exit/unmount. Keep an always-visible `Exit fullscreen` control.

One layout in every mode: windowed `/office` uses the same shell and on-demand
work panel at page size, and nothing renders below the canvas. Fullscreen and
expanded only change the shell's box, so there is one layout to build and test.

On iPhone Safari, `Element.requestFullscreen` is unavailable for ordinary
elements, so at 390/320 px the expanded fallback is the primary path, not an
edge case: verify `100dvh`, safe-area padding and the collapsing address bar there.

The scene fills the display edge to edge: no dashboard navigation, permanent
sidebar, page heading or bottom content consuming its height. A compact HUD holds
world controls, live/demo/source health, privacy, notifications and work-panel
access. Do not reparent or remount Canvas on entry/exit. Preserve camera target,
orbit, player pose/view, selection, replay position and drafts. Resize updates
camera aspect and bounds; only initial load or explicit reset reframes the town.

Audit Select dropdowns, dialogs and `DirectTask.portalContainer`: their portal
targets must be descendants of the fullscreen root. Avoid duplicate mounted
composers, duplicate IDs, additional polling loops and lost drafts when panels
close. Keep workflow controllers mounted; separate their state from visibility.

### Data and interaction inside both buildings

| World location | Visible without activation | Click / F / keyboard action |
| --- | --- | --- |
| Lab attention board | Needs-you, review, working and done counts; bounded oldest-first queue; source status | Select a session and open its evidence panel inside the world |
| Lab person | Existing identity, attention and activity labels | Existing read-only detail/evidence; observed external sessions do not become resumable owned tasks |
| Lab task board | Owned questions, results to review and blocked-work summaries | Open tasks, answer a question, start/stop an owned task, accept/request changes or prepare follow-up using existing controls |
| Lab timeline board/control | Live/replay state and recorded coverage | Expand the existing timeline in-world; scrub or return to live |
| Finance assets board | Tracked assets, allocation summary, currency, scope, as-of and coverage; amounts masked initially | Read expanded asset details in-world; explicit source link remains optional |
| Finance notices board | Maturity/coverage notices from existing evidence | Read recorded notices in-world |
| Finance workbench board | Saved open/draft work summary with its own as-of/unavailable state | Use existing funding, allocation, scenario and evidence forms in the world work panel |

Prefer a small fixed set of Drei `Html transform` boards attached to physical
board positions. Existing Drei already supplies this capability. Use constrained
card dimensions, bounded rows and simple layouts; do not mount full data tables
per desk or create a text mesh per field. At a distance show a compact summary;
nearby show readable content. The actual data remains on the building's boards,
not just a clickable decorative sign. Prototype one board in each building before
expanding; validate perspective blur and overlap in overview and walking views.

Use only explicit board/wall occluders where needed, not a whole-scene raycast
per board per frame. Hide boards behind the camera, outside the frustum or facing
away. Do not make every building board update through React on every frame.
No new font/image/model files are required. HTML has DOM/compositing costs that
must be measured; avoiding WebGL geometry does not make it free.

Complex content uses one on-demand work panel within the world: a readable side
panel on desktop and bounded sheet on mobile, with close/back-to-world controls.
These are detail surfaces, not department tabs that replace the world. Finance
desk selection no longer scrolls the document. Opening details never auto-moves
the camera; an explicit `Focus board` action can use the standard camera transition.
Department deep links still select the intended content and open it in-world.

Board input takes priority over walking/orbiting: stop pointer propagation at
interactive controls, clear held movement keys when a panel takes focus, and
restore scene focus on close (the standard already blocks scene keys while focus
is in a form control).

**Escape.** In native fullscreen the browser consumes Escape to exit and does not
deliver the keydown, so neither "panel closes first" nor Esc-to-overview can work
by default. Pressing Esc mid-walk would drop the user out of fullscreen instead.
Rule:

1. After native entry succeeds, call `navigator.keyboard.lock(["Escape"])` where
   available (Chromium; requires fullscreen). Then a short Esc reaches the page
   (panel first, then overview) and a held Esc exits fullscreen, which the browser
   announces itself. Release the lock on exit.
2. Where the lock is unavailable (Safari, Firefox), Esc exits fullscreen. Panel
   close and overview must therefore always have visible controls (`Close`,
   `Overview`), and every view button keeps working without a keyboard.
3. Expanded (non-native) mode receives Esc normally: panel, then overview, then
   leave expanded.
4. Every exit path (`fullscreenchange`, lock release, blur) clears held keys and
   shell state. Never try to suppress the browser's own exit.

Prototype the lock in phase 1 in a headed Chromium build before writing the shell;
headless Playwright cannot prove real Escape/fullscreen interaction. Update the
standard's §2 key map with this fullscreen note in the same change.

### Green ground with bounded geometry

Replace the visible grass/soil island treatment with a single-segment green
`PlaneGeometry` and existing matte material. Keep roads, plaza, flower beds and
building floors above it. The overview pan target is clamped to the
`GROUND` rectangle and the camera distance to `maxDistance`, so the reachable
frustum is finite: use one fixed plane covering `GROUND` inflated by the fog far
distance (260), beyond which everything already renders as sky colour. No
per-frame recentering. Check maximum pan, zoom and all walk-camera directions.
Do not enlarge `GROUND`, generate more trees, add grass blades, tile meshes,
textures or terrain chunks. Avoid a coplanar second green surface and exposed
soil seams. Keep visual ground separate from walk/collision geometry.

An unsegmented plane has two triangles regardless of its world dimensions.
Reusing/replacing the current ground meshes should keep main-pass draw calls
flat or lower; large screen coverage can still change GPU fragment work.

### Malaysia clock and sky

Create a pure `environmentAt(epochMs, timeZone)` helper using a cached
`Intl.DateTimeFormat` per IANA zone. The zone comes from its existing owner,
private `data/config/settings.yaml`, read on the server in `app/office/page.tsx`
and passed down; fall back to `Asia/Kuala_Lumpur` for demo or when private data
is not checked out. Do not hardcode the zone in the component.

Anchor times follow Kuala Lumpur light (sunrise about 07:05–07:25, sunset about
19:15–19:30 all year), stylised. Colours are owned by the standard's §4 Office town
parameters and `web/lib/office-palette.ts` (`townSkyAnchors`, checked by
`scene-standard.test.ts`); this table only names the intent:

| Local time | Visual anchor |
| --- | --- |
| 00:00 and 06:00 | Dark blue night |
| 07:30 | Pale blue morning |
| 12:00 | Clear daytime blue |
| 19:15 | Soft dusk |
| 20:15 and 24:00 | Dark blue night |

Interpolate between anchors, including midnight. Check overlay text, building
labels and HUD contrast against the night colour. Use scene background and the
existing fog with the same sky colour; retain readable scene illumination at
night. Initially keep light positions and shadow resources fixed, adjusting only
existing light colour/intensity if visual proof shows it is needed. No HDRI,
sky dome, sun simulation, cloud animation, weather API or extra shadow-casting light.

Update at most once per visible minute and immediately on visibility return;
cleanup timers/listeners. Reuse the live clock cadence where practical, but do
not use the frozen demo/replay timestamp for the default ambient sky. Tests inject
time. Demand mode invalidates once per environment update; the sky must never
enable a continuous render loop. Reduced motion needs no animation loop.

## Ownership, privacy and compatibility review

| Contract | Owner -> consumers | Migration / verification |
| --- | --- | --- |
| Scene appearance and control rules | `3d-scene-standard.md` -> environment, ground, boards, HUD | Update active Office parameters and document in-world UI input precedence before implementation; shared movement constants remain owned by the standard |
| World placement | `office-departments.ts` -> landscape, board anchors, F targets | Add board positions without changing walk bounds or financial semantics; collision and navigation regression |
| Valuation and financial evidence | Python wealth report v4 -> `loadReport` -> Finance detail + board projection | No report/schema version change; TS formats/selects existing results only; test missing/unpriced/stale states |
| Saved Finance work | Existing workbench snapshot/API -> initial summary + existing workbench controller | Reuse loaded snapshot; preserve revision, confirmation and reconciliation rules; no new financial write path |
| Lab observations and owned execution | Existing observation/execution/work contracts -> boards + same mounted controllers | No permission expansion; no observed-session resume; same action handlers and error states |
| Privacy | One `PrivacyProvider` -> HUD, boards, Finance and work panels | Bridge privacy explicitly across Canvas/Html roots; verify one toggle controls all surfaces; never a second independent flag |
| Routes and access | `/office` query state -> world panels and text alternative | Preserve live/demo isolation and deep links; update Office verify-web feature map |

[Status: OK] This proposal requires no data migration, public/private move,
valuation reimplementation or observation-schema change. All financial amounts,
holdings and sensitive work content retain existing masking/consent rules. Do not
bake private values into textures, public assets, fixture files or browser logs.
Privacy is screen masking, consistent with the current local app, not access control.

[Status: Warning] Existing standards contain older radar-only language while
the current town supports walking. Update the active parameter description as
part of this feature rather than copying stale scene exceptions into new code.

## Performance target and measurement

Separate storage, CPU, GPU and memory. New code/DOM adds some bytes and work;
the goal is no new downloaded assets/dependencies, no persistent data growth,
no extra polling, and no material sustained CPU regression. Fullscreen and HTML
compositing cannot honestly be guaranteed to consume exactly zero extra resources.

Capture the current implementation before changes using the same synthetic
scenario, device, camera and sample duration. Compare environment alone, boards,
and fullscreen separately. Record renderer calls/triangles/geometries/textures,
draw-buffer pixels, browser main-thread time, frame-time distribution, DOM size
and memory trend. Compare idle, walking, orbiting, task editing and hidden-tab
states. `renderer.info` does not measure HTML/CPU costs by itself.

Cap drawing-buffer pixels at a fixed megapixel budget declared as an Office
parameter in the standard's §4 (set from the phase 1 baseline), not at "the
windowed size": that depends on layout, and on a 1× 1920 px display it would drop
fullscreen to about 0.6 DPR. Effective DPR is
`min(deviceDpr, existingCap, sqrt(pixelBudget/(width*height)))`. The current
`dpr={[1, 1.75]}` range floors at 1, so the Canvas must receive the computed
number instead. Allow DPR below 1 only if the budget requires it; keep DOM text
at native resolution. This trades some 3D sharpness for bounded pixel work and must be
visually checked. Do not increase shadow maps or enable expensive postprocessing.
If boards cause a repeatable CPU increase, reduce DOM/visible rows and hide
irrelevant boards before adding features; report measurements rather than claiming
the target passed from geometry counts. Keep current rendering mode behaviour;
do not claim idle savings when existing motion is enabled.

## Implementation sequence and acceptance

1. **Baseline and active contract.** Capture current default-world costs and
   interactions and set the pixel budget; reconcile Office parameters (sky anchors,
   pixel budget, fullscreen Escape note) in `3d-scene-standard.md`. Prototype the
   Escape keyboard lock in headed Chromium. Prototype one Lab and one Finance HTML
   board to resolve blur, privacy context and input behaviour. Keep their data synthetic during the prototype.
2. **Persistent world shell.** [Status: OK] Done 2026-11-09: `use-world-fullscreen.ts`,
   the extras portal that moves below-canvas content between the page and the panel slot
   without remounting, `PortalRootContext` in the shared `Select`, the camera `touched` rule,
   `PixelBudget` (`web/lib/office-render.ts`), the narrow bottom sheet closed on entry, and
   `office-immersive.spec.ts` (native, declined fallback, 390 px). Evidence: ignored
   `web/.verify-web/2026-11-09T02-32-*-fullscreen-*`. Not yet: the keyboard-lock behaviour has
   only been exercised headless, and the 3.0 MP budget is provisional until phase 1 measures it.
   Original plan: add a fullscreen
   state hook; adapt `office-workspace.tsx` and `office.css`. Add overlay/portal
   host and pixel budget; fix resize-induced camera resets in `radar-scene.tsx`.
   Prove native exit, rejection fallback, state retention and form portals first.
3. **Environment.** Add `web/lib/office-environment.ts` and its scene adapter;
   update `town-landscape.tsx` visual ground. Prove all views hide ground edges,
   day/night boundaries work, and geometry/textures remain bounded.
4. **Finance in-world.** Add typed board projection and `finance-world-boards.tsx`;
   pass existing evidence through the page/workspace. Adapt
   `finance-department.tsx` to render existing detail/workbench inside the shared
   panel; replace station `scrollIntoView` with panel selection. Reading core
   values/notices must require no desk click or department-tab activation.
5. **Lab in-world.** Add `lab-world-boards.tsx`; integrate existing details,
   `office-timeline.tsx`, `workbench.tsx` and `direct-task.tsx` with one persistent
   controller per workflow. Replace page-scroll/focus assumptions with in-world
   panel actions. Prove question -> answer, result -> review and follow-up retain
   state across panel and fullscreen changes.
6. **Focused regressions and evidence.** Update the Office feature map and add
   `web/tests/browser/office-immersive.spec.ts`; register it in
   `config/scene_checks.json` (suite list and a file scope for the new shell,
   board and environment files) so `make scene-check` selects it. Test actual native fullscreen
   separately from a stubbed rejection fallback; use a headed browser where
   headless/native support differs. Unit-test KL time boundaries, the pixel cap,
   and board projection/absence semantics with synthetic fixtures.

Before/after camera-change regressions:
`make test-browser SUITES="office-radar office-departments office-player office-camera"`.
Final gates: `make design-check`, `make test`, `make scene-check` with the scope
selected by the scene workflow, plus immersive and affected workbench suites.
Do not run state-changing execution or financial acceptance against real records
as a visual test; use fixtures/mocks for write journeys.

Use verify-web's isolated launch -> doctor -> journeys -> screenshots/evidence ->
cleanup before claiming the feature works. Capture 1440, 390 and 320 px, light/dark,
reduced motion and touch. Include morning/night, overview/first/third person,
fullscreen/expanded, a Lab task panel and Finance data/forms. Verify no page scroll,
movement while typing, detached portals, lost drafts, hidden unmasking, new external
requests or context-loss dead ends. Private evidence stays in ignored runtime/test
folders; link the actual evidence only after implementation.

## Failure behaviour and review decisions

| Case | Expected behaviour |
| --- | --- |
| Native fullscreen denied/unsupported | Labelled expanded mode; exit control works; root contains every portal |
| Browser exits fullscreen | Restore shell/scroll/focus; keep world state and unsaved work |
| Data unavailable/stale/unpriced | Show source-specific state and as-of; never substitute zero or a success badge |
| WebGL lost | Text controls remain usable in the same shell; retry restores world without duplicate controllers |
| Action fails or revision conflicts | Existing component error/retry/confirmation behaviour remains visible in-world |
| Board is too small/occluded | Compact summary plus explicit focus/read action and accessible work panel |

Defaults for review, not blockers for writing this plan:

1. Start in the ordinary world with a Fullscreen button; browsers require a user
   gesture for native entry. Should viewport-filling expanded mode be the default
   on page load? Proposed: explicit entry first.
2. Use the stylised Kuala Lumpur anchors above in the configured timezone.
   Should seasonal sunrise/sunset be added later? Proposed: keep the fixed cycle;
   KL varies by only about 20 minutes across the year.
3. Show a few bounded summaries on physical boards and use the same-world work
   panel for long tables/forms. Is this information density sufficient? Validate
   it using the two-board prototype before implementing every board.

## Web references

Verified 2026-11-09. Mechanisms below come from official documentation; low-cost
expectations and the chosen product interaction are design inferences, pending measurement.

- [MDN: requestFullscreen](https://developer.mozilla.org/en-US/docs/Web/API/Element/requestFullscreen) — user activation, promise rejection and fullscreen state events.
- [MDN: Keyboard.lock](https://developer.mozilla.org/en-US/docs/Web/API/Keyboard/lock) — capturing Escape in fullscreen (Chromium only); held Escape still exits.
- [Three.js: PlaneGeometry](https://threejs.org/docs/pages/PlaneGeometry.html) — dimensions and independent segment counts.
- [Three.js: Scene](https://threejs.org/docs/pages/Scene.html) — colour background and existing fog integration.
- [Three.js: responsive rendering](https://threejs.org/manual/pages/responsive.html) — drawing-buffer dimensions, aspect and pixel-budget implications.
- [MDN: Intl.DateTimeFormat](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/DateTimeFormat) — explicit IANA timezone formatting.
- [R3F: scaling performance](https://r3f.docs.pmnd.rs/advanced/scaling-performance) — demand rendering and invalidation rather than a permanent sky loop.
- [Drei: Html](https://drei.docs.pmnd.rs/misc/html) — world-anchored HTML, transforms, portals, occlusion and possible perspective blur. Compare against installed Drei 10.7.9 during the prototype.
- [Three.js: CSS3DRenderer](https://threejs.org/docs/pages/CSS3DRenderer.html) — separate renderer has zoom limitations; no second renderer is proposed.
