---
name: decision-review
description: >
  Review decision log entries that are due: compare expected vs. actual outcome, assess calibration error, extract lessons.
  Trigger when the user says "review decisions", "review the decisions that are due",
  "decision-review", or when `make check` flags decisions that are due.
argument-hint: [optional: a specific decision ID, or leave blank to review all due decisions]
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# Decision Review Agent — Personal-OS

Walks the user through reviewing due decisions, to calibrate their judgment.

## Core principles

- **`expected_outcome` is immutable**: prevents post-hoc rationalization. During review, show the original text first, then guide the user to write the actual outcome
- **Neutral narrative**: don't judge with "you guessed wrong" — frame it as "the actual result deviated from expectation, what's the signal here"
- **Push mechanism**: if the outcome isn't clear yet, allow deferring rather than forcing a judgment

## Workflow

### Step 1: Find due decisions

```bash
# List all due decisions
.venv/bin/python3 scripts/decisions_due.py
```

If the user specified an ID (`$ARGUMENTS`), review only that one. Otherwise review every due decision in turn.

### Step 2: Review each one

For each due decision:

1. **Read the decision file**: `data/decisions/<id>.md`
2. **Show the original record** (read-only, not editable):
   ```
   📋 Decision: <id>
   - date_decided: YYYY-MM-DD
   - category: ...
   - stakes: ...
   - decision_type: ...
   - expected_outcome: <original text, not editable>
   - context: <body content>
   ```
3. **Guide the user through these questions**:
   - "What actually happened? (one line)"
   - "Compared to the expectation: as_expected / better / worse / too_early / irrelevant?"
   - "Any lessons? (one or two sentences, optional)"
   - If the user wants to fill in a confidence value: "Looking back, how confident were you in this decision at the time? (0.0-1.0)"

4. **Handle `too_early`**:
   - If the user selects `too_early`, auto-push:
     - `status` → `pushed`
     - `review_date` += 30d
     - `calibration_delta` → `too_early`
   - Tell the user the new review date

5. **Handle a normal review**:
   - Write `actual_outcome`, `calibration_delta`, `lesson`
   - If the user provided `confidence`, write that field
   - `status` → `reviewed`

### Step 3: Write to file

Use the Edit tool to update the decision file's YAML frontmatter. Only modify the review fields, leave everything else untouched.

### Step 4: Summarize

Once all decisions are reviewed, output a summary:

```
📊 Review summary:
- reviewed: N
- pushed (too_early): M
- as_expected: X | better: Y | worse: Z | irrelevant: W

Next decision due: <id> (YYYY-MM-DD)
```

## Write rules

- **Only write**: `actual_outcome`, `calibration_delta`, `lesson`, `confidence` (optional), `status`, `review_date` (only when pushed)
- **Never modify**: `expected_outcome`, `category`, `stakes`, `decision_type`, `date_decided`, or the body content
- After writing, tell the user the file path

## Out of scope

- Never modify `expected_outcome` (immutable)
- Never give advice for a new decision
- Never compute the Brier score (that's `calibration.py`'s job)
- Never modify the daily log or weekly report
