# Social Post Visual Guide

- [Status: OK]
- Updated: 2026-11-08
- Stage: shared design extracted; this document owns post-specific composition and platform adaptation. Each private post folder owns asset review and publication status.
- Scope: image carousels, titles and concise captions. Video is deferred for the current account experiment.
- Canonical owner: this document owns post format; [shared design](artifact-design-guide.md) owns reusable visual and delivery rules. Private identity, post copy and assets remain under `data/posts/`.

Build a recognisable engineering explainer series around an everyday question, a visible mechanism and a concrete takeaway. Each post should look authored by the same person while allowing the topic and illustration to change.

## Read order

Read [the shared artifact guide](artifact-design-guide.md) and its private style reference first, then this post adapter, `data/posts/brand.md` and the target post's `post.md`. Read the voice and personal-direction references as directed by the shared guide.

## Post identity

Resolve display name, recurring column, signature, device preferences and any approved identity images from `data/posts/brand.md`. Attribution is small plain text in a consistent position. Do not copy another owner's name or identity artwork. Identity is applied only to post outputs; shared illustration style can be used in other media independently.

Palette, typography and illustration materials are owned by `data/reference/artifact-style.md`; reference them rather than maintaining a second set here. Private account settings own the current avatar/mascot decision and topic-specific UI language.

### Factual names and generic visual assets

For the selected payment-explainer treatment, retain factual product names and official source citations in ordinary text. Use original generic network nodes, QR standees and wallet interfaces instead of third-party logos, official packaging or copied app layouts. Redesign the whole component rather than removing a logo from an otherwise copied design. Label invented interfaces and QR props as conceptual; do not present them as a real app screenshot or official standard. Keep phone hardware consistent with the account's device preference. This visual treatment is not a claim of legal clearance.

The selected QR prop may use pink as an accent while retaining its original straight border and rectangular colour tab. Keep this separate from the official standee's curves, oval framing, typography and logos; matching a topic colour does not require copying its full visual design.

For the selected account treatment, use English inside illustrated QR payment props, phone screens, merchant-device screens and security UI panels. Keep the surrounding editorial explanation and annotations Chinese. Apply the same wording to miniature QR cards in phone-camera previews; do not translate only the large foreground object.

## Page families

### Cover

Use small text attribution and a restrained series label, a short concrete question in large type, one recognisable subject and a concise promise. For the selected cover direction, let the subject overlap the edge of the typography to create depth while keeping the title and product identifier readable. The question should remain clear as a feed thumbnail.

### Explanation

Keep the post attribution strip and shared palette and typography. Use one claim per page, a short explanation and one diagram, comparison or evidence object. Avoid repeating the cover's full visual density. Clearly distinguish illustrative values from measured results.

The current sample sequence pairs a typography-and-object cover with a counterintuitive magnified detail page and a front-stage/account-change process page. These are composition choices for the sample, not a mandatory sequence for every post.

### Closing

Reuse the same signature and series label. Ask one specific follow-up question or present two short options. Keep source qualifications legible.

### Page-type library

Choose each explanation page's type from this list. No two consecutive pages share a type, and at most two pages in a set use stacked rows.

| Type | Use when | Composition |
|---|---|---|
| Object metaphor | A concept needs to become tangible | One or a few physical objects, each labelled directly; strongest type in the first posts |
| Misconception vs fact | The reader holds a wrong default | Two halves or a before/after object; one verdict line |
| Mechanism scene | Something travels between parties | One low platform, objects left to right, dashed paths; labels on the paths |
| Process | Order matters and has 3–5 steps | Stacked rows allowed here; cap two per set |
| Checklist | The saveable page | Numbered actions with one icon object each |
| Closing | Last page | One question with A/B options drawn on the image |
| Data chart (rendered) | A research post needs exact numbers | Same header, headline hotspot, takeaway, aside and footer; one flat 2D chart on a cream card, built from `sources/research-data.json` by `make post-chart`, never generated |

## Restraint rules

Derived on 2026-11-08 from a review of the first three sets, where every page converged on the same dense template. These are design hypotheses; the account's own results decide whether they stay.

