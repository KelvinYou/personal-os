# Office (town: Lab, Finance and Content Lab)

Design owners: [office town](../../../../docs/design/office-world.md) (departments, layout, deep links) and
[attention radar](../../../../docs/design/office-attention-radar.md) (the Lab).

## Sub-features

- Background music: `Play music` / `Pause music` (visible label BGM) and `Music volume`
  in the town toolbar, also in fullscreen. Local **Carefree** by Kevin MacLeod, 96 BPM,
  upbeat ukulele/guitar/marimba, about 3:25 with repeat playback. Visible music credit and CC BY 4.0 link.
  Silent on entry; remembers volume only. Department
  changes and fullscreen preserve playback; leaving Office stops it. Classic town is frozen.
  Drive: `--route '/office?mode=demo&scenario=team' --wait-for '.radar-canvas-shell[data-assets-ready="true"]' --click 'Play music' --click 'Pause music' --label office-music --read-only`.
- Header "Who needs you right now?" with a source badge (`LIVE · READ-ONLY`, `DEMO · SIMULATED EVENTS`)
  and the Codex / Claude coverage line.
- Source bar: Source select (`Live office` / `Demo office`), attention summary
  ("N need you · N ready for review · N working · N done"), `Alert me` (live only, browser
  notification + tab-title count), `Classic town`, `Collaboration`, `Refresh`.
- Departments nav (`Lab · N need you`, `Finance · <notice>`, `Content Lab`): one flat town, three buildings in one
  canvas; switching never changes page. Projected building names always sit over the scene, with an
  owner-wait count badge (CSS `data-badge`; the button name stays the building name). Workstation buttons
  (`Assets`, `Notices`, `Workbench`, `Research`; `Ideas`, `Pipeline`, `Review`, `Results`) and the Content
  Lab summary board appear only for the selected building; projected buttons and person labels push each
  other up instead of overlapping. Deep links: `?dept=finance&station=assets|notices|analysis`. Old
  `/office/world[?place=finance]` links redirect here.
- Radar scene: four zones (Needs you, Ready for review, Working stations, Done shelf), floating
  labels with zone time and skill badge, `Name labels` toggle, camera reset/zoom/focus.
- Attention queue (right panel, "LOOK AT NEXT"): needs-you then review, oldest first; a row opens
  session details with `Back to queue`. Below it, `ELSEWHERE IN TOWN` lists other departments' owner
  decisions (`web/lib/office-attention.ts`): `Content Lab: N posts to review` / `N runs failed` and
  `Finance: N proposals to review`; a row opens that station. The same labels appear on the Content Lab
  and Finance department buttons (hidden ≤ 640 px) and the fullscreen HUD. Demo seeds one Finance
  proposal and no Content Lab wait. Drive:
  `--route '/office?mode=demo&scenario=team' --wait-for '.radar-canvas-shell[data-assets-ready="true"]' --click 'Finance: 1 proposal to review' --expect-text 'Research desk' --label town-waits --read-only`
  (expectations run after clicks, so assert `ELSEWHERE IN TOWN` in a separate drive without the click).
- Day timeline ("TODAY"): one lane per session, `Replay day`, `Back to live`, slider "Replay time".
- `Office tasks` (live only, collapsed): workbench + task composer.
- `Fullscreen` (town toolbar): native fullscreen of the world, or a labelled expanded view when the
  browser declines or lacks it (iPhone). The HUD keeps the department buttons, `Hide panel` /
  `Show panel` and `Exit fullscreen`. The queue, details, Finance detail, timeline and tasks move into
  the side panel (a bottom sheet at ≤ 760 px, closed on entry) without remounting. Escape: walking
  view → overview, then panel detail, then leave expanded; in native Chromium fullscreen a held Esc
  exits. Suite: `office-immersive`. Drive:
  `--route '/office?mode=demo&scenario=team' --wait-for '.radar-canvas-shell[data-assets-ready="true"]' --click 'Fullscreen' --expect-text 'Exit fullscreen' --label fullscreen --read-only`
  (`drive.mjs` runs every `--wait-for` before clicking, so never wait for the fullscreen class).
- Classic town (frozen): `/office?scene=town` — the former garden town, walk/cameras, worker list,
  posts board. Its suites: `office-player`, `office-camera`, `office-courtyard`, `office-team`,
  `office-posts`, `office-workbench`.
- Posts moved to `/posts` (nav **Posts**).
- Content Lab: `?dept=content&station=research|production|review|results` (titles Ideas / Pipeline / Review / Results), a third building west of the Lab. Projected station buttons, click/F interaction and the accessible workstation nav open the same panel. The default/fullscreen world and composer retain their owners.

## Content Lab journey

