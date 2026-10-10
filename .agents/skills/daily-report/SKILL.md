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

### Core principle: record only observed facts

**If the brain dump doesn't mention a field, leave it blank — don't infer it, don't backfill it, don't make something up just to "fill it in".**

Blank means unknown. An explicit zero means the owner observed zero. Never
invent an observation from silence or a routine schedule.

### YAML metadata

Only fill a field when the brain dump **actually mentions** it:

- `energy_level`: (1-10) fill only if the user described energy; otherwise unknown.
- `deep_work_hours`: fill only when the user gave a duration, including an explicit zero.
- `mental_load`: (1-7) fill only if the user described stress.
- `caffeine_cutoff`: (HH:MM) record any stated last caffeine time; compare with `data/config/thresholds.yaml` at review time.
- `adherence.timetable`: record ✅, ⚠️, or 🔴 only when the user says how the plan went; add
  `deviation_note` for ⚠️ or 🔴. Unmentioned adherence remains unknown.
- `primary_blocker`: **only write a line when there was an actual incident that day**. Everyday griping (tired, slept badly) doesn't count —
  that belongs in subjective observations or an on-demand COROS query. Writing it here would make the archive script mistakenly treat it as an event day whose original text must be preserved
- `daily_spend`: itemize actual spending when supplied. A confirmed zero may be recorded as an explicit zero entry.
- `body.*`: fill only measured fields, including a weight-only measurement.
- `sleep.*` / `readiness.*` / `training.*` / `activities[]`: official COROS MCP is
  the live source; follow `docs/design/coros-official-mcp.md`. Do not copy MCP
  results into daily logs by default or overwrite historical health blocks.
  Record owner-supplied measurements only when explicitly provided for logging.

### Markdown body

**By default, leave the whole body blank.** Only the following is worth writing:

- **Today's core output (highlights)**: write it only if something was actually shipped that day, covering both company and personal projects
- **Blockers and disruptions**: only real incidents, not everyday fatigue
- Root cause for plan deviation (when `adherence` is ⚠️/🔴)

An uneventful day means an empty body — manual frontmatter supplies personal context; weekly-review queries official COROS MCP separately.

## Handling missing data

**Do not raise a warning just because a field is blank.** Keep missing observations unknown.

Only flag a gap needed for the requested assessment, and only flag it once:

- Missing sleep measurements → flag once if they are needed for the requested assessment;
  use the official COROS connector only when the owner uses COROS and an assessment is requested.
  Missing connector access does not prevent writing a manual daily log.
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