- One magenta hotspot per page, normally the marked headline words. Borders, badges, number chips and strips use neutral cream or ink.
- No decorative burst or sparkle marks. Every arrow and line points at something it explains.
- One hero scene per page with at least about 30% calm background. Avoid filling empty space with small badges or props.
- Matte, plausible proportions and low gloss; one or two supporting props. Uniform glossy clay across every object reads as generated.
- Disclaimers: one footer line on the image. Longer qualifications belong in the caption. Exception: a qualification that changes the meaning of a specific object stays next to it.
- Each page carries one orange handwritten aside in the account voice, attached to an object. Image text uses the same colloquial register as the caption; private language settings live in `data/posts/brand.md`.
- Each page ends with one plain takeaway line; it does not need its own coloured box.
- Restraint must not strip the series signature. Keep the warm blush background, the magenta hand-drawn underline under the highlighted headline words and the rounded matte 3D material. The 2026-11-08 prototype dropped all three, became clearer but read as a different account, and its photoreal phone broke material continuity.

## Platform adaptations

- XHS working canvas: 1080 × 1440, portrait 3:4.
- TikTok video working canvas: 1080 × 1920, portrait 9:16.
- Recompose for each canvas; keep type and identity marks proportional instead of stretching an exported image.
- Keep essential content clear of platform controls and captions. Check the actual preview; TikTok safe zones vary with placement and caption length.
- The TikTok references below describe advertising creative; use their composition guidance as a reference, not as a claim about organic ranking or a guarantee of engagement.

## Production and storage

Follow the shared guide's evidence, sample-page, editable-layout and full-page inspection workflow. For posts, additionally check the account attribution, series label, platform crop and page numbering. Deliver ordered final images and the requested publication copy; video is deferred for the current account experiment.

Storage and version lifecycle are owned by [data/posts/README.md](../data/posts/README.md). Keep post content, current prompts and exports together; identity assets are referenced from private brand settings.

Recommended private structure:

```text
data/posts/<topic>-YYYY-MM-DD/
  publish.txt
  post.md
  verification.md
  prompts.md
  images/      # current final set only
  sources/     # optional
  video/       # optional
```

Layout rules live in [data/posts/README.md](../data/posts/README.md); this link is unavailable in public-only checkouts.

## Review criteria

- Can a reader recognise the author after seeing several posts?
- Is the topic clear from a small cover preview?
- Does the cover promise match the explanation?
- Do the cover and inner page share a visible identity?
- Can a new topic reuse the system without redesigning every component?
- Is every depicted payment flow explicitly conceptual where appropriate?
- Does the set vary page type and layout, with one magenta hotspot per page?
- Does the image text sound like the same person as the caption?

The `social-post` skill (`.agents/skills/social-post/`) owns the topic gate, the per-page QA checklist and the publication checklist, including the platform's AI-content label.

A visually attractive template is a design hypothesis. Assess actual results through completion, saves and useful responses; appearance alone does not establish performance.

## References

- [Canva cream black and orange informational carousel](https://www.canva.com/templates/EAG3d2sl_KA-cream-black-and-orange-simple-clean-informational-tips-instagram-carousel-post/): editable layout reference.
- [Canva yellow personal notes carousel](https://www.canva.com/templates/EAGsewxZwmA-yellow-simple-minimalist-personal-notes-message-instagram-carousel/): personal notebook reference.
- [Behance personal brand carousel](https://www.behance.net/gallery/235911951/5-Steps-Build-a-Personal-Brand-Online-Carousel-Design): contrast and series reference; not a verified editable template.
- [XHS layout factory](https://github.com/irenerachel/xiaohongshu-layout-factory-skill): reference workflow for stable character assets, HTML layouts and repeatable portrait exports; not installed.
- [TikTok creative best practices](https://ads-useast2a.tiktok.com/resources/help/article/creative-best-practices?lang=en): vertical video and UI safe-zone guidance.
- [TikTok in-feed specifications](https://ads.tiktok.com/resources/help/article/tiktok-auction-in-feed-ads?lang=en-GB-8): placement-dependent safe-zone guidance.

References were consulted on 2026-11-05. Visual treatment and palette are proposed creative choices.

