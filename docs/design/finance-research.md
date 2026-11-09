# Finance research desk: Finance manager proposals (design-lite)

[Status: OK] Phase 1 implemented · 2026-11-09

## 1. Outcome

The owner wants a Finance manager who does the research and hands over a proposal to
review. The Content Lab works the same way: the owner asks and reviews, and the agent
does the work in between.

The first proposal kind is `rent_vs_buy`. It compares buying a KL condo to live in
against renting a room and investing the same money in a global ETF, over years 0–20.

## 2. Ownership

| Layer | Owner | Invariant |
|---|---|---|
| Market rules (stamp duty, legal fees, RPGT, exemption cap) | `config/research/kl_rent_vs_buy.yaml` `rules` | Public; each source has `verified_at`. After `fresh_days` the desk shows a stale warning. |
| Sourced starting inputs | same file, `reference` | Read by the agent only; no code consumes it. |
| Projection math | `scripts/lib/wealth/research.py::project` | The only place numbers are made. Python owns valuation logic (ARCHITECTURE §10). |
| Proposal (inputs, reasons, prose) | Finance manager (`wealth-manager` skill) → private `data/finance/research/<id>.yaml` | Validated by `scripts/finance_research.py validate`. The prose is bound to `inputs_fingerprint`. |
| Owner review | `data/finance/research/reviews.jsonl` | Append-only. Bound to the fingerprint; a changed proposal re-opens review (409 for stale reviews). |
| Web contract | `scripts/export_finance_research_schema.py` → `web/lib/finance-research*.{schema.json,gen.ts}` | Drift check runs in `tests/test_finance_research.py`. |
| UI | `web/components/finance/research-board.tsx`, Finance `research` station | Amounts are masked by default. What-if inputs are hidden while amounts are hidden. |

## 3. Model

The model simulates month by month. Both paths start with the same capital: the
buyer's day-one cash (down payment, transfer and loan stamp duty, legal fees with
service tax, other costs, renovation). The renter invests all of it at month 0.

Each month both paths spend the same on housing, the larger of the owner's all-in
cost and the rent. The cheaper path invests the difference in the ETF. The all-in
owner cost is instalment + maintenance + tax + insurance + repairs − room income.

Net worth at each year end assumes the position is liquidated:

- **Buy:** value − loan − agent/legal − RPGT (by holding year), plus any ETF.
- **Rent:** the ETF.

The model reports nine scenarios (property growth low/base/high × ETF return
low/base/high) and the break-even property growth at the base ETF return, found by
bisection.

Out of scope: FX (use the `etf_cost_drag` input as a stress test), DSR eligibility,
vacancy, special levies, taxes on the ETF (Malaysia's foreign-sourced income
exemption is assumed), and the different living space of a whole unit versus a room.
The proposal text names these.

## 4. Boards

1. Manager's call and review
2. Headline stats
3. Net worth year 0–20 (nominal / today's ringgit)
4. 3 × 3 scenario grid (it drives the other boards)
5. Cash in and cash out
6. Year-by-year table
7. What-if inputs (recomputed by Python, never saved)
8. Inputs and sources

Entry points:

- `/office?dept=finance&station=research`
- the Research desk or the Finance manager in the town
- the Finance aside button

## 5. From research to a public post

The owner's choice on 2026-11-09: research images are a public XHS post, made by the
Content Lab pipeline.

1. The Finance manager adds `post` to the proposal. It holds `public_inputs` (generic
   market numbers), `owner_derived` (the inputs that came from the owner's records)
   with a public note for each, the reader moment, the hypothesis and the limits on
   what the post may say. Validation rejects a public scenario that reuses any
   owner-derived value.
2. After the owner **accepts** the proposal, **Send to Content Lab** (`op: post_idea`)
   creates `data/posts/<slug>-<date>/` with:
   - `post.md`: the idea brief
   - `lab.yaml`: stage `idea`
   - `sources/research-data.json`: the public projection, facts and sources

   A proposal can be filed once; the desk then shows the post id.
3. The owner approves the idea in Content Lab → Ideas, and the autonomous pipeline
   produces the post.
   - Chart pages are rendered by `make post-chart` (`scripts/lib/post_chart.py` →
     HTML → `scripts/render_html.mjs`, 1080 × 1440) in the account template.
   - Numbers on a page can only come from `{{fact}}` placeholders bound to the data
     file; a typed digit fails the spec.
   - Cover, mechanism and closing pages are generated as usual.

## 6. Phase 2 (not built)

An autonomous loop, modelled on `scripts/content_pipeline.py`: the owner types a
question on the desk; a runner (`claude -p` with the wealth-manager skill) writes or
revises the proposal; `validate` acts as the acceptance gate before it reaches the
review inbox. The runner would also pick up `revise` reviews. More proposal kinds
(for example, EPF/PRS top-up versus ETF, or prepaying The Wyn versus investing) each
need their own model in `research.py` and their own boards.
