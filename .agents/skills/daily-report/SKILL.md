---
name: daily-report
description: Turn the user's brain dump (free-form natural-language notes) into a structured daily review log that conforms to Personal-OS conventions. Use when the user describes what they did today, how much they spent, their sleep, etc.
argument-hint: [brain-dump text]
allowed-tools: Read, Write, Grep, Glob
---

## Role: Daily Report Agent

Turn the user's free-form brain dump into a structured Personal-OS log.

## Workflow

1. **Read the template**: first read `templates/daily.md` to get the latest YAML field structure.
2. **Read the user profile**: read `data/user_profile.md` to understand the user's schedule/dietary preferences, to help with judgment calls.
3. **Read grocery unit prices**: query `python3 scripts/nutrition.py food <id>` (backed by `repos/notes/datasets/nutrition/`, the single owner of food macros/prices), to estimate home-cooking cost.
4. **Extract metadata**: extract all YAML fields from the brain dump.
5. **Generate the log**: output a complete log file that conforms to the spec.

## Brain dump input

$ARGUMENTS

## Extraction rules

### Core principle: log only exceptions

**If the brain dump doesn't mention a field, leave it blank — don't infer it, don't backfill it, don't make something up just to "fill it in".**

Blank = fall back to the `logging_defaults` baseline in `config/thresholds.yaml`; scoring auto-covers it with no penalty.
This is deliberate design, not missing data. The actual failure mode runs the other way: the 2026-08-09 log got backfilled with
`deep_work_hours: 0` + `adherence: ✅`, guessed by the agent — that both polluted the dataset and contradicted the baseline rule itself.
**A guessed value is far more harmful than a blank one** — a blank value tells the system to fall back to baseline; a guessed value gets treated as a real measurement.

### YAML metadata

Only fill a field when the brain dump **actually mentions** it:

- `energy_level`: (1-10) only score it if the user described energy/mood. Not mentioned → leave blank (baseline 7)
- `deep_work_hours`: (float) only fill if the user gave an explicit duration. Not mentioned → leave blank (baseline: 8 on workdays / 0 on weekends)
- `mental_load`: (1-7) only fill if the user described stress. Not mentioned → leave blank (baseline 3)
- `caffeine_cutoff`: (HH:MM) **only fill if it's after 14:00**. Normal / not mentioned → leave blank (baseline 14:00, compliant)
- `adherence.timetable`: **only fill when it deviates from `data/protocol/standard_week.md`** ⚠️ or 🔴, and add a
  `deviation_note` line with the root cause. Followed the plan or not mentioned → leave blank (baseline ✅)
- `primary_blocker`: **only write a line when there was an actual incident that day**. Everyday griping (tired, slept badly) doesn't count —
  that's already captured in COROS data. Writing it here would make the archive script mistakenly treat it as an event day whose original text must be preserved
- `daily_spend`: **only itemize when there was eating out / extra spend**. A fully home-cooked day is left blank (baseline RM24.13/day, sourced from
  `data/protocol/standard_week.md` §7 grocery list). If there was eating out, estimate the home-cooked portion too, using unit prices
- `body.*`: fill only if the user provided actual measurements, otherwise leave blank. **Never falls back to a baseline** — no measurement means no data
- `sleep.*` / `readiness.*` / `training.*` / `activities[]`: **auto-filled by COROS** (`make sync-coros`),
  the brain dump doesn't need to touch these; don't overwrite existing values already in the file. Also never falls back to a baseline

### Markdown body

**By default, leave the whole body blank.** Only the following is worth writing:

- **Today's core output (highlights)**: write it only if something was actually shipped that day, covering both company and personal projects
- **Blockers and disruptions**: only real incidents, not everyday fatigue
- Root cause for plan deviation (when `adherence` is ⚠️/🔴)

An uneventful day means an empty body — COROS + frontmatter already contain everything weekly-review needs.

## Handling missing data

**Do not raise a warning just because a field is blank.** Blank is the expected state; `logging_defaults` covers it.

The old version used to append `[Status: Warning] No relevant data detected today, manual entry recommended` at the end of the log — that line
has been removed. It turned "a day executed on baseline" into a to-do item, which is exactly the kind of noise this system is meant to eliminate.

Only flag a gap that truly cannot fall back to a baseline, and only flag it once:

- Missing COROS data (`sleep.duration` is empty) → `[Status: Warning] COROS not synced, run make sync-coros`
- The user clearly mentioned a value but you couldn't parse it → ask the user directly, don't guess

## Output requirements

- Strictly follow the field structure of `templates/daily.md`; never fabricate data
- Use today's date
- Write the complete log to `data/daily/{YYYY-MM-DD}.md`
- If a file for that date already exists, read the existing content first and merge rather than overwrite
- Write in English

## Decision-detection hook

After processing the brain dump, scan the content for signals of a non-trivial decision ("decided...", "I decided...", an explicit trade-off/choice, dropping A in favor of B). If detected, append a prompt at the end of the log output:

```
💡 Possible decision detected: `<one-line summary>`. Log it in the decision log? → `/decision-log <summary>`
```

Only prompt — never auto-write the decision file. The user can copy-paste to trigger `/decision-log`.
