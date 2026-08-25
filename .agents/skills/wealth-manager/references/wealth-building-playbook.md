# Wealth-Building Playbook — Overall Financial Plan Framework

> This is wealth-manager's **overall plan layer**. `investment-framework.md` answers "which stock
> to buy"; this file answers "how should money be layered, in what order should it be invested,
> what should the portfolio skeleton look like."
> This file does not assume any particular current holdings or broker; if the runtime portfolio is
> mostly single stocks, treat it as satellite and check whether a core and cash-layering structure
> is missing.
>
> **Last researched: 2026-06-02.** Rates/tax allowances change — verify before citing a specific
> number (see the Sources at the end + SKILL.md's Data Freshness section).

---

## 0. The core diagnosis: upgrading from "picking stocks" to "having a plan"

If an investor's approach is to directly pick MY/US single stocks, that may mean they **only have
a satellite, no core** — if all the money sits in high-volatility positions that require active
judgment, modern best practice (Bogleheads / core-satellite consensus) runs the other way:

- **Build the core first (the index skeleton)**: 60–75% of the portfolio, in broad-market low-cost
  index ETFs, held hands-off, capturing the market's average return.
- **Then add satellite (high-conviction single stocks)**: 25–40%, which is the stock-picking the
  user is doing now. This allows for alpha, but even if it's all wrong, the core still provides a
  floor.

Research repeatedly shows that the vast majority of active stock pickers underperform the index
over the long run; retail investors create a "behavior gap" from frequent trading + chasing
rallies and panic-selling, so their actual return ends up lower than the fund they held. The point
of core-satellite is to **use structure to counter human nature** — lock most of the money into a
core that requires no judgment, and confine the urge to "beat the market" to the satellite.

> Whenever doing any stock analysis for the user, also remind them at the portfolio level: has the
> satellite position exceeded 40%? Has a core been built yet?

---

## 1. Cash Layering — Financial Order of Operations (sequence)

Where the next ringgit should go, ordered by "which step has the highest marginal return." MY
localized version:

| Order | Action | Target amount | Rationale |
|------|------|----------|------|
| 1 | **Starter emergency fund** | RM3k–6k (1 month of expenses) | Prevents having to liquidate positions/borrow at the first mishap |
| 2 | **Pay off high-interest debt** | Any debt >7–8% (credit card, excluding PTPTN which depends on the situation) | Paying off 18% credit-card debt = a risk-free 18% return; no investment can reliably beat that |
| 3 | **Full emergency fund** | 3–6 months of expenses, in a highly liquid, high-yield vehicle (see malaysia-wealth-vehicles.md) | The safety cushion before investing; lets you hold through a bear market |
| 4 | **Tax relief allowance** | PRS RM3,000/year (see §Tax) | A one-off ~21–24% "tax return" — the single most certain step |
| 5 | **Index core DCA** | Main monthly cash flow | Global/US index ETFs, the long-term compounding engine |
| 6 | **Satellite single stocks** | Whatever remains once the core is built | The stock-picking the user is doing now, capped at 25–40% |
| 7 | **Earmarked goals** | House purchase/further study, etc. | Use a tool matched to the timeframe (FD/MMF/bonds), not high-volatility assets |

**Key judgment**: don't put all cash into the stock market before the emergency fund is full;
investing before high-interest debt is paid off is negative-sum. If the verified cash reserve
already covers steps 1–3, the focus should be deploying the "excess cash" above step 3 per §3,
rather than hoarding cash indefinitely (cash erodes to inflation over the long run).

---

## 2. Asset Allocation Skeleton — Matching Age and Risk

For an investor with a 30+ year horizon and moderate-growth risk tolerance, a common reference is
**85–90% equities / 10–15% defensive assets (bonds/cash/MMF)**. Don't scale down to 60/40 just
because the profile says "moderate" — that's a near-retirement allocation; a young person's
biggest asset is time, and being overly conservative is itself a risk.

### Recommended core skeletons (pick one, increasing in complexity)

**A. Simplest, one fund (recommended starting point)**
- 100% global stock index: `VWRA` (Vanguard FTSE All-World, Acc, Ireland-domiciled, TER 0.22%)
- One fund covers global diversification, auto-reinvests, no rebalancing needed. Good for someone
  still in the accumulation phase who doesn't want to fuss over it.

**B. Classic three-fund (a localized Bogleheads three-fund portfolio)**
- 60% total US market (`CSPX` S&P500 or the US portion of `VWRA`)
- 20% international stocks (developed ex-US + emerging)
- 10–20% defensive (MY bond fund / MMF / cash)
- As of 2026, this combination's 10-year annualized return is around 11%, with total fees as low
  as 0.03–0.22%.

**C. Core-Satellite (best fit for this user)**
- **Core 65–75%**: `VWRA` or `CSPX` (global/US index)
- **Satellite 25–35%**: the MY + US single stocks in the runtime portfolio (selected per
  investment-framework.md)
- Rule: total satellite value must not exceed 40% of the portfolio; a single satellite position
  ≤ 15% of the portfolio (echoing the framework's concentration cap).
- Self-check: if the satellite underperforms the core for 3 consecutive years, move more money
  back into the core.

> If the investor is already doing satellite picking, the correct move is to first check whether
> the core has reached its target, then confine stock-picking to a bounded alpha attempt.

---

## 3. Deployment Pace — DCA vs. Lump Sum (let the evidence decide)

- **Vanguard research (1976–2022, MSCI World)**: lump-sum investing beat DCA in about **68%** of
  12-month periods, because more months are up months than down months. So **when there's a
  verified chunk of excess cash, deploying it promptly beats slow DCA** — unless valuations are
  clearly elevated or it's psychologically unbearable.
- **If the main money source is a regular monthly inflow** (the amount read from
  `data/finance/portfolio.yaml`'s `investor_profile.monthly_savings`) — this is inherently DCA
  already, not the alternative to lump-sum but the natural shape of that cash flow. Just keep
  dollar-cost-averaging into the core monthly.
- **DCA's real value is psychological discipline**: it lets someone keep buying through a bear
  market instead of sitting out. If a lump-sum deployment would keep the user up at night, or make
  them panic-sell during a pullback, spreading the excess cash over 2–3 months is a worthwhile
  "peace-of-mind premium."
- **Accelerate during a pullback**: when there's an index-level pullback >10%, concentrate the next
  2–3 months' allocation into the core (not the satellite), while keeping ≥1 month of cash buffer.
  This echoes the DCA strategy in investment-framework.md.

---

## 4. Rebalancing Discipline

Without rebalancing, a portfolio automatically drifts into a "higher-volatility version" of itself
as things rise, quietly amplifying risk.

- **Frequency**: once a year (e.g. every January) is enough; rebalancing too often just adds cost
  and tax drag.
- **Threshold method (the 5/25 rule)**: rebalance when an asset class drifts **>5 percentage
  points** (absolute) or **>25%** (relative) from its target. Example: target core 70%, rebalance
  when it rises to 76% or falls to 64%.
- **Prefer rebalancing with new contributions**: use new monthly money to top up whichever part is
  "below target" first, minimizing sales (saves fees, avoids realizing gains/losses).
- When the satellite outgrows its target share because it outperformed, rebalancing forces exactly
  the right move — trim the winner, top up the core — which is counter-intuitive but correct.

---

## 5. Behavioral Discipline — Countering the Behavior Gap

90% of a good plan is behavior, not stock-picking. Reinforce this repeatedly when advising the
user:

- **Don't try to time the market**: the cost of missing out is usually larger than the cost of a
  pullback; being absent for the market's few best days severely drags down long-term returns.
- **Don't chase hot trends**: frequent satellite traders underperform long-term holders over time.
  News-driven impulsive trading is an alpha killer.
- **Think in years, not days**: over a 30-year horizon, daily/weekly swings are noise. A monthly
  review should look at DCA execution rate, not paper gains/losses.
- **Automate by default**: if automatic recurring investment can be set up, don't do it manually —
  manual investing leaves room for the "let's skip this month" impulse.
- **Write down the sell rationale**: define what would mean "the thesis is broken" at the time of
  purchase (see the framework's stop-loss discipline), to avoid emotional decisions later.

---

## Sources (retrieved 2026-06, review periodically)

- Vanguard — Lump sum vs cost averaging (the 68% finding): https://investor.vanguard.com/investor-resources-education/news/lump-sum-investing-versus-cost-averaging-which-is-better
- Bogleheads three-fund portfolio: https://www.bogleheads.org/wiki/Three-fund_portfolio
- Optimized Portfolio — 3-fund 2026 review: https://www.optimizedportfolio.com/bogleheads-3-fund-portfolio/
- Core-satellite strategy: https://waterloocap.com/core-satellite-investing-guide/ ; https://www.home.saxo/learn/guides/diversification/core-satellite-approach-a-smarter-way-to-diversify-your-investments
- Vanguard asset allocation models: https://investor.vanguard.com/investor-resources-education/education/model-portfolio-allocation
- Money Guy — Financial Order of Operations: https://moneyguy.com/guide/foo/
