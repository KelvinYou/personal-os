# Office town: Lab and Finance

[Status: OK] Design-Lite · Implemented locally · 2026-11-08 (flat town supersedes the street the same day)

Current extension: [Finance workbench](finance-workbench.md) owns durable funding
tasks, monthly allocation, cash scenarios and guarded private evidence writes.
The Lab's attention semantics remain owned by [the attention radar](office-attention-radar.md).

## Outcome and scope

`/office` is one flat town. The first building is the **Lab** (the attention
radar, unchanged at its original origin); the second is **Finance** (three
desks). Both are roofless, with only a back wall row and no side walls, and
stand on a grass town: a main avenue in front, a front path from each building,
a paved plaza between them with a round planter, benches and shade trees, and
trees, shrubs, flower beds and street lamps around. There are no doors and no
page change between departments. kelvin.ai walks anywhere in the town under
explicit input (overview WASD, first person, third person); F at a Finance desk
opens it, F near a Lab person selects them.

Owner direction (2026-11-08): entering and leaving the Lab and Finance was too
much friction; show the whole town as departments, flat, with walls not fully
enclosing each building; a whole town with flowers, grass and trees rather than
a walkway joining two floors; a controllable person with a third-person view.

Page pattern: town overview (both buildings) → department panel (Lab queue or
Finance workstations) → evidence (Lab timeline or Finance detail).
Reuse: RadarScene, KenneyAsset/Modular Space Kit, TownSign, Button, SectionCard,
DataState, PrivacyProvider/Money, AllocationBar, MaturityPanel, DataHealth,
FinanceWorkbench. New decisions: department tabs with live notes, projected
department and desk buttons, `dept`/`station` deep links.

## Architecture and ownership

```text
/office (server: roster + wealth report v4 + workbench notice; demo → synthetic fixture)
  -> OfficeWorkspace  [department state, tabs, URL sync]
       -> RadarScene  [KenneyTownShell + Lab radar + FinanceBuilding, one Canvas]
       -> Lab:     AttentionQueue / RadarDetails / OfficeTimeline / Office tasks
       -> Finance: FinanceAside / FinanceDetail (components/office/finance-department.tsx)
/office/world[?place=finance]  -> redirect to /office[?dept=finance] (old links)
```

| Contract | Owner | Consumers | Verification |
| --- | --- | --- | --- |
| Building footprints, plaza, paths, greenery placement (seeded LCG), walk world, spawn, desk positions, deep links, legacy redirect | `web/lib/office-departments.ts` | Town shell, `town-landscape.tsx`, scene, workspace, world redirect | `web/tests/office-departments.test.ts` |
| Walking, cameras, HUD, F interaction | Shared `office-player.tsx` + scene standard §2–3 | Town scene | `office-departments` browser walk journey |
| Finance notice (amount-free) | `web/lib/office-finance.ts` | Department tab, floor notice, Finance aside | same unit file |
| Wealth values | Python report v4 + `loadReport` | Finance detail | No schema change; demo never calls the private loader (unit test) |
| Lab attention, slots, camera rules | `office-radar.ts`, radar design | Lab building | `office-radar` browser suite |
| Town journey | — | `/office` | `web/tests/browser/office-departments.spec.ts` |

The Lab keeps the radar room's coordinates, so every attention slot and station
is unchanged; a unit test asserts all pads and stations stay inside the Lab
footprint. Finance desks are interaction targets only: clicking a desk, its
projected button or a workstation button opens the same detail.

## Interaction and states

| Input | Result |
| --- | --- |
| Any load, any width, any deep link | The overview is centred on kelvin.ai at whole-town distance and follows them as they walk; drag and scroll keep working (owner: never lock onto one building) |
| Department tab / projected building name | Panel and evidence switch, a ground outline marks that building, `?dept=` updated; the camera does not move |
| Finance desk (3D, projected button, aside) | Finance + that workstation; `?station=` updated |
| Selecting a person | Lab panel; the camera is not moved |
| Overview WASD / First person / Third person | kelvin.ai walks at one brisk speed (the standard run speed; no separate run); trees, benches, planter, desks, lamps, beds and back walls block; people do not |
| F near a Finance desk / Lab person (walking) | Opens that workstation / selects that person; a `F · …` button shows the nearest target |
| Esc / R | Back to overview / back to the plaza spawn |
| `?dept=finance&station=assets` | Opens directly there, survives reload |
| `/office/world?place=finance&mode=demo` | Redirects to `/office?dept=finance&mode=demo` |

### Town attention

The Lab radar counts agent sessions. Other departments' owner decisions are
counted by `web/lib/office-attention.ts`, the single definition used by the
department buttons, the in-world HUD, the `ELSEWHERE IN TOWN` rows under the Lab
queue, the live tab-title count and the screen-reader summary:

| Department | Waits on the owner | Opens |
| --- | --- | --- |
| Content Lab | Posts in `review` with an idle pipeline; failed runs (same kinds as the `content_review` / `content_failed` phone push) | Review / Pipeline station |
| Finance | Research proposals with status `ready_for_review` | Research desk |

Ideas are excluded: an idea becomes work only after the owner says go, so it is
backlog, not a wait. Unavailable sources add no wait (never a zero claim); each
station keeps its own error. Replay hides the rows, since they are current
records, not part of the replayed day. The Research desk reports its proposals
back after a review so the count stays current without a reload.

