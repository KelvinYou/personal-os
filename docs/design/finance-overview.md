# Finance overview and activity journal

[Status: OK] Design-Lite · 2026-11-07 · Implementation in progress

## 1. Context
The owner's acceptance brief is to implement the researched finance dashboard: an overview of gross assets and monthly changes, a category donut, a time-range trend, monthly change bars, and a private transaction record. Detailed balances currently precede the charts. Existing balance snapshots do not establish investment returns.

## 2. Scope and owners
| Contract | Owner | Consumers | Compatibility / verification |
| --- | --- | --- | --- |
| Valuation and category percentages | Existing Python wealth report v4 | Overview and allocation chart | Unchanged; wealth contract gates |
| Monthly asset deltas | Python activity projection over history.csv | Header, trend, monthly bars and table | Moves prior frontend calculation to Python; synthetic sparse-month tests |
| Confirmed transaction evidence | Private transactions.jsonl; strict Python model | CLI append/read, activity journal | Optional file; missing is explicit; no migration or inferred backfill |
| Activity JSON | Python ActivityReport serialization schema | Generated TypeScript and runtime loader | Separate schema v1; existing wealth and history output unchanged |

## 4. Design
Page order: gross assets and monthly change → freshness / coverage → allocation → trend and monthly change → accounts, investments, liabilities, maturities and journal. Reuse SectionCard, Stat, Money/Private, Button, Select and the existing line chart. The donut has fixed category colours plus a readable amount/percentage list; more than five nonzero categories retain a bar presentation.

A journal entry has a stable id, recorded date, optional actual date, kind, positive original-currency amount, account, description, and optional counter-account or security/quantity/fees. Unknown dates and fees remain null. Transfers require two distinct accounts; purchases and sales require a security and quantity. A repeated id with identical facts is a no-op; a conflicting id is rejected. Appends are locked and flushed. Malformed records fail visibly instead of disappearing.

## Business rules
- Holdings YAML remains the owner of balances. Journal writes never mutate holdings or history, preventing double subtraction after a corrected balance.
- Positive amounts carry their meaning through kind: income, expense, deposit, withdrawal, transfer, buy or sell. Transfers/trades do not constitute external investment return.
- Do not infer missing trades, dates, foreign-exchange conversions, completed repayments or complete cash-flow coverage.
- Monthly change = this month's last observed gross assets minus the immediately preceding month's last observed gross assets. Missing prior months yield null; a zero baseline yields a null percentage. Dates expose partial months.
- Journal coverage is always presented as partial in v1. TWR, IRR and attributed market gains are unavailable until complete, dated cash flows and valuation evidence exist.
- Private values remain under data/finance; public fixtures, screenshots and tests use synthetic values only.

## 7. Trade-offs
A small append-only evidence journal is useful immediately without pretending to be a reconciled double-entry ledger. It has no automatic balance posting, no return computation and no historical completeness claim. A new financial API write surface is unnecessary: the existing agent and a stdin CLI provide entry; the dashboard reads the evidence.

## 8. Verification and failure handling
Python tests cover sparse history, zero baselines, positive and negative deltas, journal validation, duplicate/conflicting ids and malformed files. Generated schema/type checking guards the language boundary. Browser tests replay range selection, privacy, category labels and mobile layout using catalog fixtures. `make test` and `make design-check` remain required. Activity load failure renders an error while existing asset valuations stay usable. Missing history or journal renders an empty state, never a zero investment return.

## 9. Decisions
No pending product decisions. The user's instruction authorizes implementation. No commits, external publication or historical balance rewrites are part of this change.

## Transaction entry

Copy `templates/finance-transaction.example.json` to a private location, replace its synthetic facts and stable unique id, and submit:

```sh
.venv/bin/python scripts/finance_activity.py add < data/finance/event.json
```

The CLI fills `recorded_on` from the owner's timezone. Supply `occurred_on` only when the actual date is known. For a `buy` or `sell`, include `symbol`, `quantity`, and optional `fees`; `amount` is gross trade consideration in the original currency, with fees separately recorded. A same-currency `transfer` requires `counter_account`; foreign-exchange legs need independently confirmed amounts rather than an assumed conversion. Deposit and withdrawal represent crossings of the tracked asset boundary; income and expenses describe external earnings/spending. Transfer, buy and sell describe movements inside it. Do not duplicate one economic event under multiple kinds.

The append command accepts one JSON object and returns `{"ok":true,"inserted":true}`. Replaying the same id and same facts returns `inserted:false`; a conflicting id, invalid record or malformed journal returns a nonzero exit and `ok:false`. No API write endpoint is added. The activity reader returns schema v1 with observed history, Python-derived monthly rows, current-month summary, priced-stock allocation and original-currency journal entries. Generated owners are `web/lib/activity.schema.json` and `activity.gen.ts`; regenerate with `scripts/export_finance_activity_schema.py`.

Stock allocation uses `wealth.stocks.total_myr` as its denominator and existing position market values as its numerator. It is a separate ranked-bar view, never the gross-assets donut. Unpriced symbols remain visible as incomplete coverage.