Select **Content Lab** in Departments or the in-world HUD. Station ids are unchanged;
their titles changed in the autonomy revision: `research` = **Ideas** (heading *Ideas board*),
`production` = **Pipeline**. Ideas lists `stage: idea` records filed by the `content-ideas` skill,
with **Approve idea** (queues and, when `office.content_pipeline.enabled`, starts the detached
headless run) and **Archive**. Pipeline shows queued/running/failed work with the last run's
reason and log name; failed runs offer **Retry run** and **Archive**. Expand/Compact workspace
changes width; mobile starts with the scene hidden and exposes Show scene/Hide scene.
Review shows cover cards through PostsLibrary. Enlarge image opens a separate
fit-to-screen dialog; Escape returns focus to its trigger. **Approve content** saves
owner review; **Request changes** (with a note) re-queues the pipeline, no task is sent; **Archive** stops it.
Never approve, request changes or archive on live data during verification: each is a real owner decision. Results reads optional Python-validated `lab.yaml` records and offers
Record published post results for already-published links and observed counts.
Never enter invented metrics into live data during verification. Synthetic tests
cover saves, reload and conflict retention. Zero, unknown and unavailable remain distinct. The explicit comparison
window is 168–192 hours after publication, grouped by traffic coverage. Fewer
than three comparable posts remains an incomplete comparison.

```bash
cd web && node ../.agents/skills/verify-web/scripts/drive.mjs --port 3041 \
  --route '/office?dept=content&station=research' --heading 'Content Lab' \
  --wait-for '.radar-canvas-shell[data-assets-ready="true"]' \
  --expect-text 'Ideas board' --label content-ideas --read-only
node ../.agents/skills/verify-web/scripts/drive.mjs --port 3041 \
  --route '/office?dept=content&station=review' --heading 'Content Lab' \
  --wait-for '.radar-canvas-shell[data-assets-ready="true"]' \
  --expect-text 'Final carousels and publication copy' --label content-review --read-only
node ../.agents/skills/verify-web/scripts/drive.mjs --port 3041 \
  --route '/office?dept=content&station=results' --heading 'Content Lab' \
  --wait-for '.content-lab-panel:not([hidden])' \
  --expect-text 'Results board' --width 390 --dark --label content-results --read-only
```

Demo uses synthetic lab metadata and never reads private posts. To see real
carousels use Live office; missing optional records show unknown, not published.
Keep screenshots private. Synthetic browser suite: `content-lab`.

## How to get to it (user POV)

Top nav **Office**, or open `/`. Demo without private config: `/office?mode=demo&scenario=team`
(busy day across all zones). Classic town: `Classic town` button or `/office?scene=town`.

## Driving it with drive.mjs

```bash
cd web && node ../.agents/skills/verify-web/scripts/drive.mjs --port 3041 \
  --route "/office?mode=demo&scenario=team" --wait-for canvas --wait-for .radar-label \
  --expect-text "Who needs you right now" --expect-text "LOOK AT NEXT" --label radar-demo
cd web && node ../.agents/skills/verify-web/scripts/drive.mjs --port 3041 \
  --route "/office?scene=town&mode=demo&scenario=team" --wait-for canvas --wait-for .office-host-label \
  --expect-text "Radar view" --label town-frozen
cd web && node ../.agents/skills/verify-web/scripts/drive.mjs --port 3041 \
  --route /posts --expect-text "Final carousels and publication copy" --label posts-route
```

Proof: `after.png` shows people standing in zones with labels and the queue on the right;
`writes` is empty.

## Gotchas

- Wait for both `canvas` and `.radar-label` (radar) or `.office-host-label` (town); otherwise the
  screenshot is an empty room that still reports `pass`.
- Live mode reads the owner's Codex and Claude Code sessions; labels show generated person names
  and skill ids only, but prefer demo mode unless the change is about live observation.
- Done-shelf labels are hidden unless selected; on screens ≤ 760px only needs-you labels show.
- Movement/camera changes need `make test-browser SUITES="office-radar office-player office-camera"`
  before and after (AGENTS.md).

## Kenney Mini characters

`/office/characters` previews original locally bundled Kenney Mini Characters 2.0 (CC0).
Check the six-role lineup, select a character, switch Standing / Seated and Front / Side / Back.
The labels describe the role family, not bespoke garments. The official asset keeps its palette.

```bash
cd web && node ../.agents/skills/verify-web/scripts/drive.mjs --port 3041 \
  --route /office/characters --wait-for canvas --expect-text "Small team. Big character." --label mini-cast
node ../.agents/skills/verify-web/scripts/drive.mjs --port 3041 \
  --route /office/characters --wait-for canvas --click Seated --click Side --width 390 --label mini-seated
```

The radar shares these figures, original Modular Space Kit floor/wall/gate modules and Furniture Kit props.
Wait for `.radar-canvas-shell[data-assets-ready="true"]` in addition to labels before capturing the world.
Home uses the same source geometry; its architectural style stays Walnut House.


## Finance department

