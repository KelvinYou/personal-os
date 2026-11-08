# Artifact Design Guide

- [Status: OK]
- Updated: 2026-11-06
- Scope: shared visual and delivery conventions for presentations, social posts and other explanatory artifacts.
- Canonical owner: this document owns the shared contract; the owner's selected visual style lives in private `data/reference/artifact-style.md`.

## Composition and read order

Apply three layers: shared design → medium-specific format → optional identity.

1. Read this guide and [the owner's visual preferences](../data/reference/artifact-style.md) when present. If unavailable, use the current brief or supplied references without inventing personal defaults.
2. Read [the voice routing note](voice-guide.md) and the owner's personal direction when writing outward-facing material. Evidence standards and tone transfer across media; blog headings, TL;DR counts and article lengths do not.
3. Load the relevant medium: [presentations](presentation-guide.md) or [social posts](social-post-visual-guide.md). Other formats use their applicable artifact skill and the requested delivery format.
4. Load account identity only for a social post: `data/posts/brand.md` and identity assets explicitly selected there. Presentations and other artifacts do not inherit post names, series labels, signatures, avatars, mascots, logos or identity images. Topic illustrations and visual style can be reused independently of account identity.
5. Read the task's source material, evidence and existing artifact before editing it.

Explicit instructions for the current task take precedence. The medium owns dimensions, page structure and file format; identity owns attribution; shared preferences own reusable appearance. A client or event template can override the appearance for that task without changing the shared default.

These conventions cover authored artifacts. Runtime web interfaces and interactive 3D scenes retain their own design-system and scene-standard owners.

## Shared design

- Start with a concrete question and show the mechanism or evidence behind the conclusion. Distinguish observations, illustrative examples and interpretation.
- Give each page one main claim, a clear hierarchy and enough space for labels and qualifications.
- Reuse the selected palette, type hierarchy and illustration treatment across the artifact. Use emphasis sparingly and consistently.
- Recompose for the destination canvas. Keep text and evidence readable at the actual viewing size; do not stretch an existing export.
- Keep text, diagrams and recurring components editable where supported, and include the artwork required by the selected style. Generate or reuse suitable illustrations; do not claim rasterized text is editable. Editability does not waive an illustration requirement.
- Keep conceptual interfaces visibly distinguishable from real screenshots. Check factual names, quantities, arithmetic and process order against sources.

## Shared production and delivery

1. Resolve audience, medium, language, canvas and requested files from the brief. Use the medium's defaults only for missing details. User-requested artifact language takes precedence over the repository's English documentation convention.
2. Check source claims before layout. Do not turn missing evidence into a confident statement.
3. For a new visual treatment, build representative pages before scaling out: a cover and content page at minimum, plus any additional sample types required by the medium. Inspect hierarchy, image integration and explanatory accuracy before reusing the treatment. Ask for owner review when the task requests it, rather than introducing an automatic approval stop.
4. Save source material, prompts where used, editable source where applicable, exports and verification notes together in the task's destination. Post storage is owned by `data/posts/README.md`; other destinations follow the task and artifact skill. Personal drafts remain private.
5. Render and inspect every final page for wording, glyphs, overflow, overlap, contrast, cropping, page order and evidence accuracy. Check that required artwork is visibly present on the pages specified by the selected style; record those page numbers and asset paths in the production notes, or record the explicit override. Palette reuse alone does not establish style compliance. Recheck changed pages after corrections.
6. Deliver the requested artifact plus an inspectable preview, with clear links. State actual format/dimensions, editability and any unresolved verification or rendering limitations. Generation and visual checks do not constitute owner approval or publication.

## Acceptance

- Shared style remains recognizable when the canvas changes, including required illustration content. Inspect rendered artwork, not only palette and typography. Missing required artwork blocks a claim of style compliance; report an incomplete draft if it cannot be supplied.
- Each medium uses its own layout and delivery format.
- At thumbnail size, the main visual and hierarchy are clear; at intended viewing size, essential wording and labels are legible. Open space, alignment and contrast organize the page. Artwork helps explain the claim and its connections agree with the content. Neat alignment and image presence alone are insufficient for visual acceptance.
- A presentation produced without an identity brief contains no social-account identity assets.
- Claims and sources survive layout changes; every final page has been inspected.
- The delivery accurately describes which components are editable and which are flattened images.
