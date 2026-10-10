# Travel Markdown → HTML build

[Status: OK] Design-Lite · 2026-10-06

## 1. Problem and outcome

Trips currently require independent Markdown and HTML edits. The source holds
version history and evidence that cannot safely be discarded, while independently
rewritten HTML can omit a warning or retain an obsolete route. Keep Markdown as
the only editable trip content and generate the existing standalone HTML UI.

## Latest approved delivery decision

The initial HTML-only request is superseded: retain Markdown when it contains
necessary records and use deterministic Markdown-to-HTML generation. Edit trip
content in Markdown, then run `scripts/travel_build.py` and its `--check` mode.
Lodging belongs in the main itinerary; do not generate a separate hotel page.
Visible HTML icons use bundled Lucide SVG with visible text labels, never emoji.
Markdown markers remain semantic inputs; builds do not refresh factual evidence.

## 2. Scope and ownership

| Owner | Consumer | Change |
|---|---|---|
| Trip Markdown | New strict parser and renderer | Small opt-in `travel_render` schema and named current-stays table |
| Canonical travel HTML template/CSS/JS | Renderer and existing HTML finalizer | Reuse styles, timelines, cards and native controls |
| Renderer | `scripts/travel_build.py`, Makefile | Build, stale check, optional no-script preview |
| Travel skill/references | Future agents | AI plans/verifies/edits MD; scripts render/check HTML |

No network or AI runs in the builder. Existing legacy sources/pages remain
readable; unsupported source formats fail rather than being rewritten silently.
Only the main itinerary is generated; separate hotel HTML pages are retired.
The first migration uses the current trip. Other sources require explicit
normalization, particularly the incomplete recovered source.

## 3. Flow

```text
AI/user → Markdown [MODIFIED: sole editable content]
               ↓
         strict parser + source lint [NEW / EXISTING]
               ↓
         structured blocks in memory [NEW, no persisted second owner]
               ↓
         timeline/stay/checklist renderer [NEW]
               ↓
         canonical shell + HTML validation [EXISTING]
               ↓
         Main itinerary HTML, including lodging [GENERATED]
```

## 4. Input and output contract

`travel_render` YAML identifies schema 1, language and optional display title.
Require numbered sections 0–12 and 4.1, a five-column overview, consecutive
`Day N` headings with purpose quotes and five-column timeline tables, city
checklist tables, and one explicitly marked current-stays table with status.
Preserve other prose, tables, map/source links and review/history sections.

Current stay states are explicit (`已选`, `待确认`, `已预订`); `已选` never means
paid. Hotel date ranges must reconcile with stated nights. Unknown keys, malformed
tables, unsupported markup, missing sections, invalid links and ambiguous maps
raise source-line errors. Plain text/Markdown is escaped, not executed as HTML.

Overview, daily headings and dates agree. Source marker meaning is retained:
critical/constraint/pending notices stay visible, verified context stays quiet.
City cards link dates to real day anchors. Sources, versions, evidence dates and
review tasks remain in expandable supporting sections in the generated page.

Output is deterministic and carries source filename/hash and schema version.
`--check` rebuilds in memory and compares all requested outputs without writing;
changes in Markdown, renderer, template or assets make it stale. Validation occurs
before replacing output. Source files cannot be output/preview paths. A malformed
source must leave existing outputs intact.

## 5. AI and script responsibilities

| Trigger | Action |
|---|---|
| Add/remove stops, change priorities, replan transfers | AI verifies and edits source MD, then builds |
| Explicit known booking/status correction | User/AI edits the source field; build |
| Source unchanged, style/template update | Build without AI |
| Parser cannot understand a source | AI/user normalizes the reported line; no automatic guessing |
| Opening/pricing/closure evidence stale | AI checks sources; build is not factual verification |
| Shared UI changes or visual defects | Inspect actual desktop/mobile render; fix canonical renderer/assets |

## 6. Acceptance and risks

Synthetic tests cover content/link/history preservation, risk states, day/stay
agreement, malformed input, unsafe links, reproducibility, stale detection and
no-overwrite on failure. Run existing source lint and HTML/controls checks plus
one real local trip build. Browser availability is reported separately from
structural checks; no claim of visual equivalence without actual renders.

The intentional trade-off is a bounded Markdown grammar rather than arbitrary
HTML passthrough. This avoids new runtime dependencies and prevents silently
flattening unrecognized content. Do not broaden it by guessing: extend its
contract and tests when an actual source needs another supported construct.

## 7. Verification

36 renderer/linter tests and 6 canonical builder tests pass on synthetic inputs.
All local travel sources pass the consistency linter. The migrated main trip
build and stale check pass, with nine daily anchors and canonical embedded assets.
All three current trip sources are normalized and pass full build/check gates:
12, 9 and 8 activity days. A red-eye departure overview row covers the extra
calendar date without inventing another hotel or activity day. A prearrival
hotel night is retained. Daily supplementary tables and subheadings are kept.
The migration preserves all original link destinations and clock-time values;
recovery gaps remain explicit. Recoverable before-migration snapshots were
retained locally during conversion. Source dates are not refreshed by builds.

The controls regression check passes. All three retained main pages use bundled
Lucide SVG for visible markers; Markdown markers remain semantic inputs.
The earlier desktop screenshot was inspected for the first migrated page.
The current whole-library visual pass is blocked: both native Chrome and Safari
return `cgWindowNotFound`, and no browser automation surface is available.
Desktop/mobile visual acceptance for all three pages remains outstanding;
structural tests do not establish visual quality.
No fresh factual verification was performed by this implementation.

## 8. Open decisions

No decision blocks this implementation. Future new/legacy sources should be normalized explicitly, retaining recovery
gaps and verification dates.
