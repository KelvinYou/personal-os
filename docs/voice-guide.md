# Voice Guide

Extracted from all 34 published posts in `repos/portfolio-website/src/content/blog/`
on 2026-08-24. Every rule below is a measured pattern, not a preference someone
asserted — the counts are included so a future reader can check whether the rule
still describes the corpus, or whether the corpus moved and the guide went stale.

**Who reads this:** any agent drafting prose in Kelvin's name — blog posts,
LinkedIn/Jobstreet copy (`profile-optimizer`), README and doc prose, commit
bodies. It does not govern Personal-OS internal reports; those follow the
`[Status: OK/Warning/Critical]` engineer-log convention in `AGENTS.md`.

**Refresh cadence:** re-derive after every ~10 new posts. Stale voice guides are
worse than none, because they launder an old style as a current rule.

---

## The one-line version

Concrete failure first, mechanism second, generalisation last — and the
generalisation has to be falsifiable. If a paragraph could be pasted into
someone else's post unchanged, it is not in this voice.

---

## Measured shape

| Property | Value in the corpus |
| :--- | :--- |
| Post length | median 805 words (range 109–2,792) |
| Sentence length | median 17 words, mean 19.8, p90 36 |
| `**TL;DR**` block | 20 of 34 posts, **always exactly 3 bullets** |
| Em dashes | 431 across 31 of 34 posts (~13/post) |
| First person `I` | 191 uses across 21 posts |
| Second person `you` | 207 uses across 29 posts |
| Bold lede sentence (`**…**` opening a point) | 44 across 14 posts |
| Language | English default; Chinese only for personal-finance/career posts |

Two of those are worth stating as rules because they contradict common
"AI writing" advice:

- **Em dashes stay.** They are a signature here at 13 per post, not a tell. Any
  instruction to strip em dashes from Kelvin's prose is wrong.
- **Second person outnumbers first person.** The reader is addressed directly and
  often. This is not a diary; it is a briefing.

---

## Structure

The corpus uses one skeleton, with variation only in the middle:

```
**TL;DR**                  ← 3 bullets, exactly. Not 2, not 5.
                              Bullet 1: the concrete situation
                              Bullet 2: the mechanism/fix
                              Bullet 3: the actual lesson ("the real lesson is…")
<cold open>                ← the failure, in the second person or as a scenario.
                              No throat-clearing, no "in this post I will".
## <mechanism>             ← what the thing actually does, with real code
## Why <the bug was hard>  ← the diagnosis. This is the section readers stay for.
## The transferable part   ← 14/34 use this exact heading
   or ## What generalizes  ← 8/34
   or ## What I'd keep     ← the retrospective variant
```

Recurring heading vocabulary, in frequency order: `## The transferable part`
(14), `## The fix` (9), `## What generalizes` (8), then one-off `## Why <X>`
headings. Prefer reusing these — a reader arriving from another post already
knows where the payload is.

**Closing sections are bold-lede lists.** Each item opens with a bolded
imperative or claim, then 2–4 sentences of argument:

> **Audit the advice, not the human.** Same data, but "your P0 was missed three
> weeks running" is a verdict on a person and "this objective has been scheduled
> three times and never achieved" is a bug report against a planner.

> **Make honesty monotone.** The property I like most about DSR is that searching
> harder *raises* the bar.

Two to four of those, then — for a post about a public repo — one line linking it.

---

## Titles

Two shapes, both in use:

1. **Colon split** — concrete artifact, then what it is:
   *"The Status Column Is the Lock: Duplicate-Submit Protection Without an
   Idempotency Key"*
2. **Bare narrative claim** — a sentence that states the bug:
   *"Computed Once, Wrong Forever"*, *"The Flag Meant 'Done', But 'Done' Hadn't
   Happened Yet"*, *"Disabling It Did Nothing, Because 'Off' and 'Never Set'
   Looked the Same"*

Both name the *specific mechanism*. None is a category label ("A Guide to
Concurrency"). The title is usually the bug's shape stated in plain words, which
is why several read like the punchline of the post.

Frontmatter is fixed: `title`, `date`, `description`, `tags`, `author`
(+ optional `image`). `description` is one or two sentences that already contain
the finding — it is not a teaser.

---

## What the corpus never does

Scanned all 34 posts. These constructions appear **zero** times, and that is
almost certainly deliberate:

| Construction | Hits |
| :--- | ---: |
| "It's not X, it's Y" / corrective antithesis | 0 |
| "X isn't just Y" | 0 |
| "The key insight is…" | 0 |
| Rhetorical "The difference? …" / "The catch? …" | 0 |
| "Here's where it gets interesting" | 1 (in 1 post) |

Also absent: emoji in English posts, exclamation marks, fake statistics,
invented scenarios presented as real, and hype adjectives on one's own work.

`delve`/`leverage` appear 9 times but concentrated in 2 posts — the two oldest,
pre-dating the current style. Treat them as drift, not as licence.

---

## The epistemics, which are the actual voice

Style rules are cheap to imitate. What makes the corpus recognisable is a
consistent stance, visible in almost every closing section:

1. **State what would falsify the claim.** Load-bearing assertions come with the
   evidence that would contradict them. `depth: built` means "a public repo of
   mine runs on it — go open it," not "I'm good at this."
2. **Publish the number that loses.** *"My Trading Signal Loses to Buy-and-Hold.
   I'm Publishing It Anyway."* The benchmark that beats you goes in the post.
3. **Separate what you measured from what you argued.** "I can show you the code
   that makes the desks independent. I cannot show you a chart proving the
   argument stage improves accuracy, because I haven't run the ablation."
4. **Name the counter-argument you take seriously, then answer it.** Several
   posts carry a literal `## The counter-argument I take seriously` section. The
   objection is stated at full strength before being addressed.
5. **The lesson is a rule, not a feeling.** Closing items are actionable
   constraints ("do all the work that can fail before you take the lock"), never
   sentiment ("this taught me a lot about humility").

An agent that follows the formatting rules and drops these is producing a
convincing forgery. These are the load-bearing part.

---

## Drafting checklist

Before handing a draft over:

1. Is the opening a concrete failure or scenario, with no preamble?
2. Exactly 3 TL;DR bullets, ending on the real lesson?
3. Does the mechanism section show real code, config, or a diagram — not a
   description of code?
4. Median sentence around 17 words; anything over ~36 split?
5. Does the closing list have 2–4 bold-lede rules, each one falsifiable?
6. Zero instances of the constructions in the table above?
7. Any claim about a result — is it stated as measured or as argued, explicitly?

---

## Source material

- Corpus: `repos/portfolio-website/src/content/blog/*.mdx` (34 posts)
- Process notes, unpublished: `repos/portfolio-website/src/content/for-me/blog-sop.mdx`
  — that file is about *how to turn input into a draft* (the 5-step
  watch-then-write-from-memory loop). This file is about what the draft has to
  sound like. Different jobs; keep both.
