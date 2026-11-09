# Office Content Lab — Design-Lite

[Status: OK] V1 implemented; local acceptance and limitations in the delivery plan · 2026-11-09

## 1. Outcome

Add a Content Lab to the default 3D `/office`: a place to commission research,
produce Xiaohongshu content, review publishable files and learn from recorded
performance. Its primary product is a publishable content package. Traffic and
follower growth are experiment outcomes, never promised results.

The owner supplies direction and judgment; the assistant researches topics,
checks claims, prepares content and interprets evidence. Personal branding emerges
from repeated useful output. The lab must support this work rather than become
another decorative building or a career-portfolio dashboard.

This is the technical proposal. The sole implementation checklist is
[the delivery plan](../plans/office-content-lab.md). Repository documentation is
English; post language and identity resolve from private account settings.

## 2. Scope and planning baseline

| Surface | Proposed change | Existing owner to preserve |
| --- | --- | --- |
| Default Office world | Third building, `content`, displayed as Content Lab | `office-departments.ts`, `radar-scene.tsx` |
| Four workstations | Research, Production, Review, Results | Shared Office interaction and work-panel pattern |
| Commissioning work | Prepare a stage-specific brief; explicitly send through existing execution or hand off to the client | `DirectTask`, execution API and saved work history |
| Content files | Read existing posts and optional lab records | Private `data/posts/`; existing bounded post adapter |
| Output review | Images, copy and explicit readiness evidence in-world | `PostsLibrary`; `/posts` remains available |
| Performance review | Read manually recorded platform evidence | Optional private lab record, linked to one post |

Before this change, `Department` was `lab | finance`. The development Lab contains the
attention radar; Finance has physical desk targets. Department changes currently
select panels beside/below the canvas. `/posts` already reads final images and
copy through local endpoints; its folder date is not a publication date.

