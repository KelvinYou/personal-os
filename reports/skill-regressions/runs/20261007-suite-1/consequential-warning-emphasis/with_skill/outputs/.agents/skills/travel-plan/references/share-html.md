# Standalone travel HTML

A companion page rewrites the plan for the traveller; it is not a raw Markdown
export. Save it as `data/travel/<slug>-itinerary.html`. Hotel lists and other travel
HTML derivatives use the same UI assets and can have their own page titles.

## Content owner

Read the latest trip Markdown before composing. Reconcile hotels, dates, nights,
return transport, and booking status against it. Never reuse a stale HTML body as
current evidence. A restyle does not authorize changing the itinerary.

| Drop | Keep | Add |
|---|---|---|
| Versions, changelog, research source appendix | Verified facts, constraints, maps, contact numbers | A one-sentence purpose per day |
| Internal audit checklist and literal question-mark markers | The uncertainty itself | Plain instructions for confirming pending details |
| Superseded arrangements | Day-specific fallbacks | One-line reasons for unusual routing |

Distinguish selected hotels from paid bookings and target time windows from
confirmed services. Do not invent a quotation, room count, transport time, or
booking confirmation to fill a visual component.

## Shared design guidance and travel composition

Read [the shared interface design guide](../../../../docs/design-system.md)
for hierarchy, trustworthy information, material, accessibility and reuse.
It is the owner of those cross-page principles; this reference owns their travel
application, content semantics and offline HTML build.

The travel default uses the same neutral palette, typography scale, floating
navigation, appearance menu and card treatment as the local web dashboard,
implemented by the bundled assets. Adapt it when the user requests another direction. Start
with the traveller's immediate decisions: trip identity, dates, next action and
important constraints. A date index leads into timelines; lodging can use comparison
cards, transfers connected stages, and numerical costs tables. Use a compact
introduction for a hotel-only page. Preserve uncertainty and fallbacks while
removing repeated or decorative information.

For complete itineraries, read [checklists.md](checklists.md) and include separate city-by-city must-visit (`#places`) and must-eat (`#food`) sections, with top-navigation links, priority labels, actual dates/meals and maps. Keep all accepted places accounted for in daily routes, conditions or explicit unscheduled status.

Reuse `assets/share.css`, `assets/share.js` and `templates/share.html`; exact
styles and responsive behaviour stay there rather than becoming global rules.
The HTML is a CSS interpretation of glass, not Apple's native material. When
changing the shared visual treatment, update the canonical assets and reference
together, then re-inline those assets into the affected outputs. Avoid per-trip
CSS overrides: they drift from the next generated page.

## Semantic hierarchy and action-first composition

Calm styling must not flatten consequential information into ordinary notes.
Translate source markers by meaning, retaining uncertainty and severity:

| Meaning | Treatment | Required text |
|---|---|---|
| High risk / source 🚨 | Red `notice alert`, visible without expansion | Specific consequence and next action |
| Hard constraint / source ⚠️ | Amber `notice warning` | Constraint and what to confirm |
| Pending / source ❓ | Amber pending status; elevate to warning when it blocks travel | What is pending and how to resolve it |
| Verified fact / source ✅ | Quiet context, or `notice good` for a useful reassurance | Precisely what is verified |
| Selected hotel | Green `status selected` | Selected; never imply paid or booked without evidence |
| Ordinary explanation | Neutral `note` or blue `notice info` | Brief context, not an alarm |

Use `notice-icon`, `notice-title`, and `notice-copy` to make callouts readable.
Icons are supplementary (`aria-hidden="true"`); meaningful labels and actions
must remain in text. Colour alone is insufficient. Keep long copy in normal ink.

