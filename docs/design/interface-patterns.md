# Interface reuse catalog

[Status: OK] Active implementation reference · Updated: 2026-10-27

Use [the shared guide](../design-system.md) for design principles. This catalog
answers what to reuse, how to compose a page, and which known failures to replay.
Exact values remain with their implementation owner.

## Implementation index

Paths are relative to the repository root. Open the local dashboard's
`/design-system` route for deterministic examples. It reads no private data.

| Need | Reuse | Notes |
|---|---|---|
| Page sections | [SectionCard](../../web/components/shared/section-card.tsx) | Title, description, optional action; avoid nesting panels merely to separate paragraphs |
| Numeric summaries | [Stat](../../web/components/shared/stat.tsx) | Keep unit, scope and missing-value explanation visible; direction needs a text label |
| Loading, empty, error, partial and complete states | [DataState](../../web/components/shared/data-state.tsx) | Caller supplies truthful title, scope and real recovery; used by reference and Skill regressions |
| Semantic status | [StatusBadge](../../web/components/status-badge.tsx) | Label and icon accompany reserved status colours |
| Buttons | [Button](../../web/components/ui/button.tsx) | Variants default/outline/ghost/destructive, sizes default/sm; colour is `action`, never a status colour. Pattern from ai-stock-analysis `ui/button.tsx` (unpinned), no cva |
| Private amounts | [privacy.tsx](../../web/components/shared/privacy.tsx) | `PrivacyProvider` + `PrivacyToggle` per page; `Money` (MYR) and `Private` (other text) mask by default with a fixed-width mask and an sr-only label. Screen privacy only: values remain in the page payload. Editing is disabled while hidden because inputs show raw values |
| Text fields | [Input / Textarea](../../web/components/ui/input.tsx) | Same surface as Select (card fill, 8px radius, 40px / 44px coarse); pass width/margins via `className`, never colour or border. Links that must look like buttons use `buttonClass()` from [button.tsx](../../web/components/ui/button.tsx) |
| Choice of one value | [Select](../../web/components/shared/select.tsx) | String values, including long IDs; labelled trigger, disabled options, Radix keyboard/focus handling |
| Appearance toggles | [AppearanceMenu](../../web/components/shared/appearance-menu.tsx) | Reuse through dashboard navigation; consecutive changes stay in the menu |
| Sticky navigation | [DashboardNav](../../web/components/dashboard-nav.tsx) | Scroll-dependent material, theme and reduced-transparency controls |
| Role tokens and controls | [design-controls.css](../../web/app/design-controls.css), [globals.css](../../web/app/globals.css) | Resolve styles through the real layout import order; brand, status and series have different meanings |
| Standalone travel HTML | [Travel reference](../../.agents/skills/travel-plan/references/share-html.md) | Use its renderer and canonical assets rather than copying a previous trip |

SectionCard and Stat were copied from `repos/ai-stock-analysis/web/components/shared/`.
Their upstream revisions are currently **unpinned**. Local intentional differences
include the icon props, Personal-OS status colours and more rounded surfaces.
A future synchronization should record the reviewed upstream SHA; do not invent
one from the current checkout or treat the copies as automatically synchronized.

## Three composition recipes

These are flexible starting compositions, not three new generic components.
Reuse the actual presentation components and adapt domain content. Existing
pages below demonstrate composition; they are not blanket visual approval.

### Overview: understand current state and act

Order: context and freshness → primary summary → consequential blockers →
supporting metrics → detailed sections. Keep the summary's scope explicit.

- Start with [the finance page](../../web/app/page.tsx), SectionCard and Stat.
- Give the important summary more space than supporting numbers. Use section
  spacing before adding another card. Do not make every metric a primary action.
- On phones, place the context and next action before secondary statistics.
- Loading has an explicit label; absent amounts remain unknown. Partial data
  retains its scope warning beside the summary. An error offers a real recovery
  action where available; it must not become a successful zero balance.

### Comparison: narrow choices and understand differences

Order: question and scope → labelled filters → result count → aligned comparison
→ selected result and next action. Use a table for cross-row numerical comparison.

- Reuse Select, StatusBadge and the table composition in
  [skill regressions](../../web/app/skill-regressions/page.tsx).
- Keep units in headings or values, align numeric columns and identify the
  selection in text. Preserve long identifiers as strings.
- On phones, a necessary wide table scrolls in its own labelled region. Keep
  filters readable without squeezing every column into the viewport.