The [immersive Office proposal](office-immersive-world.md) is a separately owned track.
It owns fullscreen, the persistent Canvas, world-mounted panels and input priority.
Content Lab does not wait for it and does not build another shell: v1 uses the
current department-panel pattern (Finance's panel beside/below the same Canvas).
When the immersive shell lands, Content Lab panels move into its work panel in
the same way as Lab and Finance. Classic `?scene=town` remains frozen.

Out of scope: automated publishing or engagement, scraping private platform data,
multi-account operations, paid promotion, revenue projections, new character rigs,
a scene editor, background scheduling, and a second task runner.

## 3. Spatial design and user journey

Use the current Kenney Modular Space Kit / Furniture Kit palette, shared lighting,
scale and navigation from [the scene standard](3d-scene-standard.md). Reuse asset
aliases and `KenneyAsset`. Post brand colours do not become a new 3D scene palette.

Place the new open building beside the existing town, connected by its paths.
Determine exact bounds from a visible baseline before fixing coordinates. Adding
it requires updating the combined town extent, overview fit, walk bounds,
collision obstacles, signs and landscape exclusions together; `town` currently
calculates its extent from two explicit buildings. Preserve existing building
coordinates, radar slots and Finance deep links.

| Station | Visible summary before opening | Work inside the world panel |
| --- | --- | --- |
| Research | Current question, candidate count, research availability | Inspect demand evidence and competitor examples; prepare a research task |
| Production | Selected topic, requested deliverables, linked run state | Prepare a verified brief; inspect sources, copy and image-production handoff |
| Review | Previewable packages and outstanding checks | Browse carousel and copy; inspect factual/visual checks; request changes |
| Results | Recorded publication and measurement coverage | Compare recorded views, saves, shares and follows at comparable ages |

Use a source board, editing desk, preview wall and results board to distinguish
the stations with existing props. Avoid four identical desks and walls of tiny
text. Use compact DOM summaries and one readable detail panel, rather than whole
tables rendered as 3D text. Counts are derived from evidence, with unavailable and
unknown shown explicitly. No invented workers or looping production animations.

Journey: walk to Content Lab or choose its accessible entry → open Research →
prepare/submit a brief → inspect actual progress or client handoff → open output
in Review → manually publish → record evidence → review Results → prepare the
next experiment. Opening a station never starts a task or moves the camera.

Proposed deep links: `/office?dept=content&station=research|production|review|results`.
Parse station by department using a discriminated selection type; do not widen
`FinanceStation` with unrelated content values. Unknown values fall back to that
department's default station; existing Finance and legacy links retain behavior.

## 4. Architecture and execution capability

```text
OfficeWorkspace [MODIFIED: content selection; same execution controller]
  -> RadarScene [MODIFIED: Content Lab + targets + world extents]
  -> department work panel [EXISTING pattern; moves into the immersive shell when it lands]
      -> ContentLabPanel [NEW: four station views]
          -> existing post endpoints / PostsLibrary [REUSED]
          -> content-lab projection [NEW: bounded private read adapter]
          -> existing DirectTask + work history [REUSED]
          -> explicit client handoff [NEW: copy brief / inspect returned files]
```

Reuse one execution owner and one source of post files. Lab stations are stages
of work, not separate agents or independent execution queues.

**Capability gap:** `office-execution-runtime.ts` currently starts a workspace-write
Codex task with approval policy `never` and developer instructions stating network
access is disabled. The roster can select `social-post`; that does not establish
browser research or image-generation capability. Work history's artifact reader
is text-only; it cannot replace the existing post image endpoint.

Before enabling actions, exercise the actual Office runtime for web research and
image generation. Discover relevant official connectors/tools before proposing
an integration. Any runtime permission change requires its own concrete contract
and review; this plan does not silently enable network access or bypass policy.

| Capability | First-release behavior |
| --- | --- |
| Read existing posts and saved task evidence | Use current local guarded APIs |
| Prepare topic, production or review brief | Available locally; sending is a distinct user action |
| Local file work supported by runtime | Submit through existing solo execution, respecting configuration and busy state |
| Research/image generation unavailable in Office | Label client handoff; copy a complete brief and expected destination |
| Client completes work | Explicit refresh reads actual files; do not infer completion from a copied brief |

The content workflow remains owned by `social-post`. Its present topic gate is
specific to the configured local-reader series. Research experiments outside that
scope can be recorded, but must not silently bypass the gate. Choose a compatible
pilot; broader editorial support needs a separately reviewed skill change.
Capability limitations must be visible before dispatch.

This change does make one reviewed edit to `social-post`: its gate questions and
criteria stay the same, but where results are recorded moves. Step 1 writes gate results
and step 7 writes seven-day measurements into `lab.yaml` (§5) instead of `post.md`
prose, so one structured owner holds the numbers the skill later compares.

## 5. Data contract and lifecycle

Existing post layout and GET APIs stay unchanged. Do not parse arbitrary Markdown
prose into authoritative production or publication states. Proposed optional
`data/posts/<post-id>/lab.yaml` holds the lab's structured record; a topic may have
`post.md` and this record before it has images. Legacy folders without the record
remain readable with unknown workflow/publication state.

Proposed version 1 record, with synthetic values:

```yaml
schema_version: 1
stage: research
experiment:
  hypothesis: "An actionable explanation earns more saves than a mechanism-only introduction."
  changed_variable: "Opening question"
  gate: []            # social-post step 1: [{question: 1..5, result: pass|fail|unknown, note}]
  demand_evidence: []
task_ids: []
readiness:
  factual: unknown
  visual: unknown
  owner_review: pending
publication: null
measurements: []
```

`stage` is one of `research`, `production`, `review`, `ready`, `published`,
`archived`; it is editorial state, separate from a run's execution/review state.
Readiness checks use `unknown | passed | failed`; owner review uses
`pending | accepted | changes_requested`. `ready` requires factual and visual
passes, owner acceptance, and existing readable images and copy. This readiness
rule must be enforced by the schema/projection validator, not only a button.
Existing review acceptance of a task alone does not make a post ready.

Publication, when recorded, includes `platform`, `published_at` and `url`.
`published` requires that explicit record; folder date and file existence never
qualify. Each measurement includes `observed_at`, a source reference and nullable
non-negative integer counts for views, likes, saves, comments, shares and follows
attributed to that post. Account-level follows cannot substitute for attributed
follows. Record production minutes/cost only when observed, with currency for cost.
Zero means observed zero; absent metrics stay null.

Demand/competitor evidence records URL or private capture reference, observation
time, observed wording/counts and qualifications. Do not invent search volume.
Compare equivalent measurement windows; display sample size and paid/organic
coverage. Rates require a known nonzero denominator. No universal scoring weights
or virality thresholds. Seven-day review keeps the skill's comparison rule (own
median, check after three posts) but records into `measurements`; insufficient
data produces an explicit incomplete comparison.

