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
- Demand evidence: ask the owner to type the seed word into XHS search and paste the dropdown suggestions, or search the web for the phrasing people actually use. Record observations, source references, timestamps and qualifications in the selected post's `lab.yaml` under `experiment.demand_evidence`. Never claim search volume you did not observe.
- Record the selected candidate's five gate results in `lab.yaml` under `experiment.gate` (`question: 1..5`, `result: pass|fail|unknown`, `note`), alongside `hypothesis` and `changed_variable`. `lab.yaml` is the sole structured owner; `post.md` keeps candidate reasoning, copy and prose, and existing historical gate tables stay untouched. Use the Pydantic owner in `scripts/lib/content_lab.py` and run `make posts-check` after every record write. Failed/unknown question 1 cannot be treated as passing the topic gate.
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

### Research posts: rendered chart pages

When the post folder has `sources/research-data.json` (filed from the Finance Research desk), its numbers are owned by the Python model, not by you or the image generator.

- Plan 2–4 **data chart** pages: `networth`, `monthly`, `breakeven`, `grid`. Cover, mechanism, checklist and closing pages stay generated.
- Write one spec per chart page in `charts/<NN>-<name>.json`. Fields are in `scripts/lib/post_chart.py::PageSpec`; set `"data": "../sources/research-data.json"`.
- Put every number in a spec through a `{{fact}}` placeholder. A typed digit fails the spec on purpose. Write years and ratios as `{{horizon}}` or in Chinese words.
- Mark the page's single hotspot with `[[...]]`. Use `\n` for a headline line break.
- Render each page with `make post-chart SPEC=data/posts/<id>/charts/<NN>-<name>.json OUT=data/posts/<id>/images/<NN>-<name>.png`. Never regenerate a chart page with `image_gen`, and never edit its numbers by hand.
- In `verification.md`, cite `sources/research-data.json` plus the sources listed inside it for every figure. Use the public scenario only; `post.md` → Must avoid lists the owner's limits.
- Chart pages are flat by design, as the style allows for 2D charts. The cover and mechanism pages still carry the 3D artwork, so the set keeps its signature.

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

## Autonomous mode (Content Lab pipeline)

Applies when the instruction starts with `AUTONOMOUS` (sent by `scripts/content_pipeline.py`). Nobody is there to answer, so every "ask the owner" above changes into a rule you follow without asking. Steps 1–6 still apply. Write only inside the named post folder.

- **Topic:** the idea brief in `post.md` names the topic. Still score the five gate questions. If question 1 fails, record the gate and stop. The final message says why it failed; do not swap in a different topic.
- **Demand evidence:** use WebSearch for the phrasing people actually use (forums, XHS/Lowyat/Reddit pages that are publicly indexed). In each `qualification`, write that this is web evidence and not an XHS search-volume figure.
- **Employer or private-repository material:** never use it. There is nobody to clear it, so generalise the mechanism.
- **Owner feedback:** the run instruction lists change notes, oldest first. Address every note, and say in `post.md` which change answers which note.
- **Images:** `printf '%s' "<instruction>" | codex exec -s workspace-write -C data/posts/<id> --image <style-reference>`. This keeps Codex writes inside the post folder.
- **Critic (step 5):** you are the critic and Codex is the generator; that different-family split is intentional. Downscale copies one command per page with literal paths. The allowlist denies loops and `$VAR` expansion; this was observed in the first run on 2026-11-09. Use `sips -Z 800 data/posts/<id>/images/01-cover.png --out data/posts/<id>/.qa/01-cover.png`, then Read each page and the whole set. Regenerate a failing page at most twice. After that, record the failure in `verification.md` and set `readiness.visual: failed`; do not keep looping.
- **Sameness:** XHS penalises batches of near-identical AI posts. Read the cover and sequence table of the three most recent posts in `data/posts/`, and do not repeat their cover composition or page-type order.
- **Readiness:** set `factual: passed` only when every on-image claim has a primary source in `verification.md`. Set `visual: passed` only when every step-5 box passes on every page. Never edit `stage`, `pipeline` or `owner_review`; the runner decides whether the package reaches review.
- **Final message (three lines):** what was made; the weakest claim or page; what the owner should look at first.

## 7. Seven-day review

After 7 days, record actual publication evidence and views, likes, saves, comments, shares and post-attributed follows in `lab.yaml` (`publication`, `measurements`), alongside the structured gate results from step 1. Each observation requires its timestamp, source reference and organic/paid/mixed/unknown coverage. Missing metrics are null, observed zero is 0; account-level follower growth is not post-attributed follows. Keep observations before publication invalid. For the Content Lab's comparison, collect an observation at 168–192 hours after publication, and compare the same coverage against the account's own median, not viral examples. Keep older prose results untouched and do not backfill inferred numbers. Run `make posts-check` after every record write. When three comparable posts have results, check whether gate questions 2–4 predicted saves; propose any skill revision from that evidence rather than new articles, following the owner's correction/change workflow.
