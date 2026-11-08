# Agent signals

## Sub-features

- h1 "Agent Signals": monthly rollup of `make eval` session signals.
- `Signal 趋势` chart and `月度明细` monthly table; a signal firing in over half a month's
  sessions is the AGENTS.md-bug threshold.
- `纠错复发` table: per month, corrections logged, repeats (an earlier entry used the same
  `**Class:**`), repeat rate and the repeating classes. Source: `session_eval.py --corrections --json`
  over `reports/corrections/`. Independent of eval sessions, so it has rows even when evals don't.

## How to get to it (user POV)

Top nav **Agent signals** → `/eval-rollup`. Numbers come from
`scripts/session_eval.py --rollup-history`; the page does not recompute them.

## Driving it with drive.mjs

```bash
cd web && node ../.agents/skills/verify-web/scripts/drive.mjs --port 3041 \
  --route /eval-rollup --heading "Agent Signals" --expect-text "纠错复发" --full --label agent-signals
```

Add `--width 320` and `--dark` runs for layout changes; the corrections table must scroll inside
its `纠错复发明细` region at 320px (drive.mjs fails on page-level horizontal scroll).

## Gotchas

- Empty history (no `reports/evals/` records yet) is a valid empty state, not a failure; check
  `after.png` to tell which state rendered.
- Changing eval logic needs `make eval-rollup` before driving, or the page shows old numbers.
- The corrections table is read live on every request; an entry without `**Class:**` is listed
  as unclassified and lowers the repeat count, not raises it.
- The section is below the fold: without `--full`, `after.png` does not show it.