**Single owner.** `lab.yaml` is the only structured owner of gate results,
readiness, publication and measurements. `post.md` keeps copy, sources and prose
notes; nothing reads numbers back out of it. Legacy gate tables already in
`post.md` stay as prose (no backfill), so those posts show gate results as unknown.

**Validator owner.** One Pydantic model under `scripts/lib/` owns the v1 shape,
following the finance-workbench pattern: an export script writes
`web/lib/content-lab.schema.json` and `content-lab.gen.ts`, with `--check` for
drift. A proposed `make posts-check` validates every `lab.yaml` against that model
plus the cross-file rules (readiness prerequisites, readable images/copy for
`ready`, publication record for `published`) and names the failing post and field.
The skill runs it after every record write; the API projection applies the same
rules, so the browser never becomes the first place a malformed record is noticed.

The owner/client owns the private record. The browser reads the collection and exposes only the narrow metadata commands below.
Add `GET /api/office/content-lab` returning
`{schema_version:1, items:[{post_id,record,revision}], partial:boolean}`. `record` is either
the validated v1 shape above or null for legacy posts. Missing optional records
are null; malformed records are excluded with `partial:true`; an absent private
root returns `503 {error:{code:"content_lab_unavailable"}}`. Valid empty data is
`200` with `items:[]`. Reuse the post ID policy, bounded regular-file reads,
realpath confinement, loopback/same-origin guards and private/no-store responses.
Do not expose arbitrary filesystem paths or render source HTML.

This requires the validator/model, its export and check command, synthetic
fixtures, optional-record documentation, the `social-post` record-location edit
and an additive API; no backfill, existing source rewrite or existing API version
change. General source editing/import remains deferred; narrow review/results writes use the contract below.

## 6. Ownership, compatibility and failure review

| Owner | Consumer | Migration / tests | Assessment |
| --- | --- | --- | --- |
| Scene standard + department geometry | New building, camera, walking, targets | Existing two-department behavior and new bounds/collision journeys | Warning: proposed geometry not verified |
| Immersive Office shell | Content panels, portals, focus | v1 uses the existing department-panel pattern; migrate with Lab/Finance when the shell lands; no second Canvas/controller | OK: not a v1 dependency |
| Private posts README + social-post skill | Files, preview, gate results and seven-day review | Steps 1 and 7 record into `lab.yaml`; old folders, prose gate tables and `/posts` still work | Warning: reviewed skill edit required |
| New lab v1 Pydantic model + `make posts-check` | Skill writes, projection and results panel | Invalid/legacy/null cases; readiness, publication and timestamp rules; schema export drift check | Warning: not implemented |
| Existing execution/work contracts | Prepared briefs, real progress, task links | Busy, retry, disabled, interrupted and handoff coverage | Warning: capability gate pending |
| Private `data/posts/` | Local API only | Synthetic tests; confinement and no public export | OK: private boundary retained |

Missing data shows unavailable; missing metrics show unknown. A failed run retains
partial files but does not become ready. A handoff stays a handoff until output is
observed. Stale requests are aborted/ignored. Refresh cannot reset camera or drafts.
When execution is busy, retain the prepared brief; do not create another runner.
WebGL loss retains accessible station controls and content access.

