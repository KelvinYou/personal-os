# Presentation Format Guide

- [Status: OK]
- Updated: 2026-11-08
- Scope: PPT / slide format and delivery; shared appearance is owned by [the artifact design guide](artifact-design-guide.md) and its private style reference.

## Before producing slides

Read the shared guide and selected style, then use the available presentation skill for creation, rendering and verification. Resolve audience, purpose and language from the brief. This document does not replace the skill's tool-specific workflow.

No post account identity or identity images are loaded by default. Use only the presenter, organization or event identity explicitly supplied for this presentation.

## Presentation mode

Resolve the mode from the brief and record it in production notes:

- **Presented:** a speaker guides the audience. Prioritize a clear claim and visual evidence on each content slide; move supporting narration into speaker notes or an appendix.
- **Read independently:** the deck must explain itself without a speaker. Allow more supporting context, clear section navigation and captions, while retaining hierarchy and readable type. Do not compress a report into tiny text.
- If the brief gives no indication, default to presented mode and state that assumption. Do not stop production merely to request a mode choice.

## Canvas and page organization

- Default to landscape 16:9 when the brief and template specify no canvas.
- Recompose portrait references for the slide canvas; reuse their palette, typography and illustration treatment rather than enlarging a carousel image.
- When the selected shared style requires 3D artwork, include it on the cover and main mechanism/explanation slides as specified by the style owner. Build those slides from topic-relevant 3D image assets plus editable text and diagrams. A deck composed solely of text, flat cards and arrows does not satisfy that requirement.
- Use a clear title and purpose, one main claim per content slide, and a closing conclusion or action appropriate to the audience. Choose slide count from the material; there is no fixed carousel sequence or TL;DR count.
- Keep evidence, chart labels and source qualifications legible. Put supporting detail into notes or an appendix when appropriate without hiding a limitation needed to interpret the slide.

## Typography and layout defaults

These are owner-approved production starting points for a standard 16:9 deck, not universal research thresholds. Values are actual PowerPoint points, not preview pixels; verify the generated file and rendered output.

| Role | Starting range | Use |
|---|---|---|
| Focal claim or key number | 72–160 pt | At most one per slide; the single phrase or figure the audience should remember |
| Cover headline | 44–60 pt | One concise subject or promise |
| Content headline | 32–40 pt | A concrete message, normally at most two lines |
| Main body and explanatory labels | 22–28 pt | Essential reading in presented mode |
| Secondary labels and captions | 18–22 pt | Supporting context, still readable at the destination |

Use a coherent type family with regular, semibold and bold weights; add a second family only for a defined role such as code or metadata. Verify Chinese glyph coverage and record font substitution. Do not use thin grey text for essential explanations.

If content does not fit, shorten, restructure or split the slide before reducing type. Independently read decks may carry more text, but retain the hierarchy and use 18 pt as the initial body-size floor. Nonessential credits can be smaller only when they remain readable in the delivered reading artifact; a caveat necessary to interpret a result must stay in the readable content area. A supplied template or unusual viewing environment may require adjusted sizes; record the rationale and inspect the result.

Establish a consistent grid, outer margins and content anchors in reusable layouts or the slide master. Let the current claim determine the focal point. A large unused area does not compensate for crowded text elsewhere.

## Page families and sample review

Use the families the material needs; they are not a mandatory sequence or a quota:

| Family | Composition and purpose |
|---|---|
| Cover | Strong headline and a dominant topic-specific visual |
| Mechanism / process | Actual stages and relationships, with labels placed on the relevant objects |
| Comparison | Aligned before/after or alternatives, with the difference visibly emphasized |
| Evidence / data | A dominant chart, result or artifact supporting the headline; de-emphasize chart scaffolding |
| Conclusion / action | A clear takeaway and the next action or decision |

Avoid a deck dominated by the same left-text/right-square-image composition. Choose layouts to clarify different kinds of content; do not introduce random variation for decoration. The private style owner defines illustration finish, palette and image integration.

Before extending a new treatment to the whole deck, render and inspect three representative samples: cover, mechanism/process and evidence/data. If the material lacks one type, substitute another substantive page and record why. Check the samples together as thumbnails and individually at presentation size. Sample review is an agent production check; owner approval is a separate step only when requested.

## Visual acceptance

