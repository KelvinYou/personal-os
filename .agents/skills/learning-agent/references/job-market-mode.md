# Job Market Mode — Detailed Workflow

This document is the execution guide for the **job-market** and **hybrid** modes
of the learning-agent skill. It is loaded only when the user's query touches real
hiring-market signals (hiring demand / JD / salary / specific role scans) rather than
pure trend research.

## Why this mode exists

Tech blogs and Twitter tell you what's *exciting*. Job postings tell you what
employers will actually *pay for*. The two often disagree — a framework can be
buzzing online for a year before it shows up in production-ready JDs, and some
skills stay in high demand long after they stop being fashionable to write about.

For the MY/SG market specifically, most trend-research sources are US-centric,
so web-only trend reports tend to mislead when applied here. Real listings from
JobStreet / LinkedIn MY-SG / Indeed SG give us local ground truth.

## Data sources and their tradeoffs

Read this before picking what to run.

| Source | Coverage | Legal/ToS | Reliability | Preferred use |
|--------|----------|-----------|-------------|---------------|
| LinkedIn (via JobSpy) | MY + SG | Grey; aggressive rate-limit | Medium — may 429 | Senior/specialist roles, tech companies |
| Indeed (via JobSpy) | MY + SG | Grey; tolerant at low volume | Good | Broadest coverage, default first pick |
| Google Jobs (via JobSpy) | MY + SG | Public aggregator | Good | Fills gaps, de-dupes with care |
| Glassdoor (via JobSpy) | MY + SG | Grey; strict CF bot wall | Flaky | Skip unless salary data is the ask |
| JobStreet (custom) | MY + SG | Scraping undocumented internal API | Fragile — may break silently | MY-specific roles, where JobStreet dominates |
| Adzuna API | **SG only** | Official, free tier | High | SG salary ground truth, legal-safe |

**Default recipe** for a general SWE scan of MY + SG: Indeed + LinkedIn + Google
via JobSpy (one call per country), plus JobStreet MY (since Adzuna doesn't cover
MY). Cap at 30 results per source to stay under rate-limit thresholds.

## Workflow

### Step 0 — Read user context
Same as trend-research mode. Load `data/user_profile.md` and the last 3-5 daily logs
so the final report is phrased against the user's actual trajectory rather than
a generic SWE profile.

### Step 1 — Decide scope
Parse the user's query for:
- **Role** (e.g. "Senior SWE", "AI engineer", "Staff engineer") — defaults to the
  user's current role if not specified. If the user hints at a pivot ("want to move to",
  "want to go into"), use the pivot target.
- **Location** (MY, SG, or both) — default both.
- **Archive freshness** — if `market/jobs/raw/` already has a file from today
  matching the query, skip fetching (the scripts enforce this automatically).

If the query is ambiguous (e.g. "check the market"), propose a scope and confirm with
one sentence before running scrapers. The scrapers take 1-3 minutes and
we don't want to burn rate-limit budget on the wrong search.

### Step 2 — Fetch
Run the scraper scripts. Typical invocation pattern:

```bash
# Per-country run so each JSON file has one location tag.
python scripts/fetch_jobs.py \
  --query "software engineer" \
  --location Singapore \
  --sources linkedin,indeed,google \
  --limit 30 \
  --output market/jobs/raw/2026-04-24_sg_swe.json

python scripts/fetch_jobs.py \
  --query "software engineer" \
  --location Malaysia \
  --sources linkedin,indeed,google \
  --limit 30 \
  --output market/jobs/raw/2026-04-24_my_swe.json

python scripts/fetch_jobstreet.py \
  --query "software engineer" --country my --limit 30 \
  --output market/jobs/raw/2026-04-24_jobstreet_my.json
```

**If a scraper exits non-zero**, do not retry automatically — report the error
to the user so they can decide whether to install the missing dep, accept the
narrower dataset, or upgrade a broken scraper. JobStreet's API in particular is
undocumented and will eventually change; "fail loud" is the right behavior.

### Step 3 — Extract skills (batched LLM call)
Each raw JSON has `jobs[].skills_extracted: null`. Fill it in with a single
batched call rather than per-job calls. Budget: one call per ~50 jobs.

