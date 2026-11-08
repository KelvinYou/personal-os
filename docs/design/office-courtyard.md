# Courtyard studio — Design-Lite

[Status: OK] Implemented and locally verified · 2026-11-03

## 1. Context

The owner chose a courtyard studio with skill-based neighborhoods and requested implementation after the separate first/third-person controls were completed. The current room places all 18 employees in repeated bench rows. This revision gives specialties recognizable spaces while retaining a single connected floor and the existing player controls.

## 2. Scope

Page pattern: existing office overview and selected-worker detail.
Reused components/assets: procedural people, desks, signs, plants, task UI, player HUD and cameras.
New design decisions: planted central courtyard, five open work neighborhoods, travel corner, shared project table and continuous circulation.

## 4. Implementation

A presentation-only layout module owns skill-to-seat mapping, zone bounds, amenity footprints and floor bounds. Office-life consumes seat geometry; the scene renders it; office-navigation derives furniture and camera collisions from it. Filtering must retain each skill's seat. Unknown future skills use an expandable rear studio bay; temporary task participants use index-based seats without becoming permanent employees.

The 18 skills group into daily operations (3), research/career (2), wealth research (2), engineering (6), reflection (4), and travel (1). These are spatial memberships, not task assignments or inferred runtime activity. Shared project furniture carries no fabricated live state.

## 7. Trade-offs

Open neighborhoods retain overview readability and walkable continuity. Separate town buildings would require scene transitions without adding useful task semantics. Physical collision uses the same static footprints as visible props; flat-floor movement and camera controls retain their existing API.

## 8. Risks and verification

Changed room bounds, desks and furnishings require updated collision tests and actual first/third/overview screenshots. Preserve pose across camera switches, keyboard focus isolation, touch controls, worker selection, demo isolation, and empty/error views. Verify known skills keep seats under filtering and all neighborhoods are reachable from spawn. The prior compact 18-person floor assertions are superseded by this explicitly authorized layout revision; other behavioral expectations remain.

## 9. Open questions

No blocking decisions. Art direction follows the existing warm wood, sage and terracotta palette. No data, execution API, employee identity, skill source, private/public boundary or persistence migration is required.

## Contract review

[Status: OK] Presentation-only change; no state or data migration.

| Contract | Owner | Consumers | Migration / verification |
|---|---|---|---|
| Employee membership and identity | Repository skill catalog, `office-skills.ts`, `projectSkillRoom` | Existing task composer, list and scene | Unchanged; roster/room tests |
| Spatial membership and geometry | `web/lib/office-layout.ts` | Office-life seats, scene furniture, player collisions | New local presentation owner; layout and reachability tests |
| Filtered employee placement | Full skill catalog and `skillSeat` | OfficeWorkspace → OfficeScene → labels/people | Known and future skills keep positions under filtering; browser anchor comparison |
| Player pose and camera controls | Existing `office-player.tsx` and navigation functions | Shared host and first/third/overview cameras | Control API unchanged; updated collision geometry and browser regression |
| Task/evidence/private stores | Existing runtime, observation and persistence owners | Existing workbench and team panels | Unchanged; Office API/runtime tests, synthetic browser fixtures |

Finance calculations, personal thresholds, Python/TypeScript report schemas and skill instructions are outside this change. Spatial names never prove live work, task assignment or collaboration.

## Acceptance record

- `npm --prefix web run typecheck` and production build with `NEXT_DIST_DIR=.next-office-courtyard-final`: passed.
- From `web/`, `node --test tests/office*.cjs`: 51 passed. Includes current roster membership, stable filtered/future employee seats, connected paths to all 18 employees, extension chairs within the floor, normalized movement, collisions and existing execution/evidence contracts.
- `web/tests/office-courtyard-browser.mjs`: passed on final production build; all 18 employees, selected-worker detail, exact seat-anchor equality under filtering, zero private API calls in demo, and 1440/390/320px with no horizontal overflow or page errors.
- Existing `office-player-browser.mjs`: passed on final production build; first/third/overview, walking, touch release, reduced motion and focus isolation.
- Existing `office-team-browser.mjs`: passed against synthetic intercepted endpoints on final production build; worker labels/selection, native-team view, keyboard/fullscreen, reload and results retained. No live model work was launched.
- Final overview, walking and narrow selected-worker screenshots were opened for visual inspection. Local screenshots, source hashes, logs and the six-criterion visual record live under `/tmp/office-courtyard-evidence/`. The text brief is the visual target; no photo-match percentage is claimed.

Preview: `http://127.0.0.1:3016/office`; synthetic scene: `/office?mode=demo&scenario=team`. The final server binds loopback only. Temporary courtyard servers on 3014/3015 were stopped; pre-existing sessions/servers were retained. Physical-phone performance, dynamic worker-to-player collision and live model skill compliance remain unverified. No commit or hosted deployment was performed.

## Subsequent garden-town revision — 2026-11-03

The approved [modern garden town](office-garden-town.md) supersedes the courtyard floor with five pavilions, organic terrain and a Coach Studio gym. Earlier acceptance records above describe their original revisions. Current layout, collision and visual evidence belong to the garden-town document.
