# Investment Decision Framework

The decision framework wealth-manager uses when doing investment analysis and giving
recommendations. The main SKILL.md defines the workflow; this file holds the investment
philosophy and judgment criteria.

> **This file only covers the satellite layer (single-stock selection).** For the overall plan
> backbone — fund layering, asset allocation, core-satellite, rebalancing, DCA evidence — see
> `wealth-building-playbook.md`; for MY tax/vehicles/UCITS ETFs see `malaysia-wealth-vehicles.md`.
> When making single-stock recommendations, always also check whether the portfolio already has
> an index core — don't let the user just keep piling up satellite.

## Investor Profile Inputs

This framework does not embed a personal age, broker, cash balance, income, or risk tolerance. Read those from the
runtime finance files and user profile before applying the framework. The relevant trade-offs are:

- **Long horizon / growth**: a long, verified horizon can justify tolerating short-term drawdowns for higher expected
  return; a short horizon or near-term liability should lower equity risk.
- **Risk capacity vs. risk tolerance**: stable cash flow and a sufficient emergency reserve may support volatility,
  but the allocation must still be one the investor can hold through a drawdown.
- **Buy-the-dip vs. momentum**: match the decision to verified cash-flow cadence and portfolio policy, not a baked-in
  monthly amount.

## Single-Stock Analysis Framework

### Buy conditions (at least 2 of 4)
1. **Valuation discount**: P/E below the industry average or below its own 5-year average
2. **Price position**: >15% off the 52-week high, and near a technical support level
3. **Sound fundamentals**: revenue/profit grew year-over-year in the most recent quarter, no major negative events
4. **Catalyst**: a clear value-unlocking event (earnings, new product, favorable policy)

### Watch conditions
- Fundamentals are good but the price hasn't reached the entry zone (still >5% above the support level)
- Or there's an unresolved uncertainty (upcoming earnings, ongoing regulatory review)

### Hold conditions
- Already held, fundamentals haven't deteriorated, but the price is not in the add-to-position zone

### Avoid / stop-loss signals
- **Deteriorating fundamentals**: revenue decline for 2 consecutive quarters, management turnover,
  structural sector headwinds
- **Technical breakdown**: breaks below a key support level with no sign of a rebound
- Take care to distinguish "temporary pullback" from "deteriorating fundamentals" — the former is
  a buying opportunity, the latter is a stop-loss signal.
  Judgment criterion: is the cause of the decline a **one-off event** (tariffs, short-term supply-chain
  issues) or a **structural change** (sustained market-share loss, technology roadmap disruption)?

### Stop-loss discipline
- A single stock down >25% with deteriorating fundamentals → force a review, lean toward stop-loss
- A single stock down >25% but fundamentals intact → treat as an add-to-position opportunity, but
  confirm you're not "catching a falling knife"
  (check: is there a clear bottom support level? are peers also declining? are institutions
  accumulating?)

## Portfolio-Level Analysis

Every time you do a stock analysis, besides analyzing the individual stock, also assess the
portfolio's overall health:

### Concentration risk
- A single stock should not exceed 30% of total portfolio value — because even with good
  fundamentals, a single company's black-swan event (accounting fraud, sudden regulatory action)
  is unpredictable, and diversification is the only free lunch
- A single sector should not exceed 50% — sector rotation is normal, and overconcentration
  amplifies cyclical swings

### Geographic/currency distribution
- US-stock holdings are denominated in USD, and are affected by the USD/MYR exchange rate
- When the USD strengthens, the MYR return on US stocks gets amplified, and vice versa
- Analysis should show both the raw USD return and the MYR-converted return, so the user sees the
  real home-currency gain

### Sector correlation
- If multiple holdings are highly correlated (e.g. MSFT/NVDA/META are all US large-cap tech),
  explicitly flag that "these stocks will decline together in a broad market pullback, so
  diversification benefit is limited"
- When recommending, consider complementarity with existing holdings (different sector, different
  market, different style)

## Position Management — DCA Strategy

Build the tranching logic based on the verified investable cash flow in `data/finance/portfolio.yaml`
or policy:

- **Base principle**: don't go all-in at once — build the position in tranches over 2-3 months
- **When the market is normal**: dollar-cost-average monthly into the target
- **When clearly undervalued** (an index-level pullback >10%): can accelerate deployment
  (concentrate the 2-3 months' allocation), but still keep at least 1 month of cash buffer
- **When valuation is elevated**: slow down deployment and accumulate cash while waiting for an
  opportunity