Batch prompt template:

> You are extracting skill keywords from job descriptions. For each job below,
> output a JSON object mapping `job_id` to an array of 3-8 concrete skill
> tokens. Only include skills that are genuinely required or strongly
> preferred — ignore generic phrases ("good communicator", "team player",
> "problem solver"). Prefer specific tech (Python, Kubernetes, PostgreSQL)
> over categories (backend, cloud). Normalize casing to lowercase. Return
> only valid JSON, no commentary.
>
> Jobs:
> [{"job_id": "...", "title": "...", "description": "..."}, ...]

After the call, read the JSON response and write `skills_extracted` back into
each job record, then save the file. Now the file is "enriched" and
aggregate_skills.py will include it.

**Cost-awareness:** if jobs >100 across all files, split into two LLM calls
rather than one giant prompt. Keep each call under ~25k input tokens.

### Step 4 — Aggregate
```bash
python scripts/aggregate_skills.py \
  --archive-dir market/jobs/raw \
  --output market/jobs/trends.json
```

Reads every enriched file ever written (archive grows over time), produces
`market/jobs/trends.json` with:
- `top_overall` — all-time frequency ranking
- `top_by_location` — MY vs SG breakdown
- `top_by_source` — which board demands which skills
- `deltas` — recent vs prior window, tagged `emerging` / `fading`

Early runs have no delta signal (no prior data). That's fine — just note it in
the report. Deltas become interpretable after 2+ months of archived runs.

### Step 5 — Write the report

Output structure for **job-market mode**:

```markdown
# Job Market Scan — [YYYY-MM-DD]

## TL;DR
> One sentence: the 3 skills most repeatedly required for [role] roles in MY/SG are X/Y/Z, and the [emerging/fading] signal is …

## Data inventory
- Scan scope: [sources] × [locations]
- Sample size: N JDs (filter: posted in the past 7 days)
- Data gaps: [any source that failed, any location that's underrepresented]

## 🔥 Top 15 high-frequency skills
| Rank | Skill | Occurrences | Coverage | Notes |
|------|-------|---------|--------|------|
| 1 | ... | ... | N/total | (optional: which seniority levels it appears most in) |

## 📍 MY vs SG comparison
[2-column table or side-by-side list, highlighting differences]

## 📈 Emerging vs fading (if delta data exists)
- 🆕 Emerging: [skill] (+X%)
- 📉 Fading: [skill] (-Y%)

## 💰 Salary bands (if salary fields were captured)
[Salary range by role/level; note data source and sample size]

## 🎯 Recommendations for you
Based on user_profile and recent daily logs:
- High-demand skills you already have: [...]
- Skills you're missing that appear frequently in the top 10: [...]
- Window recommendation: [what has the highest ROI to learn right now]
```

**Hybrid mode** additionally runs the trend-research pass (`references/trend-research-mode.md`
workflow) and includes a final section called `## 🔀 Cross-validation` — where market
signal agrees with web trends, it's a strong buy; where they disagree, note
which side the user should weight and why (e.g., "blog chatter on Rust is hot
but MY/SG JDs show only 3 mentions in 100 samples — keep on watchlist, don't
prioritize").

## When to skip fetching entirely

If `market/jobs/trends.json` exists and was regenerated within the last 48 hours,
and the user's query doesn't demand fresh data (e.g., "summarize what we know"
rather than "scan again"), you can produce the report from the existing digest
alone. Note this in the TL;DR: "(data is from the YYYY-MM-DD cache, not re-fetched)".

## Failure modes to flag honestly

- **LinkedIn returns empty**: likely rate-limited. Report "LinkedIn returned no
  data, using only Indeed/JobStreet samples." Don't pretend the dataset is complete.
- **JobStreet script returns non-zero**: API schema changed. Tell the user the scraper
  needs upgrading, run analysis on what's available, and flag MY data as
  potentially under-sampled.
- **skills_extracted is empty**: LLM extraction failed or returned malformed JSON.
  Re-run extraction once; if still broken, report without the skill aggregation
  and ask the user whether to retry.