When the source has pre-departure blockers, put a prominent amber `priority`
section immediately after the trip introduction, with a concise action heading
and an `action-grid` of short `action-card` items. Show red urgent labels only on
items whose source supports that severity. Prefer human instructions and one
clear action per item over raw field/value lists. Do not add invented deadlines.
The canonical renderer promotes marked timeline notes from muted metadata to
expanded callouts. Keep urgent row and overview labels red; amber is for
constraints or pending facts. The hero action links to the existing priority
section, which keeps its amber outline and source-supported red inner warnings.
Repeat a compact risk label on relevant overview days and the full warning in
that day's timeline. Do not collapse warnings into optional fallback details.

Review every surface for omissions: booking/payment uncertainty, station versus
hotel arrival, early check-in, road closures, admission reservation, airport
buffers, outdated prices, and emergency contacts. This is a source review, not a
requirement to invent risks. Make selected/pending status, decision constraints,
and budget uncertainty visually distinguishable from routine advice.

Use `journey` for complicated transfers, showing each actual stage and a short
qualifier. Use `practical-card` for city place and food checklists and booking actions;
reserve tables for numerical comparison. Give emergency numbers direct `tel:`
links where the source supports them. Chronological rows use a subtle timeline
rail so the eye can follow time without colouring every item.

Localize navigation and dynamic control labels to the page language. Hotel-only
pages use `compact-hero`. Do not decorate every fact: priority actions, daily
warnings, and quiet explanatory content should have three distinct visual levels.

When revising an existing trip, update the Markdown owner and companion HTML together, including overview, day timelines, both checklists, conditions and freshness notes. Scope claims of verification to facts actually rechecked.

During refinement, open the actual generated pages, inspect desktop and phone
layouts in light and dark appearances, and iterate on the render. Check whether
a first-time reader can identify the journey, the next action, and the day's
main constraint without reading the entire page. Do not claim an objectively
"best" UI; report what was inspected and any remaining verification gaps.

## Build

Use the deterministic Markdown renderer described in [render-source.md](render-source.md).

```bash
make travel-build TRAVEL_DOC=data/travel/<slug>.md
make travel-check TRAVEL_DOC=data/travel/<slug>.md
```

The renderer fills `templates/share.html`, then uses `scripts/build_share.py`
only as the canonical asset/control finalizer. Do not fill itinerary content
manually or run the low-level finalizer as a substitute for source rendering.
Keep lodging cards inside the main page's `#stays`. Separate hotel pages have
been retired and must not be recreated or linked.

Keep the light background and glass navigation defaults, native appearance
checkboxes, offline embedded assets and print controls from the shared shell.
A temporary script-free preview can be generated with the CLI's
`--nojs-preview /private/tmp/travel-preview.html`; it is not another source.

Build/check validate balanced structure, canonical assets, classes, local
anchors, checklist navigation, placeholders and day counts. They do not verify
travel facts, per-city completeness, browser rendering or colour contrast.
Inspect desktop/mobile renders when changing layout or claiming visual parity.

## Component vocabulary