- At thumbnail size, each slide has a clear focal point and the deck shows purposeful changes in composition while retaining a coherent identity.
- **Dominant element (measurable):** every content slide has one element that clearly outranks the rest. If it is text or a number, its size is at least 3× the slide's main body size (for example ≥ 72 pt against 24 pt body); a 32–40 pt content headline does not count. If it is artwork, a chart or a diagram, it covers at least a quarter of the slide. A content slide with neither fails. Reference inventories in an appendix are exempt. `make deck-lint DECK=… [EXEMPT=…]` enforces this and the cover-artwork requirement; limits live under `presentation:` in private thresholds. It cannot judge whether artwork is 3D, on-topic or well composed.
- **Composition rhythm (measurable):** a slide's layout is derived from its geometry, not self-reported: focal kind and column plus body-text column, e.g. `art-C/text-C` or `art-R/text-L` (`make deck-lint DECK=… LAYOUTS=1` prints them; record them in production notes). Among content slides (cover and exempt slides excluded), no three consecutive slides share a layout, and in decks of six or more content slides no layout covers more than one third. Vary the layout because the content differs, not by moving the same picture from side to side.
- At the intended viewing size, headlines, main text and necessary qualifications are readable. Verify actual font sizes rather than assuming pixel-sized design values became the same point sizes.
- Content slides communicate a claim supported by a visual, comparison or evidence object. Reference inventories may use structured text; avoid turning the deck into a sequence of topic headings and lists.
- Artwork and annotations are integrated into the layout. Verify correspondence between illustrated stages and the real process; a decorative subject image alongside an unrelated full text explanation is insufficient for a mechanism slide.
- Required 3D artwork meets the shared style's material, lighting and content requirements. Its presence alone does not establish composition quality.
- Record visual defects and the corrected slides in production notes. Unresolved defects mean a draft, not a passed visual review. Agent inspection is not owner approval or a guarantee of aesthetic preference.

## Deliverables

- For a PowerPoint request, deliver `.pptx` plus rendered slide previews or a contact sheet. Add PDF when requested or required by the presentation workflow.
- Keep text, charts and diagrams editable where the tools support it; embed required 3D illustrations as image assets. Describe any flattened slides or other editability limits. Do not drop artwork to make the deck entirely native shapes.
- Inspect every rendered slide at presentation size and check the native file's page count and order. Verify that required artwork is embedded in the deck and visible on the specified slides; record slide numbers and asset paths in production notes. Embedded media alone does not prove a 3D visual treatment. A deck with zero 3D artwork fails the shared 3D style unless explicitly overridden by the owner or a supplied template. Report unverified rendering or font substitutions.
- Run `make deck-lint DECK=…` on the final `.pptx` before delivery; a deck with findings is a draft. In Claude Code a Stop hook (`scripts/deck_hook.py`) enforces this for every `.pptx` changed in the session. Exempt an appendix inventory or closing slide only through `{"deck_lint": {"exempt": [n], "reason": "…"}}` in the task's `production.json`; an exemption without a reason is ignored.
- Keep sources, prompts, previews and exports together in the task's specified destination; do not store decks under `data/posts/` merely because they share the visual style.

## Research basis

Consulted on 2026-11-06. The sources support clarity, hierarchy and readable visual communication; the private art direction, type ranges above and three-sample workflow are owner-selected production conventions.

- [Duarte: Perfect your slide design](https://www.duarte.com/blog/perfect-your-slide-design/): use visual consistency, deliberate reading order, contrast and open space to focus attention.
- [Harvard Catalyst: Slides](https://catalyst.harvard.edu/writing-communication-center/visualize-science/slides/): support clear message headlines with visual evidence and minimize bullet lists.
- [Microsoft: Creating and delivering an effective presentation](https://support.microsoft.com/en-us/powerpoint/tips-for-creating-and-delivering-an-effective-presentation): use readable fonts, minimize text, maintain contrast and generally avoid sizes below 18 pt; larger rooms may need larger type.
- [Duarte: Displaying data in presentations](https://www.duarte.com/blog/display-data-in-presentations/): emphasize the relevant data and distinguish spoken presentations from independently read slide documents.

Added 2026-11-08 after the v4 dtc-e2e deck review, which found 36 pt headlines over 22–24 pt body on every slide (ratio 1.5×), a 3× or larger focal element on only 2 of 12 slides, and one title-top / centered-cluster layout repeated across most content slides. The 3× ratio and one-third rhythm cap are owner-selected thresholds, not research values.

- [Penn State: Assertion-evidence research](https://writing.engr.psu.edu/research.html): sentence headlines plus visual evidence improved recall over topic-plus-bullets slides (Garner & Alley, 2013).
- [Carmine Gallo on Apple slide design](https://www.carminegallo.com/?p=3927): one theme per slide, with a single statistic given the whole slide.
