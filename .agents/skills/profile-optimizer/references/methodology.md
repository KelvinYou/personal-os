# Profile Optimization Methodology

Detailed methodology. SKILL.md references this document in Steps 3-5.

## 1. XYZ Formula (core of bullet rewriting)

Source: public advice from Google recruiters, widely adopted by SEA fintech / big-company hiring.

> **Accomplished [X], as measured by [Y], by doing [Z].**

- **X (What)**: the concrete result you produced (not a task, an outcome)
- **Y (Measure)**: the quantified metric — percentage, absolute number, time saved, user count, GMV, etc.
- **Z (How)**: the key technical decision or method (lets people judge whether you're senior/junior)

### Good vs. bad comparison

❌ "Worked on the payment system to improve performance."
- No X (improved by how much?), no Y (measured by what?), Z is too vague

✅ "Reduced p99 payment API latency from 800ms to 180ms (-77%) by introducing
   request coalescing and replacing SQL N+1 with a single JOIN."
- X: latency reduction
- Y: 800ms → 180ms (-77%)
- Z: request coalescing + SQL refactor

### When the user has no quantified data

Don't make numbers up. In the rewrite candidates, **leave a placeholder** and explicitly tell the user what
to fill in:

> "Reduced checkout drop-off by **[X%]** via Stripe + local PSP integration with
> idempotent retry layer. **Please provide: the specific percentage improvement in drop-off, or another
> metric such as user count.**"

Better to leave `[X%]` for the user to fill in themselves than to write "significantly improved."

### Three variants of XYZ (pick by scenario)

1. **XYZ-strict**: all three parts present, suits senior key bullets.
2. **Outcome-first**: bring X+Y to the front of the sentence, Z trails as a prepositional phrase. Suits the
   top 3 bullets that need to grab attention in the first 6 seconds.
3. **Tech-emphasis**: Z first, X+Y after. Suits target roles that are very tech-heavy (e.g. ML infra,
   distributed systems), where the recruiter is a tech lead rather than HR.

---

## 2. Skill Gap three-color classification rules

Inputs:
- `user_skills` — all skill keywords extracted from the profile text (including the skills section,
  experience bullets, and project descriptions)
- `jd_top_skills` — the top-30 frequency list for the target direction from `market/jobs/trends.json`

### Normalization

Merge the following variants into one canonical name:
- "Postgres" / "PostgreSQL" / "psql" → `PostgreSQL`
- "k8s" / "Kubernetes" → `Kubernetes`
- "JS" / "JavaScript" / "ECMAScript" → `JavaScript`
- "AWS" counts as its own category, but "AWS Lambda" / "AWS S3" count separately (fine-grained services)

The normalization table is maintained in the script (if one is factored out in the future); for now the LLM
judges it itself.

### Classification thresholds

| Category | JD frequency (% of sample) | Appears in user profile | Action |
|------|------------------|-------------------|------|
| ✅ Hit | ≥ 30% | Yes | Keep; check whether phrasing matches JD mainstream |
| ⚠️ Gap | ≥ 30% | No | **Focus here**: do you have it but didn't write it? Or don't have it and should learn it? Flag for the user |
| 🟡 Niche-strength | < 30% but > 10% | Yes | Keep as a differentiating selling point |
| ❌ Dead-weight | < 5% | Yes | Evaluate demoting/removing |

Frequency's "% of sample" means: of the N JDs fetched, how many mention this skill.
A sample < 30 is **unreliable** — flag this explicitly in the report.

### Two sub-types when high-frequency but not written

Within the ⚠️ Gap category, split further:

- **Type A: has it but didn't write it** — other bullets/projects imply it (e.g. did backend work but the
  skills section doesn't list SQL). Recommend adding it to the skills section or mentioning it explicitly in
  a bullet.
- **Type B: doesn't have it** — no related signal appears anywhere. Recommend either learning it (if it's a
  core skill) or abandoning this direction.

Don't conflate the two and give them the same action recommendation.

---

## 3. Section ordering heuristics

### Default Experience ordering

Reverse chronological is industry standard, **don't invert it**. But you can:
- "Spotlight" an earlier but more relevant role in the summary/about section
- Put the target direction's key skills first in the skills section

### Projects ordering formula

Score = `JD_keyword_match_count × outcome_strength`

- `JD_keyword_match_count`: number of top-30 JD keywords that appear in this project's description
- `outcome_strength`: 0-3 points
  - 0: no quantified data
  - 1: qualitative outcome ("shipped to production")
  - 2: quantified metric but small scope (personal project)
  - 3: quantified metric with large-scale impact (team/company/user count)