- Distinguish no records, no matching records, loading and request failure.
  Provide reset filters for no matches. Disabled choices explain prerequisites.
  Selection must remain valid when filtering, or be explicitly cleared.

### Detail: assess a conclusion and inspect its evidence

Order: subject and status → conclusion or next action → evidence → visible
consequential constraints → optional supporting detail. Blocking constraints
belong beside the decision as well as in supporting sections when necessary.

- Reuse SectionCard, StatusBadge and native disclosure for optional explanation.
  [Travel composition](../../.agents/skills/travel-plan/references/share-html.md)
  demonstrates summary, timeline, constraints and supporting detail.
- Give prose a readable measure and line height. Avoid putting each paragraph
  into a separate card. Collapse secondary explanation, not required warnings.
- On phones, keep the decision and relevant constraint ahead of long evidence.
- Distinguish pending evidence from a negative result. Missing sections explain
  what is unavailable. Error recovery preserves information already available.

## Recurring failures and replay checks

These are documented failure scenarios to prevent, not assertions that the
current implementation is broken. Add an entry only for a recurring need or a
consequential defect. Improve the owning implementation before adding prose.

| Scenario | Implementation to reuse | Replay / expected result |
|---|---|---|
| Dense text shows through scrolled navigation | DashboardNav + design-controls.css | Scroll actual dense content under the header; inspect computed production `backdrop-filter` in both themes; solid mode remains readable |
| Portalled choices clip or use the wrong font | Select + design-controls.css | Open near viewport edges; long labels wrap, options scroll locally, menu is above navigation |
| Choice loses keyboard focus or commits twice | Select | Open by keyboard, arrow/typeahead, commit once; reopen and Escape restores trigger focus; disabled option cannot commit |
| Long ID loses precision or disappears | Select string API | Select `900719925474099312345678901234567890`; displayed selection preserves every digit |
| Missing amount looks like confirmed zero | Explicit display-state contract | Compare missing, loading, error and confirmed zero; each has different text; missing data cannot appear complete |
| Enlarged text widens the page | design-controls.css inherited and heading wrapping | At narrow width, enlarge text beyond 200%; titles, prose and action labels wrap and page width stays within a 1px rounding tolerance |
| Phone page overflows | Catalog recipes and local table regions | Inspect 320px and 390px plus enlarged text; page fits, necessary table scroll is local, last section remains reachable |
| Calm styling hides a consequential warning | StatusBadge and source-specific callout | Constraint and recovery action remain visible without expanding details; meaning survives monochrome |
| Copied assets drift | Local owner and recorded provenance | Compare the changed behavior with the source; replay its scenario in each affected consumer |

## Review and evidence

The `/design-system` page exposes complete, loading, empty, error and partial
states with deterministic controls. It also includes long Chinese copy, a long
ID, large/negative/missing numbers, multiple statuses and disabled choices.
Use the actual global Appearance menu for light/dark and solid/glass checks.
Do not add a second appearance implementation just for the reference.

For a UI change, record the affected scenario, viewport/zoom, appearance/material,
interaction result, and screenshot location or precise unverified gap in the PR.
Check 320px, 390px and desktop when layout changes; check keyboard behavior when
controls change. For enlarged text use an explicit zoom setting. Exercise the
production build when validating material effects. Automation can check overflow,
selection and focus; screenshots still require visual review.

A reference becomes an accepted visual baseline only after user review of the
relevant states, with a screenshot and reviewed revision recorded. Automated
checks alone cannot establish comfort or certify accessibility.

## Reuse trial — Skill regressions

**Page pattern:** comparison, from this catalog.

**Reused assets:** SectionCard, Stat, StatusBadge, DataState and the existing
navigation/appearance tokens. DataState was extracted only when the reference
and the actual report page needed the same state presentation. Its caller owns
state triggers and business meanings; it never derives zero, success or retry.

**New decisions:** the existing load failure gets an explicit recovery link;
verbose local diagnostics move into a disclosure. An empty configuration list
gets a truthful empty state. The comparison's local scroll region is labelled
and keyboard-focusable. Existing report generation and outcome semantics stay
with their original owner.

Stat owns unbroken-value wrapping, so its consumers no longer need their own
numeric overflow selector. The reference stress case exercises that shared
behavior. This trial demonstrates concrete reuse; time saved has not been
measured and must not be reported as a proven efficiency gain.

Regression checks for this trial: run `node --test tests/interface-reuse.cjs`
in `web/`. Browser results, measured overflow checks and exact replay steps are
recorded in [the implementation verification](interface-reuse-implementation.md#verification-record--2026-10-27).
