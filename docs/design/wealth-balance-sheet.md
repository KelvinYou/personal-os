# Wealth dashboard: liabilities and readable glass surfaces

Status: Implemented; visual acceptance pending · Updated: 2026-10-04

## Context and scope

The dashboard renders gross tracked assets but does not expose recorded liabilities. Credit-card balances recorded in notes cannot participate in calculations. The change adds structured MYR liability observations, a partial balance sheet, monthly commitments, and unconverted travel wallets. It preserves gross asset history and allocation denominators.

## Ownership and data contract

Private savings.yaml owns optional liability `outstanding`, `as_of`, `statement_due`, and `payment_due_date`. An outstanding balance must be nonnegative and dated; missing means unknown, never zero. Existing installment-only records remain valid without backfill. Credit-card notes are migrated only from explicit dated user evidence. Loan principal is never inferred from installments.

Private travel-cash.yaml owns CNY wallet balances. A missing file is expected. These balances render in original currency and remain excluded from MYR totals until a supported dated FX conversion exists.

The Python report builder owns all sums and differences. Report v4 adds liabilities, balance_sheet and excluded_cash; generated JSON Schema/TypeScript and version checks update together. Gross `tracked_total_myr`, allocation and history retain their existing meanings. CLI and web render the same report.

## Rules

- Sum observed outstanding balances only; expose unknown and stale observations separately.
- If recorded debts exist but none has a balance, known debt and adjusted balance are null.
- Subtract known outstanding debt once from gross tracked assets; monthly payments are cash-flow information and are never subtracted again.
- Monthly commitment uses monthly_now when present, otherwise monthly. Null remains unknown, explicit zero remains zero.
- Adjusted tracked balance is not full net worth; loan principals, property valuations and other untracked assets may be absent.
- Travel cash is shown without an invented MYR conversion.

## Presentation

Adapt travel-plan/share-html design vocabulary: floating glass navigation, quiet opaque content surfaces, large aligned figures, restrained depth, amber missing/stale observations and readable tables. Support theme and reduced-glass controls, visible focus, reduced motion, print and small screens. Do not copy travel-specific layout or validation rules into the dashboard.

## Implementation and acceptance

1. Add dated debt observations and Python calculations; synthetic fixture tests cover unknown/zero, partial debt, stale balances and monthly commitments.
2. Extend generated report contract and CLI; migrate only confirmed private facts; show excluded travel cash.
3. Recompose the finance overview, debt section and quality summary; retain existing account/position editing.
4. Run wealth, contract, golden and finance-edit tests, generated-contract check and web typecheck. Inspect actual desktop and phone views, light/dark and reduced glass.

## Risks and decisions

Do not parse numeric prose on every load: notes are historical context, not executable balances. The observation schema is additive, while report version changes explicitly reject mismatched consumers. Financial tests use synthetic fixtures only; private balances must not enter public tests or documentation.

## Open questions

No implementation-blocking decisions remain. Outstanding loan principal, credit-card statement amount/due date and travel FX require future owner evidence; the UI marks those omissions rather than estimating them.

## Verification record

- 101 focused tests passed: wealth calculations, liability edge cases, recursive/generated report contract, CLI golden output and existing finance editing.
- Web typecheck and production build passed.
- Live HTTP/SSR acceptance matched the Python report for gross assets, known debt, partial adjusted balance, missing loan principal, CNY wallets and history labels.
- `git diff --check` and generated-report `--check` passed.
- Browser visual acceptance is blocked: no browser provider is available, and native Chrome access returned `cgWindowNotFound`. Desktop/phone screenshots, theme/material interaction and keyboard tests remain unverified. This does not establish full UI acceptance.
- Production preview is localhost-only. No merge, commit or deployment is performed.
