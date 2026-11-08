# Finance

## Sub-features

- h1 "Financial overview", `Show amounts` / `Hide amounts` privacy toggle, "As of" date.
- `Balance overview`: gross tracked assets (before debt), this-month change and %, after known debt.
- Debt-coverage warning card when loan principal is missing.
- `Finance sections` anchor nav: Activity, Liabilities, Cash & savings, Investments,
  Allocation, History.
- Section cards: Asset allocation, Gross asset history, Travel wallets (non-MYR), Cash & savings,
  Investments, Liabilities & payments, Upcoming maturities, Transaction journal.

## How to get to it (user POV)

Top nav **Finance** → `/finance`. Server-rendered on every request: runs
`.venv/bin/python3 scripts/wealth_check.py` against private `data/finance/`.

## Driving it with drive.mjs

```bash
cd web && node ../.agents/skills/verify-web/scripts/drive.mjs --port 3041 \
  --route /finance --heading "Financial overview" --expect-text "Asset allocation" --label finance
```

Proof: h1 visible, section cards render, amounts masked (`••••••`) in `before.png`.

## Gotchas

- Privacy: amounts are masked by default. Do not add `--click "Show amounts"` to a captured
  journey; assert structure and percentages instead.
- If `.venv` or `data/` is missing the page shows "Finance data could not be loaded. Run make
  wealth…" — that is the error state working, not a finance proof. `doctor.sh` reports `data/`.
- "History unavailable" / "Journal unavailable" cards are per-section error states from
  `loadActivity()`; the rest of the page can still be correct.
- Synthetic finance states (empty, error, partial) are proven on `/design-system`, not here.
