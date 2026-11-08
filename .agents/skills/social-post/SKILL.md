---
name: social-post
description: >
  Plans, generates and reviews XHS image-carousel posts under data/posts/: picks
  the topic through a reader-demand gate, sequences page types, writes image
  prompts with the restraint rules, runs visual QA and prepares publication copy
  with the AI-content label. Use whenever the user wants a new post, a post
  idea, a topic shortlist, new or revised post images, a review of how a post
  looks, or publication copy for XHS / TikTok — even if they only say "make a
  post about X" or "what should I post next".
---

# Social Post

[Status: OK] — rules derived from a review of the first three posts (DuitNow, Double 11, dtc-e2e-tests) on 2026-11-08. They are hypotheses until the account's own 7-day numbers confirm them; see step 7.

The two failures this skill exists to stop:

1. **Supply-driven topics.** Picking what the author knows instead of what readers hit in daily life. The repository-explainer draft failed this; the Double 11 post passed it.
2. **Template sameness.** Every page as headline + stacked rounded pills + magenta strip + two-line disclaimer, so a set reads like slides and looks generated.

## Read first

1. `docs/social-post-visual-guide.md` — page types, restraint rules, platform canvas. This skill does not restate them.
2. `docs/artifact-design-guide.md` and private `data/reference/artifact-style.md` — palette and 3D material.
3. Private `data/posts/brand.md` — display name, series label, language voice, AI disclosure.
4. Private `data/posts/README.md` — folder layout and version lifecycle.

## 1. Topic gate (before anything is drawn)

Score each candidate. Question 1 is a hard gate: a "no" ends the candidate, however interesting it is to the author.

| # | Question | Pass looks like |
|---|---|---|
| 1 | Does a Malaysian reader meet this system at least monthly? | scan-to-pay, online shopping, bank transfer, tax filing, tolls |
| 2 | Is there an anxious or money-at-stake moment? | payment stuck, discount doubt, deduction not refunded |
| 3 | Can the reader save and act on a page? | checklist, decision rule, "check these 3 things" |
| 4 | Is there a time hook? | 11.11, tax season, a rule taking effect |
| 5 | Can an engineer explain something a lifestyle blogger cannot? | the mechanism behind the anxious moment |

- Build at least 3 candidates; recommend the highest-scoring one and say why the others lost.
- Pick the failure or doubt moment, not the happy path. "Where does my money go after a successful scan" is curiosity; "payment stuck, do I press again" is a need.
- Demand evidence: ask the owner to type the seed word into XHS search and paste the dropdown suggestions, or search the web for the phrasing people actually use. Record it in `post.md`. Never claim search volume you did not observe.
- Material from the owner's employer or private repositories needs explicit owner confirmation that it may be published. Default: generalise the mechanism and drop internal names, paths and known limitations.

## 2. Sequence (6–9 pages)

Plan the set as a table in `post.md`: page, reader question, page type, hero object. Rules:

- Choose page types from the visual guide's library. No two consecutive pages share a type; at most two pages use stacked rows.
- Every abstract concept gets a physical object (price tag, envelope, receipt, standee). This was the strongest page type in the first three posts.
- Exactly one saveable page (checklist or one-picture summary) and one closing page with a single A/B question drawn on the image.
- Each page ends with one plain takeaway line.

## 3. Verify before prompting

Write `verification.md` first: each on-image claim, its primary source and its qualification. Hedge mechanisms that vary by bank or wallet ("有机会", "一般"). An unverified claim does not go on an image.

## 4. Prompts

Write `prompts.md` with a shared block plus one section per page. The shared block must carry the restraint rules from the visual guide verbatim, the header/footer from `brand.md`, and the language split (English inside device screens, Malaysian Chinese editorial text). Give every page one orange handwritten aside in the account voice, attached to an object.

Generation runs in Codex's built-in `image_gen`. From Claude Code, pipe the instruction through stdin — `--image` is variadic and swallows a positional prompt:

```bash
printf '%s' "<instruction naming prompts.md sections and output paths>" \
  | codex exec -s workspace-write -C <repo> --image <style-reference.png>
```

## 5. Visual QA (every page, before showing the owner)

Downscale to 800 px and inspect each page, then the set side by side:

- [ ] Exact 3:4 ratio (`sips -g pixelWidth -g pixelHeight`); generator output can drift (1058 × 1487 on 2026-11-08). Crop, do not stretch.
- [ ] Series signature present: blush background, magenta underline, rounded matte 3D. Restraint that removes these reads as another account.
- [ ] Cover headline readable at 25% size; topic recognisable from the hero object alone.
- [ ] One magenta hotspot per page; no decorative bursts; every arrow explains something.
- [ ] At least ~30% calm background; one hero scene, not a grid of equal elements.
- [ ] Disclaimers: one footer line on the image; the rest in the caption.
- [ ] Orange aside present and in voice; image text uses the same Malaysian colloquial register as the caption, not textbook Mandarin.
- [ ] Set rhythm: no two consecutive pages with the same layout.
- [ ] Every claim on the image appears in `verification.md`.
- [ ] Generator defaults match the locale: no "$" on coins or price props in an RM post (v2 cover, 2026-11-08). Fix with a single-change image edit, not a full regeneration.

Record pass/fail per page in `verification.md`. Regenerate failing pages; do not ship "close enough".

## 6. Publication copy

Write `publish.txt`: title (primary keyword within the first 10–12 characters), caption of 200–500 characters with the keyword in the first 100, one soft save prompt, 6–9 hashtags mixing broad and niche, and a pinned comment with one A/B question.

Publication checklist for the owner (the agent never posts):

- [ ] XHS AI-generated content label switched on.
- [ ] Source qualifications present in the caption.
- [ ] Employer or third-party material cleared.

## 7. Seven-day review

After 7 days, record views, saves, comments and follows in `post.md` under "Results", next to the gate scores from step 1. Compare with the account's own median, not with viral examples. When three posts have results, check whether gate questions 2–4 predicted saves; revise this skill from that evidence, not from new articles.
