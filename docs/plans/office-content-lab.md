# Office Content Lab — Delivery plan

[Status: OK] V1 implemented; local acceptance completed with scoped regression reruns · 2026-11-09

Technical owner: [Content Lab design](../design/office-content-lab.md).
This file alone owns phase status and implementation checklists. The owner reviewed the plan and authorized implementation. Current code adds
the building, workstations, briefs, output review and validated result records.

## Phase 0 — Establish dependencies and executable capabilities

- [x] Re-read the working tree: Office geometry and immersive-shell work may be concurrent; preserve unrelated changes.
- [x] Check whether the [immersive Office shell](../design/office-immersive-world.md) has landed. If not, v1 uses the existing department-panel pattern (Finance's); if it has, use its work panel. Never build a competing fullscreen system.
- [x] Check installed official research/image tools and exercise the actual Office runtime. Record available, unavailable and unverified capabilities separately.
- [x] Define local-send versus client-handoff behavior before exposing task buttons; retain existing runtime policy.
- [x] Capture the current world using `make scene-reset` and `make scene-preview SCENE=office`; open the baseline before any scene change.

Exit: integration points and capability boundaries have evidence. A missing online
tool can use the designed handoff; it cannot be represented as working automation.

## Phase 1 — Build one usable spatial slice

- [x] Search existing packs with `make scene-assets QUERY=desk` and board-related queries; inspect bounds and orientation. Prefer existing aliases and modules.
- [x] Add the `content` department, a distinct open Content Lab and four labelled stations in the default world.
- [x] Update combined town extent, overview framing, ground/path layout, collision/landscape exclusions and interaction targets together. Preserve existing radar/Finance coordinates and classic town.
- [x] Add department-specific station parsing and deep links; remove binary Lab/Finance assumptions in selection, signs and active-state rendering.
- [x] Open a real existing post through Review using the current reader/API in the department work panel chosen in Phase 0. Include keyboard/touch/non-3D access.
- [x] Inspect fixed-camera desktop and narrow previews before repeating props or polishing materials.

Exit: walking or clicking reaches Review and opens actual output while the same
Canvas, player pose and camera stay mounted. The building is useful before new analytics exist.

## Phase 2 — Connect research and production work

- [x] Research brief collects audience, reader problem, candidate questions, demand/competitor evidence and freshness limitations.
- [x] Production brief names the selected topic, primary sources, intended claim, requested files and factual/visual checks; resolve private identity at runtime.
- [x] Reuse existing `social-post`, DirectTask and saved work history for compatible local tasks; keep one execution controller and solo default.
- [x] Offer complete copyable client briefs for capabilities unavailable in Office, naming the existing private post-folder convention.
- [x] Refresh actual files and task evidence after work. Distinguish preparing, working, blocked, client handoff, failed and output observed.
- [x] Ensure stop, retry with the same request ID, busy state and panel close/reopen preserve the existing task guarantees.

Exit: one task moves from brief to observed output through a truthful local or
client path. No unobserved production is shown as complete.

## Phase 3 — Record experiments and review results

- [x] Add the lab v1 Pydantic model under `scripts/lib/` and its export script (`content-lab.schema.json` + `.gen.ts`, `--check` for drift), following the finance-workbench export.
- [x] Add `make posts-check`: validate every `lab.yaml` plus cross-file rules; each error names the post and field. Prove it fails on a synthetic `ready` record with missing images.
- [x] Implement the bounded read projection using the same rules; update private layout documentation alongside the reader.
- [x] Edit `social-post` steps 1 and 7 to record gate results and seven-day measurements in `lab.yaml`, then run `make posts-check`. Leave existing prose gate tables in `post.md` untouched.
- [x] Add synthetic legacy, valid, invalid, missing and incomplete records; require publication evidence and readiness prerequisites.
- [x] Show hypothesis, changed variable and linked task evidence. Keep task execution, content readiness and publication as distinct states.
- [x] Read manually recorded publication/measurement evidence. Show metric definitions, sample size, observation dates and unknown values.
- [x] Compare like-aged measurements and prepare the next experiment; do not label a series successful from a single outlier.

Exit: a recorded post can be traced from hypothesis to files to publication and
observed results; `lab.yaml` is the only structured source of gate results and
measurements. Legacy content remains accessible without invented metadata.

## Phase 4 — Verify the integrated workflow

- [x] Test department-specific URLs, old Finance/legacy URLs, bounds/collision, record validation, guarded APIs, partial data and unknown/zero distinctions with synthetic fixtures.
- [x] Cover the browser journey: enter lab → research brief → actual local task or handoff → review carousel/copy → recorded results → return to the unchanged world.
- [x] Check loading, empty, unavailable, stale, interrupted and retry states; execution disabled/busy; focus, fullscreen portals and movement keys while typing.
- [x] Update `.agents/skills/verify-web/features/office.md` for every new route/control/entry point in the implementation change.
- [x] Run `make test`, `make posts-check`, `make design-check`, `make scene-plan` and `make scene-check`; inspect selected files/scopes and broaden coverage where needed. Run pre/post affected movement/camera browser suites when their behavior changes.
- [x] Complete verify-web's isolated launch → doctor → journey → evidence → cleanup with real local data, avoiding public captures of private content.
- [x] Inspect screenshots at 1440, 390 and 320 px, light/dark and reduced motion. Record fixed-camera renderer deltas; explain any rise above the scene standard's resource budget.
- [x] Record capability gaps and evidence paths, then `make scene-stop`. Only call the workflow complete after the preceding exit criteria pass.

## Delivery boundary

V1 delivers one XHS carousel workflow in a useful 3D building, supported by real
research/production capability or explicit client handoff, output review and
manual evidence-based iteration. Automatic platform analytics, browser record
editing, video, multi-account operation and permission/runtime expansion are
separate future decisions. There is no publishing, commit or deployment in this plan.


## Verification record — 2026-11-09

- `make test`: 514 Python tests, web typecheck and 124 web tests passed during
  the final integration sweep. The final post-ID boundary adjustment also passed
  the focused Python content-lab suite (5 tests).
- `make posts-check`, `make design-check`, `make doctor` and `git diff --check`
  passed. Doctor reports the pre-existing offline private-data directory is not
  an independent Git repository; no repository was initialized.
- `make scene-plan` selected all nine scene suites. The first `make scene-check`
  reused another run's port 3027 and lost its server; later connection failures
  were infrastructure failures, not successful tests. The isolated run used
  `TEST_PORT=3067 TEST_OUTPUT_DIR=.scene-preview/browser-3067` and passed 15/18.
  Its two department failures were substring selectors made ambiguous by Content
  Lab; those now match Lab exactly. The Home failure was a timed movement
  assertion; no Home code or assertion was changed.
- The final isolated browser command, using `.scene-preview/browser-final`,
  passed all 12 tests across Content Lab, Office departments, Home interactions,
  Posts and Finance workbench. Together with the unchanged camera, character,
  courtyard, player, radar and team successes from the broad sweep, all selected
  scene behaviors have passing evidence. The original `make scene-check` log
  remains recorded as nonzero; it is not relabelled a passing invocation.
- Verify-web's isolated preview server served real private posts. The real-data
  journey opened an existing carousel, displayed its image and copied actual
  publication text without API writes or replacing the Canvas. Screenshots were
  inspected at 1440/390/320, including dark and reduced motion. The narrow-world
  clipping/fog failure and the reader's page-specific inline CSS were corrected.
- Resource isolation at the same final demo camera: building visible versus
  building props/floor/wall hidden yielded 650 versus 581 draw calls (+11.9%)
  and 80,506 versus 74,142 triangles (+8.6%). Geometry/texture allocations stay
  211/31 while visibility toggles. This measures the new building's drawing cost,
  not a historical whole-town memory delta; additional landscape/signs remain
  in both captures. The increase above 10% is the added modular walls/furniture;
  floor tiles remain instanced, with no new asset pack or textures downloaded.
- Evidence root: `web/.scene-preview/evidence/`; final browser artifacts:
  `web/.scene-preview/browser-final/`. Capability probe, actual review journey,
  renderer JSON and complete run logs are retained there. The probe performed
  one actual official search; image generation execution remains unverified.
- Local tasks reuse the single existing runtime and its saved history. Full
  client image production and platform publication were not exercised; v1's
  explicit client handoff remains the supported boundary. No publishing,
  repository initialization, commit, push or deployment was performed.

Page pattern: overview → stage detail → evidence. Reused assets: Kenney local
modules, shared controls/DataState, PostsLibrary, DirectTask and the concurrent
shared fullscreen/panel owner. New decisions: a third building, optional
Python-owned lab record, explicit client handoff and age/coverage-based results.

## UX revision — hands-on review follow-up

Owner authorization: “做”, after the Chrome UX review on 2026-11-09.

- [x] Wide/compact work panel; composer-first task layout; history collapsed.
- [x] Prepare task opens and focuses the existing editor, retaining explicit Send.
- [x] Cover-first review with selected post title, compact status and owner decisions.
- [x] Independent fit-to-screen image dialog, paging, Escape and focus return.
- [x] Narrow screens start with work controls and a Show scene toggle.
- [x] Local results form preserves null versus zero, saves through Python validation,
  detects stale revisions and retains drafts on failure.
- [x] Add generated write union, bounded same-origin live POST, API-writer lock,
  idempotent retries and atomic lab.yaml replacement; no legacy backfill.
- [x] Update design contract, private posts guidance and verification feature map.

Validation: `make test` passed 517 Python tests and 126 web unit tests, including
API guards; typecheck, schema drift, posts-check and design-check passed. Design
check retains two existing light-theme series contrast warnings. Scoped browser
reruns passed Content Lab (five journeys, including owner approval/revision
preparation), Posts and Workbench (seven total across two runs), plus
the Finance walking journey. Immersive fullscreen/fallback/narrow journeys passed
in the wider regression run. That run exposed a broad alert test selector and
lost keyboard focus at the last carousel image; both were corrected before the
successful rerun. Finance walking also failed in the combined run and passed
its isolated rerun; this revision does not change movement or camera geometry.

Private visual evidence, opened and inspected:

- `web/.verify-web/2026-11-09T03-58-28-575Z-content-ux-review/`
- `web/.verify-web/2026-11-09T04-01-07-494Z-content-ux-research/`
- `web/.verify-web/2026-11-09T04-02-09-190Z-content-ux-mobile-final/`
- `web/.verify-web/content-ux-review-save/` (owner approval and revision preparation)
- `web/.verify-web/content-ux-final/` (synthetic saves, reload/conflict, focus,
  320/390/1440 layout, dark/light and existing Posts/Workbench)

Hands-on Chrome also confirmed full image fitting, the wide editor's focus and
collapsed history. No task was sent and no live review/metric record was written.
The initial verify-web composer drive omitted required topic/audience and correctly
found Prepare disabled. The first mobile drive waited for the intentionally hidden
scene; the maintained mobile journey now waits for the visible work panel instead.


## Autonomy revision — owner ideates and reviews only

Owner authorization: “做”, 2026-11-09, after the autonomy research. Design: [autonomy revision](../design/office-content-lab.md#autonomy-revision--2026-11-09).

- [x] Record: `idea` stage and runner-owned `pipeline` block (additive; legacy records read as idle).
- [x] Commands: `approve_idea`, `archive`, `requeue`; change requests with a note re-queue; all rejected while a run owns the post.
- [x] Runner `scripts/content_pipeline.py` / `make content-run`: one at a time, oldest first, interrupted runs fail, runner-owned gate decides `review`, ntfy push on review/failure.
- [x] Headless `claude -p` confinement proved by smoke runs: project settings only, `dontAsk`, writes limited to the post folder, Codex only as `codex exec -s workspace-write -C <post folder>`. The first smoke run exposed the owner's local blanket allows overriding the allowlist; fixed before enabling.
- [x] Skills: `content-ideas` (brainstorm and file ideas), `social-post` autonomous mode (no questions, web demand evidence, Claude-as-critic on Codex images, two regeneration rounds, sameness check).
- [x] UI: Ideas and Pipeline boards replace the brief/handoff stations; Review requests re-queue without a task send.
- [x] `make test` (527 Python, 30 web files), Content Lab browser suite 6/6, departments 4/4 isolated; `make posts-check`, `make design-check`, `make flows`.
- [ ] First real end-to-end run on an owner-approved idea (cost, duration, and how often the checks fail).
- [ ] Next slice: screenshot-to-metrics ingestion, weekly learner feeding the idea agent, critic calibration on past owner rejections, launchd fallback.
