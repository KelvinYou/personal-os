# Schedule Rules Quick Reference

Coach-planner's public rules quick reference. Personal times, training day types, meal plans,
equipment, cost, and sleep baselines don't belong in this file; they must be read from private
runtime data.

## Ownership

- `data/protocol/standard_week.md`: the single human-readable owner of the standing timetable.
- `data/protocol/standard_week.yaml`: the Calendar anchors projection of the standing timetable.
- `data/user_profile.md`: personal schedule, diet, training preferences, and phase targets.
- `config/thresholds.yaml`: sleep, HRV, training, and circuit breaker thresholds.
- `data/reports/YYYY-w##-delta.md`: records only exception-week changes relative to the standing protocol.

Every scheduling pass reads `data/protocol/standard_week.md` first, then profile, daily logs, and the
weekly report. Don't infer personal baselines from this file, and don't turn this file into a second
timetable.

## Planning rules

- A standard week just executes the standing protocol; when there's no exception, don't generate a
  weekly timetable, delta, or calendar sidecar.
- Generate a dated delta only when a schedule exception, circuit breaker restriction, goal assignment,
  or one-off experiment changes actual time blocks.
- An exception week's delta must express "what changed relative to which part of the protocol" — don't
  copy the full meal plan, training table, or timetable.
- The training gate uses `config/thresholds.yaml` and the latest log evidence; when data is missing,
  preserve the uncertainty rather than guessing a baseline.
- Preserve at least the recovery interval between training end and lights-out required by the
  project's protocol/evidence; the specific time is resolved from private data.
- Training weights, exercise architecture, and day type are read only from `standard_week.md`; don't
  maintain an equipment list in the public reference.
- Meal times, portions, protein targets, and cost are resolved from `data/user_profile.md` and
  `references/nutrition-source.md` / `scripts/nutrition.py`; don't write personal values in this file.

## Google Calendar sidecar

`scripts/sync_calendar.py` has two independent modes:

- `--protocol`: reads `data/protocol/standard_week.yaml`, syncs recurring anchors.
- `--week`: reads `data/reports/YYYY-w##-calendar.yaml`, syncs dated events for one exception week.

Exception-week sidecar schema:

```yaml
week: "YYYY-W##"
timezone: "<IANA timezone>"
calendar_id: "primary" # optional; defaults to GOOGLE_CALENDAR_ID
events:
  - date: "YYYY-MM-DD"
    start: "HH:MM"
    end: "HH:MM"
    title: "Calendar event"
    description: "Optional context"
```

Sync is delete-then-insert keyed by `week`; the sidecar must be regenerated in full, never append a
single event. Weeks with no time-block change don't generate a sidecar; only write to
`data/reports/YYYY-w##-calendar.yaml` when Calendar actually needs to be published. OAuth and
permission notes are in `scripts/lib/gcal.py`.

## Weekly delta output

```markdown
# YYYY-W## Delta

> Baseline: `data/protocol/standard_week.md`

## Exceptions
- YYYY-MM-DD: which time block changed, and how it's compensated

## Constraints
- active breaker / objective / experiment
```

Present as a Draft and wait for user confirmation before saving. Only after confirmation write to
`data/reports/YYYY-w##-delta.md`; if there's no exception, state explicitly that no file is needed.

## Timetable output templates

### Daily

```markdown
## [Day] MM-DD Timetable (Draft)

> State snapshot: Sleep Xh | Energy X/10 | Breaker: [None / breaker names]

| Time | Action | Notes |
|------|------|------|
| HH:MM | Action | Details from private protocol/profile |
| ... | ... | ... |
| HH:MM | [Forced shutdown] | lights-out from private protocol/profile |
```

### Weekly delta

```markdown
## YYYY-W## Delta (Draft)

> Only write changes relative to `data/protocol/standard_week.md`.

| Date | Protocol block | Change | Reason |
|------|----------------|--------|--------|
| YYYY-MM-DD | section/time block | exception | report / user input |
```

## Training detail

When a training day is included, the schedule row should only give a summary; the detailed section
should include:

1. HRV / sleep gate: thresholds come from `config/thresholds.yaml` — don't copy the numbers.
2. Weight table: weights come from the equipment tiers in the private `standard_week.md`; when
   unchanged, reference the last confirmed protocol.
3. Each training day's exercises, sets/reps, tempo, rest between sets, execution cues, and de-load
   conditions.

If the user requests a full timetable, still read the standing protocol first, then merge profile,
daily state, weekly objectives, and temporary exceptions; the full output is an escape hatch and
should not become the weekly default.
</content>
