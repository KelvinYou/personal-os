# Modern garden town — Design-Lite

[Status: OK] Implemented and locally verified · 2026-11-03

## 1. Context

The owner approved the generated five-building garden-town reference and requested implementation in the existing 3D Office. It supersedes the square courtyard floor in [the previous revision](office-courtyard.md). The reference is retained locally at `data/runtime/ai-office/design/garden-town/reference.png`.

## 2. Scope

Page pattern: existing office overview and selected-worker detail.
Reused components/assets: procedural people, workstations, signs, plants, task UI, player HUD and camera controllers.
New design decisions: irregular grass grounds, connected curved paths, five unequal modern pavilions, coffee entrance and recognizable gym equipment. No new runtime activity or execution features.

## 4. Design and implementation

The existing presentation owner `web/lib/office-layout.ts` continues to own fixed skill seats, now grouped into Maker Studio (6), Library & Reflection (8), Wealth Lab (2), Coach Studio (1) and Travel Atelier (1). The library combines learning/career, logs, reviews, decisions and audits; this changes physical placement only. Scene rendering, static collision and decorative routes consume shared building/furniture geometry.

The two larger rear studios and three smaller side pavilions surround a central tree and shared seating. A compact kopi/teh shelter marks the entry. Building floors meet the ground without stairs. The site outline is irregular, with actual walkable bounds derived from the visible ground outline. Curved paths connect broad front entries; grass remains walkable. The gym includes a rack, weights, bench, mat and a real Coach Planner seat at a planning desk. A skill is not converted into a running trainer process.

Overview uses cutaway roofs to retain employee visibility. First/third-person modes restore full roofs and preserve the same player pose. Roof switches do not remount people. Existing roster discovery, filtering, task assignment, history, review and session evidence retain their owners.

## 7. Trade-offs

Retain procedural assets to avoid introducing an unverified mixed art library. Reuse the prior character/detail level, simplify reference vegetation and use existing flat-floor movement. Five pavilions share one continuous scene; no building-loading transitions. Library staff retain individual fixed places even when furniture is simplified for reading and planning.

## 8. Steps and acceptance

1. Add layout/ground/placement and wall-clearance regression assertions, then update the shared presentation geometry and navigation. Gate: all 18 seats and every doorway reachable, no furniture/wall traversal, filtered seats unchanged, supported extension seats within terrain.
2. Replace the square room with pavilions, curved paths, grass, shade trees, gym and coffee amenity. Match the reference camera and coarse composition first, then refine from actual screenshots. Reuse existing data/controls. Gate: rendered overview and walking captures.
3. Run the existing Office unit suite and typecheck, build an isolated production preview, then run layout, player and synthetic-team browser checks at desktop/390/320px. Inspect fresh screenshots after any visual correction. Retain source hashes and comparison record beside the evidence.

Risks: new walls can trap actors or block cameras; shared wall footprints and reachability checks mitigate this. Decorative routes must leave buildings through open fronts and avoid furniture. The generated reference has fewer visible people than the fixed roster: all 18 actual employees must still remain accessible. Loading, empty, error, partial evidence and renderer fallback remain the existing UI states.

## 9. Open questions

No blocking decisions. Acceptance target is the approved reference's composition, palette and functional landmarks, with deliberately simpler plants and existing character art. Physical-phone performance and dynamic person-to-person collision remain outside scope.

## Contract review

[Status: OK] Layout-only change, with unchanged employee/task/evidence identity contracts.

| Contract | Owner | Consumers | Compatibility / verification |
|---|---|---|---|
| Fixed skill membership and identity | Existing repository catalog and room projection | Existing task composer, worker list, scene | Unchanged; no data migration or API version change |
| Spatial grouping and furniture | `office-layout.ts` | Scene models, seat positioning, navigation obstacles | Five groups contain all 18 existing skills once; filtered/future seats stable |
| Visible terrain and walkability | `groundOutline` | Scene ShapeGeometry and navigation polygon checks | Same outline for rendering and movement; extension seat checks |
| Pavilion walls and entrances | Layout dimensions and `buildingWalls` | Pavilion meshes and navigation/camera collision | Back/side walls solid, open fronts accessible; all seats reachable from spawn |
| Decorative movement | Existing office-life timeline, routed through new entrances | Existing procedural people | No state/evidence mutation; break routes checked against walls/tall props |
| Player input and pose | Existing player controller | First/third/overview cameras and host figure | No input API change; spawn adjusted for clear third-person framing |
| Reference and screenshots | Local design artifacts | Visual comparison record only | Synthetic generated reference, ignored private runtime directory; never sent as session evidence |

Finance calculations, thresholds, runtime execution, private task storage, skill definitions and observation/report schemas are outside this revision. A gym is a presentation landmark; it does not claim the coach is executing a training workflow.

## Acceptance record

- Production build with `NEXT_DIST_DIR=.next-office-garden-production` and web TypeScript validation: passed.
- From `web/`, `node --test tests/office*.cjs`: 53 passed. New/updated checks cover five groups including Coach Planner's gym, stable known/future skill seats, connected access to all 18 employees, terrain bounds, solid walls/open entrances, supported extension seats, decorative break routes and retained player controls.
- `office-courtyard-browser.mjs` on the final production build: passed. The existing layout regression now also captures Coach Studio; all 18 employees, selection, exact seat-anchor equality through filtering, demo isolation, 1440/390/320px containment and no page errors passed.
- `office-player-browser.mjs` on the same build: passed. First/third/overview, movement, touch, reduced motion and focus isolation retained.
- `office-team-browser.mjs` on the same build with synthetic endpoints: passed. Three temporary participants, results, reload, labels, keyboard/fullscreen, desktop/narrow layouts and dark appearance retained. No live model work was dispatched.
- Opened actual production overview, gym-focus, narrow selected-worker and first/third-person captures. Camera framing, player spawn obstruction and washed-out grass were corrected and inspected again in fresh captures. The retained original character art, simplified vegetation/library silhouette and cutaway overview roofs are intentional differences from the concept illustration. No pixel-perfect match is claimed.

The existing preview URL now serves this build: `http://127.0.0.1:3016/office`. Use `/office?mode=demo&scenario=team` for synthetic data. Final Coach Studio was also rendered from this URL after the previous courtyard server was replaced. Intermediate review servers on 3017/3018 were stopped; unrelated pre-existing servers were retained.

Reference, comparison record, source hashes, screenshots and logs are retained locally under `data/runtime/ai-office/design/garden-town/` (ignored private artifacts). Physical-phone performance, dynamic character collisions and live model skill compliance remain unverified. No commit or hosted deployment was performed.