Review latency: `readiness.reviewed_at` records every owner decision (the runner
restores it, so an agent cannot write it). `review_waits` in
`scripts/lib/content_lab.py` opens a wait at each succeeded run and closes it at
the next change-request note or decision; `make agent-wait` and weekly §4.6 add
one Content Lab line (reviewed, median/longest hours, still waiting, and
decisions made before the field existed as "without a recorded review time").

Report unavailable: Finance tab reads "Finance data unavailable", detail shows
the error; the Lab is unaffected. WebGL loss: tabs, queue and workstation buttons
still work. Amounts are masked by default. Demo reads no private sessions or
finance files.

## Trade-offs

One canvas holds both buildings and the landscape: departments switch
instantly and stay spatially related, at the cost of loading the Finance props
and greenery with the Lab. Greenery is original low-poly primitives (no plant
asset kit is bundled); repeated parts are instanced, one draw call per part.
Lab people still move only on observed state; only kelvin.ai walks.
The private wealth report is loaded with every `/office` request so the Finance
tab can show its notice; it is local-only and masked. A new building is added
only when a recurring task earns a destination.

## Town verification — 2026-11-08

- `make test`: 509 Python tests, 113 web unit/contract tests and typecheck passed. `make design-check`: OK, two existing chart-series contrast warnings, no new rule violations.
- `make scene-check` (all suites, because the town scene owns its camera): 14/14 passed, including `office-departments` (department switching, deep links, legacy redirects, reload, 320/390, dark, and a third-person walk from the plaza to a Finance desk with F, Esc and the touch joystick), `office-radar`, `office-player`, `office-camera`, `office-courtyard`, `office-team`, `office-characters` and `home-interactions`. `finance-workbench` passed separately (3/3) on the new `?dept=finance` route.
- verify-web (isolated server 3041, evidence under ignored `web/test-results/verify-web/2026-11-08T1[12]-*`): demo Notices desk, real `/office?dept=finance&station=assets` (masked), real live town with landscape, and real live Third person `[Status: OK]`. A 390 px `--click 'Notices'` drive failed by design: desk buttons are hidden at ≤ 640 px; the feature map now says so. Warm `/office` responses took 0.21–0.23 s including the report load.
- Visual: warm previews (ignored `web/.scene-preview/evidence/2026-11-08T12-*`) show both buildings on grass with the avenue, plaza, planter, trees, shrubs, flower beds and lamps; third-person screenshots show kelvin.ai in the plaza and at the Assets desk with the `F · Open Asset overview` prompt.
- [Status: Warning] Renderer readout at the default camera: 132 calls / 17,214 triangles / 72 geometries / 5 textures (Lab only) → 480 / 46,886 / 144 / 10 (two buildings) → 565 / 68,620 / 189 / 10 (with the landscape). Causes: the Finance building and both buildings in view, then greenery; instancing keeps trees, shrubs and flowers to one call per part. The Lab baseline itself is unstable (132 vs 381 in the street release, below), so the size of the rise is not established. No FPS claim; physical-phone performance is unverified.

## History: street release verification (superseded 2026-11-08)

[Status: OK] Financial and observation owners are unchanged. There is no schema
migration, API write, duplicated valuation or private value in source fixtures.
Demo uses `tests/fixtures/report_contract.json`; a route unit test proves it
never invokes the private loader and that the street receives no detailed report.
Existing dashboard maturity links now have an explicit `#maturity` anchor.

- `make test`: 485 Python tests, 107 web unit/contract tests, and typecheck passed.
- `make design-check`: passed; two existing chart-series contrast warnings remain.
- Scene scope: radar, classic player/camera/courtyard/team, characters and home
  passed in the broad run. That run loaded an older desk-only collision
  expectation while chair footprints were being added; the final world suite
  was rerun against the chair-inclusive scene and current test source.
- World journey covers Lab exit, running along the street, V, F entry, desk
  interaction, masked assets, analysis handoff, return, direct URLs, reload,
  collision, focus guard, 390/320 touch and dark. Requests remain read-only.
- Visual checks opened the warm Lab baseline/final, street, Finance assets,
  mobile street and indoor 320/dark screenshots. The fixed-camera Lab adds only
  HTML navigation; the new street and interior are independently loaded.
- Fixed-camera street readout: 116 calls / 6,346 triangles / 38 geometries /
  8 textures. Finance: 90 / 7,766 / 31 / 5. No runtime assets were added.

[Status: Warning] The Lab's existing demand-render/contact-shadow readout is not
stable enough to establish a performance delta: initial capture reported
132 / 17,214 / 72 / 5; a later capture 381 / 40,794 / 137 / 10; forcing a reset
sampled a one-call, two-triangle pass. These are different loading/render-pass
samples, so the >10% raw difference is not evidence of an added scene cost or
of a speed improvement. Raw evidence is retained; a stable after-render sampler
is needed before making a performance claim. No FPS or speedup claim is made.

Evidence lives in ignored `web/.scene-preview/evidence/` and
`web/test-results/verify-web/`; browser regression screenshots live under
`web/test-results/office-world-*`. The prior scope run is retained under
`web/.scene-preview/regression-scope-run/`. No release, commit or deployment
is part of this delivery.