Sort by total score, mark the top 3 "lead with this".

### Lead bullet selection

The first bullet under each experience entry determines whether the recruiter keeps reading. The first bullet must:
- Satisfy XYZ-strict or Outcome-first
- Contain ≥ 2 high-frequency keywords from the target JD
- Put the number within the first third of the sentence

### Trimming thresholds

Candidates for demotion to a secondary section or deletion:

| Signal | Treatment |
|------|------|
| Skill unrelated to target direction | Delete or demote to a collapsed "Other skills" section |
| Non-differentiating experience older than 5 years (non-FAANG / non-top-tier project) | Shorten to 1-2 lines |
| Duplicate bullet of the same kind of work written under two roles | Merge into one role, delete from the other |
| Skills section has > 30 tags | Cut to ≤ 20, sorted by target direction |
| Self-promotional adjectives ("passionate", "results-driven") | Delete entirely, nobody reads them |

---

## 4. Benchmark profile pattern extraction

When the user pastes 1-3 benchmark profiles, **extract patterns, don't copy words**. Dimensions to examine:

### Headline (one line)

- Length (10-15 words is most common)
- Angle of approach: years of experience / problem solved / company + title / mission statement
- Whether it includes a number (e.g. "Built ML systems serving 100M+ users")

### Summary's first sentence

The first sentence determines the open rate. Common hook patterns:
- **Numbers hook**: "10 years building payments infrastructure for SEA fintech."
- **Problem hook**: "I help fintech companies cut payment failure rates."
- **Identity hook**: "Backend engineer specializing in idempotent distributed systems."
- **Story hook**: "Started as a self-taught dev, now leading a team of 8..."

Determine which one the benchmark used, and check which one best fits the user (based on their actual
background — don't force a fit).

### How quantified numbers are phrased

- User count / customer count / GMV
- Percentage performance improvement
- Team size / cross-team collaboration count
- Cost savings / revenue growth

Note which type of metric the benchmark used, since different roles favor different metrics.
(Product managers lean toward GMV/user count, infra engineers lean toward latency/availability.)

### Project description structure

- Length: 3-5 lines vs. one paragraph vs. one sentence
- Whether a link is included (GitHub, demo, blog)
- Whether a tech stack tag is included

### How skills are grouped

- By tech stack (Languages / Frameworks / Tools / Cloud)
- By competency domain (Backend / Distributed Systems / DevOps)
- Not grouped at all (one long list of tags)

### Output format

```markdown
## Benchmark comparison

**Benchmark**: [name or "Profile A"]
**Pattern**: [the specific pattern extracted]
**You currently**: [the user's current corresponding approach]
**Recommendation**: [a concrete change based on experience the user already has, don't invent new content]
**Rationale**: [why this pattern fits / doesn't fit the user]
```

### Strictly forbidden

- Copying the benchmark's exact sentences
- Adopting the benchmark's fabricated persona (benchmark is staff eng, you can't call yourself staff eng)
- Recommending framing the benchmark used but that the user has no experience to support

---

## 5. Report writing conventions

### TL;DR template

```
**Top gap**: [one sentence, the most critical skill/framing gap]
**Top rewrite**: [one bullet, original → rewritten]
**Top reorder**: [one section adjustment, biggest impact]
```

3 lines. Not 4.

### Action list format

Each item:
- Priority marked P0 / P1 / P2
- Estimated time (must be < 30 minutes, otherwise split it up)
- Concrete and actionable (not "improve your bullets", but "change the first bullet of the dtcpay role to
  [specific content]")

### Report length cap

- TL;DR + Skill gap table + first 5 bullet rewrites + ordering recommendations + action list
- Full text ≤ 1500 lines of markdown
- If it exceeds this, split into two: `-part1.md` for priority recommendations, `-part2.md` for secondary detail

---

## 6. Common anti-patterns (flag to the user when seen in the report)

- **"Passionate", "results-driven", "team player"** — all filler, delete
- **"Responsible for", "Worked on", "Helped with"** — no ownership signal, rewrite
- **Listing job duties instead of outcomes** — things like "Wrote APIs, did code review, attended standups"
- **Overly long summary (> 5 paragraphs)** — recruiters won't read it, cut to 2 paragraphs
- **Overusing the same verb** — using "developed" 5 times across the whole profile, vary the wording
- **Hiding a key skill at the very end** — move the target direction's core skills to the front of the skills section
- **Company nobody's heard of, with no explanation**: add a line like "(SEA fintech, 200K MAU)" for context
- **Project has no link** — GitHub / demo / blog, at least one, otherwise credibility is low