Account identity, competitor captures, analytics, budgets and real content remain
private. Public docs and tests contain only abstract contracts and synthetic data.
Daily/weekly, wealth, observation schemas and Python report boundaries are outside
this change. Result recording previously had two candidate owners (`social-post`
prose in `post.md` and this record); §5 resolves it to `lab.yaml` alone. Runtime
capability remains an explicit implementation gate.

## 7. Trade-offs and open decisions

Choose a separate Content Lab building to make production visibly distinct from
development and Finance. The cost is additional layout/camera/collision work;
verify town readability before settling its footprint. A station inside the
development Lab would be smaller but would mix attention monitoring and output.

Reuse `/posts` components and endpoints inside the world; keep `/posts` as an
accessible alternative. Building a new gallery would create competing readers.
Begin with manual evidence records and explicit client handoff where necessary,
rather than promising integrations the current runtime cannot execute.

Nonblocking review decisions, with defaults:

1. Name: use **Content Lab** in UI and `content` in links; IP-building remains its purpose.
2. Format: start with one XHS carousel workflow; defer video and extra platforms.
3. Execution: accept an honest client handoff in v1; richer in-Office tools require capability proof.
4. Editorial breadth: use the current account's compatible series for the pilot;
   broaden only after a deliberate skill/identity decision.

## 8. Acceptance boundary

The feature is complete when a user can reach the building in the default world,
commission or hand off one real content task, inspect its actual output, and
view explicitly recorded performance without losing world state. Merely adding
the room is an intermediate milestone. Acceptance tasks and evidence requirements
are owned by [the delivery plan](../plans/office-content-lab.md).


## 9. Implementation and contract review

[Status: OK] Local V1 matches the owner/consumer boundaries above. Python owns
record validation and cross-file checks; generated schema/types consume that
model, the local API uses the same Python projection, and the social-post skill
writes gate/results into the optional record. Legacy folders and existing post
APIs retain their behavior; no backfill or schema removal was performed.

The implementation reuses the shared fullscreen hook and portal slots introduced
concurrently in OfficeWorkspace, keeping one Canvas and execution controller.
Content briefs survive station changes. Existing Lab/Finance deep links remain
compatible, and Content Lab has department-specific station fallbacks.

The actual runtime probe found official web search exposed and successful despite
its network-disabled developer instruction; image tooling was exposed but not
executed. This is narrower evidence than general network or production capability.
V1 deliberately keeps prepared local tasks scoped to existing local evidence and
provides a complete client brief for online research/image production. No runtime
permission or policy was changed.

Contract classes reviewed: optional schema/lifecycle, Python→TypeScript export,
private-file projection, scene/navigation consumers and skill/document ownership.
Daily/weekly and wealth contracts are unchanged. Public tests/docs contain synthetic
records; actual posts, screenshots and analytics remain private. No Critical
contract blocker remains for local V1; image production/publication automation
and browser record editing remain outside its acceptance. Full command outcomes,
rerun coverage and evidence paths are in the delivery plan.


## UX revision — 2026-11-09

[Status: OK] Owner authorized changes after a hands-on Chrome review.

The Content workspace defaults to a wide work panel. Preparing a task opens and
focuses the existing composer; history is collapsed below it. Station switches
and fullscreen transitions retain the existing Canvas, task controller and draft.
On narrow screens the scene is hidden initially and can be shown explicitly.
Review starts with cover cards and one summary status. Full images open in a
native modal dialog with fit-to-screen, paging, Escape and focus restoration.
Shared Button, Input, Textarea, Select and existing PostsLibrary remain owners.

### Narrow write contract

`POST /api/office/content-lab` accepts the generated discriminated command union:

- `review_content`: post_id, expected_revision, decision accepted/changes_requested.
- `record_results`: post_id, expected_revision, validated publication and one measurement.

