---
name: decision-log
description: >
  Capture non-trivial decisions into the Personal-OS decision log, supporting a quick one-line brain dump or an interactive walkthrough.
  Trigger when the user says "log that I decided...", "help me log a decision", "log this decision", "I decided to...",
  "decision-log", or any scenario where the user clearly expresses that they made an important trade-off/choice.
  Does not give decision advice (that's coach-planner's job) — only records decisions.
argument-hint: [one-line description of your decision, or leave blank to enter interactive mode]
allowed-tools: Read, Write, Bash, Grep, Glob
---

# Decision Log Agent — Personal-OS

Captures the user's non-trivial decisions, writing them as structured entries into `data/decisions/YYYY-MM-DD-<slug>.md`.

## Core principles

- **< 30 second capture**: the user gives a one-line brain dump, you infer all enum fields, the user only corrects
- **Recording only, no advice**: decision support is `/coach-planner`'s job — this skill only records after the fact
- **stakes ≥ medium**: don't log trivial things (choosing chicken vs salmon doesn't count). high = changes ≥ 1 year of trajectory, medium = affects ≥ 1 month
- **Write in English**, technical terms as usual, consistent with other skills

## Workflow

### Mode A: Quick brain-dump capture (when $ARGUMENTS is present)

Input: `$ARGUMENTS`

1. **Read the schema**: read `templates/decision.md` to get the field structure
2. **Infer fields** from the brain dump:
   - `category`: career | finance | health | relationship | project | tooling
   - `stakes`: medium | high
   - `reversibility`: easy | costly | irreversible
   - `decision_type`: proactive (self-initiated) | reactive (forced response) | default (chose to keep status quo)
   - `expected_outcome`: distill a one-line, falsifiable expected result from the brain dump
   - `slug`: generate a short English slug from the content (kebab-case, ≤ 4 words)
3. **Show the inferred result** and let the user confirm or correct it:
   ```
   📋 Decision captured:
   - slug: cancel-gym-membership
   - category: health
   - stakes: medium
   - reversibility: costly
   - decision_type: proactive
   - expected_outcome: Stick to home dumbbell training 3x/week, body fat ≤ 15% after 6 months
   - review_date: YYYY-MM-DD (+30d)

   Anything to change? If not I'll write it now.
   ```
4. **Once the user confirms**, generate the file and write it to `data/decisions/YYYY-MM-DD-<slug>.md`
5. Tell the user the file location and review date

### Mode B: Interactive walkthrough (when $ARGUMENTS is absent)

Walk the user through step by step:

1. "What decision did you make? Describe it in one line."
2. Infer category / stakes / reversibility / decision_type from the description, show it for confirmation
3. "What outcome do you expect? (one line, as specific as possible, ideally verifiable after 30 days)"
4. "Any context you want to add? (options considered, concerns, assumptions — write as much or as little as you like, or skip it)"
5. Generate the file, tell the user the location

## Write rules

### File path
`data/decisions/YYYY-MM-DD-<slug>.md`, where the date is `date_decided` (today) and the slug is generated from the content.

### YAML frontmatter
- `id`: `YYYY-MM-DD-<slug>`, matching the filename
- `date_decided`: today's date
- `review_date`: `date_decided + 30d`
- `status`: `open`
- `actual_outcome` / `calibration_delta` / `lesson`: leave blank (filled in by `/decision-review`)

### Markdown body
Free text. Write it if the user gave context, otherwise just a heading. No forced sectioning.

## Output requirements

- Strictly follow the field structure of `templates/decision.md`
- After writing, print the file path and review date
- If a file with the same name already exists, prompt the user to change the slug or confirm overwrite

## Out of scope

- Never give decision advice ("you should choose A")
- Never log a trivial decision with stakes = low
- Never modify `actual_outcome` / `calibration_delta` / `lesson` (that's `/decision-review`'s job)
- Never read or modify the daily log