The second building of the town. `Finance` tab, a projected desk button, a click on a desk or
`?dept=finance` opens it; the panel shows the amount-free notice and four workstation buttons, and
the detail below shows Asset overview, Finance notices, the Finance workbench (default) or the Research desk
(Finance manager proposals; `station=research`, the `Research` desk button or a click on the Finance manager). Amounts
remain masked until Show amounts. Finance notices renders `report.attention` (the `/finance`
"Needs attention" list, links into `/finance#<tab>`); the aside notice shows an open workbench
task first, otherwise the first attention item. Demo (`&mode=demo`) uses only the canonical synthetic wealth
fixture (proof text: `Matured 16 days ago`). Every width and deep link frames the whole town; the selected building gets a ground outline.

```bash
cd web && node ../.agents/skills/verify-web/scripts/drive.mjs --port 3041 \
  --route '/office?mode=demo&scenario=team&dept=finance' --wait-for '.radar-canvas-shell[data-assets-ready="true"]' \
  --click 'Notices' --expect-text 'Finance notices' --label town-finance --read-only
cd web && node ../.agents/skills/verify-web/scripts/drive.mjs --port 3041 \
  --route '/office?dept=finance&station=assets' --wait-for '.radar-canvas-shell[data-assets-ready="true"]' \
  --heading 'Finance' --expect-text 'Gross tracked assets' --label finance-assets --read-only
cd web && node ../.agents/skills/verify-web/scripts/drive.mjs --port 3041 \
  --route '/office?mode=demo&dept=finance' --wait-for '.radar-canvas-shell[data-assets-ready="true"]' \
  --click 'Research' --expect-text 'Who is ahead at year 20' --expect-text 'Demo proposals cannot be reviewed' --label research-demo --read-only
```

Research desk: amounts stay masked and the what-if inputs are hidden until Show amounts. What-if sends
`POST /api/finance/research` `op: whatif` (never saved); Accept / Ask for revision / Decline append to
private `data/finance/research/reviews.jsonl` — never click them in a real-data capture.

Walking: `Overview` / `First person` / `Third person` (top-left of the town). kelvin.ai starts in the
plaza; the overview follows them; WASD / ↑ walk (one brisk speed, no run), ← → turn, F at a desk opens it (`F · Open …` button), Esc returns
to overview, R to the plaza; touch uses the joystick. The live pose is `data-player` on
`.radar-canvas-shell`. Department switching, desk buttons, deep links, legacy redirects, reload,
320/390, dark and the third-person walk to a desk are in `office-departments.spec.ts` (synthetic records only). Do not click Show amounts in real-data captures.
`--click 'Finance'` hits the top-nav **Finance** dashboard link first; use `?dept=finance`, then click a
desk button (`Notices`, `Assets`, `Workbench`, `Research`). Desk buttons do not exist while the Lab or
Content Lab is selected.
At ≤ 640 px the desk buttons are hidden (too small over the whole town); drive Finance there
through `?dept=finance&station=…`, not `--click 'Notices'`.

## Durable finance workbench

Default entry: `/office?dept=finance` (Finance opens the workbench). The workbench loads independently
of the valuation report. Funding task creation can link a reported purchase;
only that purchase becomes confirmed. To edit movement evidence, first choose
**Show amounts** (synthetic journeys only), select a step and status, enter
original-currency amount and evidence, and **Save step evidence**. Reload retains
the selected record's revisions. A stale revision displays a conflict and retains
the unsaved draft until an explicit reload.

**Monthly allocation** and **Scenario comparison** require a worksheet title,
current assumptions/date and an explicit **I confirm these inputs are current**.
**Calculate & save result** runs Python calculations and saves inputs and results.
**Mark result reviewed** persists review status, never a transfer or trade.
Policy & missing inputs lists unconfigured keys; missing emergency settings block
allocation. Money and evidence stay hidden by default. Real-data capture must
never reveal amounts or submit a write.

Demo routes use synthetic seed data plus browser session history replayed by the
same Python command path in a temporary directory. **Reset demo** clears only
that browser session. Demo POSTs are expected in mutation journeys; they cannot
write private finance files. Test suite: `finance-workbench` (save/reload,
independent evidence, conflict draft retention, allocation, review, scenarios,
320/390 dark). The conflict UI response is injected; actual concurrent-revision
rejection is covered by Python storage tests.

```bash
cd web && node ../.agents/skills/verify-web/scripts/drive.mjs --port 3041 \
  --route '/office?dept=finance' --wait-for '.radar-canvas-shell[data-assets-ready="true"]' \
  --expect-text 'Saved tasks' --label finance-workbench --read-only
node ../.agents/skills/verify-web/scripts/drive.mjs --port 3041 \
  --route '/office?dept=finance' --wait-for '.radar-canvas-shell[data-assets-ready="true"]' \
  --click 'Monthly allocation' --expect-text 'Available after usual bills' \
  --width 390 --dark --label finance-monthly-masked --read-only
node ../.agents/skills/verify-web/scripts/drive.mjs --port 3041 \
  --route '/office?dept=finance' --wait-for '.radar-canvas-shell[data-assets-ready="true"]' \
  --click 'Scenario comparison' --expect-text 'Starting cash' \
  --width 320 --label finance-scenarios-masked --read-only
```