Python `LabWriteCommand` is the sole validation owner; its schema and TypeScript
union are exported alongside the read projection. Revision is SHA-256 of exact
lab.yaml bytes, or null when absent. The additive read field needs no migration.
Writes require an existing confined post with readable post.md, same-origin
loopback JSON, at most 64 KiB, and live mode. Demo rejects writes. A private
root lock serializes API writers; stale revisions return 409, exact retries are
idempotent. Candidate records pass the same cross-file validator, then replace
lab.yaml atomically from a same-directory temporary file. Other fields survive.
External editors should refresh before editing; they do not participate in the lock.

Approval changes owner_review only; factual/visual checks remain independently
owned. Ready still requires all checks and readable final assets. A changes
request saves the decision and prepares a task with notes; sending is explicit.
Recording results means the user reports an existing publication, never that the
app publishes it. Counts stay null when unavailable; an observed zero stays zero.
The form retains input on failure/409. Refresh loads current revisions, with an
explicit Load latest action before replacing a conflicting form draft.

| Contract | Owner | Consumers | Migration / verification | Result |
| --- | --- | --- | --- | --- |
| Typed writes and null counts | Python Pydantic models | CLI, POST, forms | Generated schemas; Python/API/browser tests; no backfill | OK |
| Version and atomic write | Python adapter | Live browser saves | Stale/conflicting and exact-retry tests | OK |
| Local private boundary | API guards + bounded file adapter | Existing private posts only | Origin/demo/body-limit tests; no public data export | OK |
| Task dispatch | Existing DirectTask | Prepared research/revision briefs | Focus/draft/world tests; Send remains explicit | OK |


## Autonomy revision — 2026-11-09

[Status: OK] Owner authorized (“做”) after the autonomy research recorded in this session.

**Outcome.** The owner touches the lab twice: brainstorming with an idea agent and
reviewing finished packages. Everything between an approved idea and the review
inbox runs without a human. Publishing stays manual; XHS's 2026-03-10 “AI托管”
notice bans accounts whose posting or interaction is AI-operated, and its
2026-04-27 rules penalise template-batch “AI低质” output.

```text
owner ⇄ content-ideas skill ──► idea folder (stage idea)
          Approve idea (Ideas station or skill) ──► pipeline.status queued
content_pipeline.py (detached; one at a time) ──► claude -p + social-post AUTONOMOUS
  └─ deterministic checks ──► stage review + push │ status failed + reason + push
owner Review: Approve │ Request changes + note (auto re-queue) │ Kill (archive)
```

This supersedes §4's “no second task runner” for content only: the Office Codex
runtime keeps network disabled, so the content pipeline runs a separate headless
`claude -p` on the owner's Mac with an explicit tool allowlist and
`--permission-prompts none` (anything outside the allowlist is denied, never asked).
It never publishes, commits, or touches files outside `data/posts/` and its log folder.

**Record (additive, schema_version stays 1).** Stage gains `idea` before
`research`. Optional `pipeline` block: `status` (`idle | queued | running | failed`),
`requested_at`, `feedback` (owner change notes, append-only), `runs` (start, finish,
outcome, bounded reason, log name). Legacy records default to `idle`.

**Commands.** `approve_idea` (idea → research, queued), `archive` (any stage →
archived, idle), `requeue` (failed → queued), and `review_content` gains an optional
`note`; a change request with a note appends feedback, sets stage `production` and
queues. All writes are rejected with `409 pipeline_running` while a run owns the post.
A write that queues work starts the runner detached when `office.content_pipeline.enabled`.

**Gate the agent cannot talk past.** After the agent exits, the runner — not the
agent — decides `review`: 6–9 numbered 3:4 images (PNG/JPEG header dimensions),
non-empty `publish.txt`, `verification.md`, `prompts.md`, five gate results with
question 1 `pass`, at least one demand observation, and factual/visual `passed`.
Any miss sets `failed` with the named checks. Critic work inside the agent uses
Claude to judge Codex-generated images (different model families) and caps
regeneration at two rounds per page.

**Out of scope here (next slice):** screenshot-to-metrics ingestion, the weekly
learner that feeds results back to the idea agent, critic calibration on past
owner rejections, cross-post sameness check, and launchd scheduling.
