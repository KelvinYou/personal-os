# Finance

## Sub-features

- h1 "Financial overview", `Show amounts` / `Hide amounts` privacy toggle, "As of" date.
- `Balance overview` KPI strip: Gross tracked assets, After known debt, This month (% stays
  visible while masked), Cash yield; one scope line under it.
- `Needs attention · N` (`#attention`): renders `report.attention` from
  `scripts/lib/wealth/attention.py` (missing debt principal, deposit caps ≥ warn threshold,
  maturities, valuation observations); each item links to its tab. The Office Finance notice
  shows the first item of the same list.
- `Gross asset history` (`#history`, zoomed axis + point markers, "Monthly change breakdown"
  disclosure) beside `Asset allocation` (`#allocation`, stacked donut + table).
- `Holdings and records` tabs (`role=tablist`): Cash & savings (`#cash`: mini stats, yield bars,
  table, maturities, travel wallets), Investments (`#stocks`: P&L % bars, table), Liabilities
  (`#liabilities`), Journal (`#activity`). A URL hash or in-page link selects the tab.
- Tables are read-only until `Edit accounts` / `Edit holdings`; Actions column and Add appear only then.
- Finance workbench: funding steps, saved monthly allocations, cash scenarios and policy gaps; all calculations live in Python. Records are separate from holdings/journal.
- Spatial entry: Office town → `Finance` tab (`/office?dept=finance`); see [Office](office.md) for its asset/notices desks and durable workbench.

## How to get to it (user POV)

Top nav **Finance** → `/finance`. Server-rendered on every request: runs
`.venv/bin/python3 scripts/wealth_check.py` against private `data/finance/`.

## Driving it with drive.mjs

```bash
cd web && node ../.agents/skills/verify-web/scripts/drive.mjs --port 3041 \
  --route /finance --heading "Financial overview" --expect-text "Needs attention" \
  --expect-text "Holdings and records" --label finance
```

Proof: h1 visible, KPI strip and attention list render, amounts masked (`••••••`) in `before.png`.
Tabs: `--route "/finance#stocks"` opens Investments; `--click "Edit accounts"` is a read-only toggle (no writes).

## Gotchas

- Privacy: amounts are masked by default. Do not add `--click "Show amounts"` to a captured
  journey; assert structure and percentages instead.
- If `.venv` or `data/` is missing the page shows "Finance data could not be loaded. Run make
  wealth…" — that is the error state working, not a finance proof. `doctor.sh` reports `data/`.
- Hidden tab panels stay in the DOM with `hidden`; `--expect-text` on a non-default tab's text fails
  unless the route hash selects that tab.
- "History unavailable" / "Journal unavailable" cards are per-section error states from
  `loadActivity()`; the rest of the page can still be correct.
- Synthetic finance states (empty, error, partial) are proven on `/design-system`, not here.