| Class / element | Purpose |
|---|---|
| `.topbar` / `.topbar-inner` / `.nav` / `.brand` | Floating glass navigation |
| `.tools` / `.icon-button.js-only` | Theme, reduced-glass, and print controls |
| `.skip-link` | Keyboard route straight to main content |
| `.hero` / `.eyebrow` / `.hero-sub` / `.dates` | Trip identity and dates |
| `.facts` / `.route` / `.stop` | Compact facts and destination summaries |
| `.overview` | Clickable day overview cards linking to real day IDs |
| `.grid` / `.hotel` / `.hotel-meta` / `.hotel-links` | Responsive lodging cards |
| `.status.selected` / `.status.pending` / `.status.urgent` | Selected, pending, and urgent labels |
| `.priority` / `.action-grid` / `.action-card` | Prominent pre-departure actions |
| `.notice.warning` / `.notice.alert` / `.notice.info` / `.notice.good` | Amber constraint, red risk, blue context, green verified fact |
| `.notice-icon` / `.notice-title` / `.notice-copy` | Supplementary icon, visible label, readable instruction |
| `.journey` | Ordered transfer stages with short qualifiers |
| `.practical-card` / `.contact-grid` / `.contact-link` | Human-readable food/booking cards and direct emergency calls |
| `.risk-label` / `.hero-action` / `.compact-hero` | Overview warning, next-action link, compact derivative introduction |
| `.section-head` / `.sub` / `.panel` | Section heading, supporting line, content surface |
| `.day-nav` | Native date anchor navigation |
| `.day` / `.dayhead` / `.daynum` / `.daydate` / `.daytitle` / `.daylede` | One chronological day |
| `.sched` > `li.key` > `.time` + `.what` with `.meta` | Timeline and important rows |
| `.map` | One map provider link immediately after a place name |
| `.tag` / `.tag.free` / `.tag.warn` | Costs and readable status labels |
| `.alert` / `.note` / `.good` with `.t` | Critical constraints, context/fallbacks, upsides |
| `.scroll` around `table`, optionally `.tot` | Contained table scrolling on phones |
| `.kv` (`dl`, `dt`, `dd`) | Practical information pairs |
| `.plain` / `.tight` / `.n` | Existing list and numeric-cell compatibility |
| `.glass` / `.button` | Optional short glass summary or native action link |
| `.footer` / `.noprint` | Freshness note / screen-only controls |

The existing class vocabulary remains supported, so historical HTML does not
require migration. Newly generated HTML must inline the current assets.

## Mobile reading standard

Mobile is a deliberate composition, not a shrunken desktop grid. Use the
canonical screen-only breakpoint so printing remains a separate layout.

- Match the web dashboard's compact top navigation and native appearance menu on
  desktop and phones. Keep section anchors visible, highlight the current section,
  and allow horizontal scrolling inside navigation when labels need it. Respect
  sticky-header offsets so destinations remain readable.
- The first phone viewport should identify the trip, dates and next action.
  Avoid repeated destinations or large decorative summaries that delay useful content.
- Let long day titles wrap, stack timelines on narrow screens and keep text
  readable. Practical contacts use a wrapping list; numeric comparisons may use
  a table with its own horizontal scroll region and visible hint.
- Keep essential warnings expanded and visibly distinct. Optional explanations
  may collapse. Use 44px touch targets for standalone controls and map actions;
  inline prose links retain readable spacing. This is a design preference, not
  a claim about WCAG AA's minimum.
- Verify narrow phones, a long day, dark appearance, reduced glass, keyboard focus
  and the document's final section. The full page should not scroll horizontally.

Reference checks: [WCAG target size](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html)
and [WCAG reflow](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html).
These are engineering acceptance targets, not a blanket accessibility certification.

## Visual acceptance

Use the [shared acceptance check](../../../../docs/design-system.md#short-acceptance-check)
for the overall interface. For travel HTML, also inspect:

- The first phone viewport, a long day, lodging, and a warning: trip identity,
  dates and next action remain clear, and sticky navigation does not cover anchors.
- Phone widths around 390px and 320px: date/time labels wrap sensibly, and only
  intentional table or navigation regions need horizontal scrolling.
- Theme, reduced-glass, section/map links and keyboard controls: they work and
  retain visible focus. Travel content remains available without JavaScript.
- A4 print, including from dark mode: readable white surfaces, working map
  references and expanded fallback content.

Record environment limitations honestly. Structural validation checks the HTML
contract and asset parity; it does not prove these visual conditions. A bounded
documentation or style change does not need a full model benchmark.

Visual alignment check: compare the delivered HTML and the local dashboard at
the same viewport and zoom. Check typography, spacing, surfaces and navigation
as well as icons; a matching icon family alone does not establish consistency.

## Icons

Use the bundled Lucide SVG assets for every HTML status/navigation icon.
No visible emoji in HTML. Keep semantic markers in Markdown for lint and risk
classification; `scripts/lib/travel/icons.py` converts text markers during render,
preserving links, canonical CSS/JS and accompanying labels. Do not load icons
from a CDN or replace verified/pending/risk distinctions with one generic state.
