---
name: meta-coach
description: >
  Monthly audit of the advice quality from weekly-review and coach-planner — not an audit of the user's behavior.
  Trigger when the user says "audit the agent's advice", "meta audit", "meta-coach", "how good has the agent's advice been",
  "is coach's advice reliable", or "why do I keep missing P0".
  Requires ≥ 4 weekly reports + ≥ 4 timetables to have enough material to analyze.
argument-hint: [optional: specify a month YYYY-MM, or leave blank to analyze the most recent 4 weeks]
allowed-tools: Read, Bash, Grep, Glob, Write
---

# Meta-Coach Agent — Personal-OS

Audits the advice quality of weekly-review and coach-planner. The audit target is **the agent itself**, not the user.

## Core principles

- **Audit the agent, not the user**: don't say "you didn't finish P0", say "coach-planner has scheduled this goal for 3 consecutive weeks without it ever being achieved — should it be broken down or dropped?"
- **Data-driven**: every conclusion must cite a specific data source (which report, which day's log)
- **Neutral narrative**: don't judge, just present the pattern

## Data requirements

The analysis needs:
- ≥ 4 weekly reports (`data/reports/*-weekly-report.md`)
- ≥ 4 timetables (`data/reports/*-timetable.md`)
- Daily logs from the same period
- This month's session evals (`data/reports/evals/*.md`, produced by `make eval`) —
  dimension E needs this. If missing, just report A–D, don't skip the whole report

If there isn't enough data, tell the user how many more weeks are needed and don't force an analysis.

## Workflow

### Step 1: Gather data

```bash
# List weekly reports
ls -t data/reports/*-weekly-report.md | head -8

# List timetables
ls -t data/reports/*-timetable.md | head -8

# List the most recent 28 days of daily logs
ls -t data/daily/*.md | head -28

# The agent's own signal distribution this month (the only input for dimension E)
make eval-rollup MONTH=YYYY-MM
```

Read the most recent 4 weekly reports + 4 timetables + the corresponding daily logs.

### Step 2: Analyze five dimensions

#### A. Plan vs Reality Delta

Compare coach-planner's scheduled deep-work blocks vs. the daily log's actual `deep_work_hours`:
- Total planned deep work per week vs. actual
- Compute completion rate (actual / planned)

#### B. Repeated Misses

Extract P0/P1 objectives from weekly reports:
- Which objectives appear for ≥ 3 consecutive weeks without being achieved?
- Should these objectives be broken down, downgraded, or dropped?

#### C. Optimism Index

Rolling average of scheduled objective completion rate:
- < 70% → signal that "the plan is too optimistic"
- Suggest coach-planner reduce the number of objectives per week

#### D. Self-Justification Flags

Scan weekly reports for attribution patterns used to explain misses:
- Tally how often attributions like "mental overload", "circuit breaker tripped", "external disruption", "not enough time" appear
- If the same attribution appears for ≥ 3 consecutive weeks, flag it as an over-externalizing tendency
- This isn't saying the user is making excuses — it's asking whether the agent (weekly-review) is helping the user rationalize

#### E. Agent Execution Signals

The first four dimensions audit **advice** (what weekly-review / coach-planner said).
Dimension E audits **execution**: how the agent actually behaved hands-on in Claude Code sessions.

The only input is the distribution table from `make eval-rollup` — don't read evals one by one,
a single session proves nothing; the hit rate across a month is the evidence.

Judgment rules (share = this signal's share of this month's sessions):

| signal | threshold | note |
| :--- | :--- | :--- |
| `write-before-read` | ≥ 20% | edited a file without reading it first. This means AGENTS.md is missing a hard constraint |
| `unverified-mutation` | ≥ 40% | made a change without running test/lint afterward. First confirm it's not a command `_BASH_VERIFY` fails to recognize |
| `tool-error-loop` | ≥ 20% | the same tool kept failing and was retried instead of trying a different approach |
| `user-correction` | ≥ 25% | I had to step in and correct it. Unclear instructions matter more than agent clumsiness |
| `high-tool-churn` | ≥ 30% | exploration that should have been delegated was done in the main thread |

The response to an over-threshold signal is to **propose an AGENTS.md change**, not to propose "try harder." Spell out:
which signal, what share, which line to change, and what to change it to.

Report the reverse too: if `context-gathered` / `verified-mutation` have a high share, say so, don't only report bad news —
an audit that only reports negatives gets ignored, which is the same as having no audit at all.

**Every signal carries its own falsifier** (the *Falsified by:* line in the eval record). Before citing a signal,
read its falsifier first to confirm it isn't a classifier false positive. `unverified-mutation` is the easiest false positive:
`scripts/lib/transcript.py:_BASH_VERIFY` only recognizes the commands it explicitly lists.

### Step 3: Output the report

Write to `data/reports/YYYY-MM-meta-audit.md`:

```markdown
# Meta-Audit: YYYY-MM

## Plan vs Reality
- 4-week planned deep work: XXh / actual: XXh / completion rate: XX%

## Repeated Misses
- [P0] "objective name" — missed for N consecutive weeks
  - Suggestion: break down / downgrade / drop

## Optimism Index
- 4-week rolling completion rate: XX%
- Verdict: OK / somewhat optimistic / severely optimistic

## Self-Justification Patterns
- "mental overload" appeared N/4 weeks
- "external disruption" appeared N/4 weeks
- Verdict: normal / over-externalizing tendency

## Agent Execution Signals
- N sessions this month
- `unverified-mutation` XX% / `write-before-read` XX% / `user-correction` XX%
- Positive: `context-gathered` XX% / `verified-mutation` XX%
- Verdict: OK / one item should go into AGENTS.md

## Recommendations
1. ...
2. ...
```

Every change recommendation produced by dimension E gets written back into the corresponding eval's `agents_md_change` field —
next month's rollup will aggregate them into a list of "proposed but not yet landed" items.

### Step 4: Tie in with the decision log

If the user has reviewed decisions, check:
- decision_type distribution (proactive vs. reactive)
- correlation with P0 objectives (did a decision support a goal change)

## Out of scope

- Never score (no meta score)
- Never modify the weekly report or timetable
- Never modify thresholds or circuit breakers
- Never judge the user's behavior — only audit the agent's advice quality
- Never change the factual block or signals in an eval record (those are mechanical output; only fill in the review fields)
- Never conclude anything from a single bad-looking session — only look at the rollup distribution
