# Long-term equity allocation — 2026-09-17

> [Status: Warning] Research notes, not an approved investment policy or a validated optimal portfolio. Public-source discussion and illustrative calculations only; no backtest or individual-stock valuation pipeline was run. Actual holdings, tax status, investable cash and loss tolerance were not verified.
> Re-verify after **2026-10-17**, or before acting if earnings, prices, fund terms or tax circumstances change. Recheck Vanguard forecasts when the next quarterly release appears.

## Allocation conclusions

- VT already contains US stocks, including the companies in VOO. Adding VOO increases US large-cap exposure; it does not add a separate asset class.
- Within an 80% ETF / 20% individual-stock allocation, the more geographically diversified candidate discussed was **80% VT + 5% each MSFT, GOOGL, BRK.B and NVDA**.
- Alternative with an explicit US tilt: **64% VT + 16% VOO + the same four stocks at 5% each**. These are candidate weights, not user-approved trades or evidence of superior returns.
- The individual stocks overlap with the ETFs: actual company exposure exceeds each direct 5% holding. No evidence established that this stock sleeve will outperform an all-ETF portfolio.
- Both candidates are **100% equities**. An illustrative simultaneous decline of 40% in ETFs and 60% in individual stocks produces a **44% portfolio loss**; this is a stress test, not a maximum-loss estimate.
- Keep emergency reserves and near-term spending outside this allocation. Compare US-domiciled VT/VOO with Irish UCITS alternatives before implementation; VWRA is not an exact VT equivalent. Verify tax eligibility, broker access and all-in costs rather than assuming eligibility or savings.

## Ten-year planning assumptions

Use **5%–7% nominal annualized total return, with 6% as a planning midpoint**, not a forecast derived from these stock weights. Do not assume stock selection adds excess return. Include weaker and loss scenarios.

Illustrations assume dividends reinvested, constant returns, unchanged FX, and no deductions for taxes, trading costs or inflation. Monthly contributions occur at month-end, starting from zero; total contributions are RM120,000.

| Annualized return assumption | RM10,000 invested once: year 10 | RM1,000 monthly: year 10 |
|---|---:|---:|
| -2% | RM8,171 | RM108,747 |
| 3% | RM13,439 | RM139,448 |
| 6% | RM17,908 | RM162,473 |
| 9% | RM23,674 | RM189,719 |

Formulas: lump sum = `P * (1+r)^10`; monthly contributions = `C * ((1+i)^120-1)/i`, where `i = (1+r)^(1/12)-1`. Real contribution outcomes depend on return sequence; MYR outcomes also depend on FX.

## Why Vanguard forecasts less than recent historical returns

- The forecast retrieved in this discussion used **2026-06-30** market conditions: **4.2%–6.2% annualized US broad-equity total return over ten years**, in USD, before inflation, taxes and investment expenses. It is a model outlook, not an annual floor/ceiling or guaranteed outcome interval.
- Vanguard attributed the reduction from 4.9%–6.9% to higher starting valuations. Its model incorporates economic and financial risk factors and simulations; valuation normalization is an important assumption, not a certainty.
- Intuition: **total return approximately reflects per-share earnings growth + dividends + valuation changes**. Strong business growth can coexist with modest investment returns when the purchase price already embeds optimistic expectations.
- Illustrative example, not Vanguard inputs: EPS grows from $10 to $19.67 at 7% annually over ten years, while P/E falls from 30 to 22. Price rises from $300 to $432.77: only **3.7% annualized price appreciation**, before dividends.
- The previously mentioned historical 12%–14% needs a specified index, start/end dates and dividend treatment before comparison. It is not a permanent return entitlement. The model can underestimate earnings or the persistence of high valuations; use it for scenario planning, not a market-exit signal.

## Lower returns do not imply money must move elsewhere

- Market capitalization is a valuation, not a pool of cash. Marginal trades can reprice all outstanding shares; a loss of market value does not require an equal cash outflow into another asset.
- Lower future returns can result from prices moving sideways while profits catch up, or from a correction followed by growth. Neither requires a particular alternative market to boom.
- Bonds, US value stocks and non-US developed equities are possible relative opportunities, not established destinations of future flows. Expected returns can decline across multiple asset classes at once.
- AI productivity gains may accrue to adopting businesses and consumers as well as technology suppliers. Economic progress does not translate one-for-one into returns for today's expensive AI stocks.

## Next analysis gates

1. Confirm starting capital, monthly contributions, tax status, broker and tolerable drawdown; then calculate net MYR scenarios.
2. Check current valuations and ETF look-through exposure before approving any individual-stock sleeve. Compare against a 100% VT benchmark without assuming stock-picking outperformance.
3. Refresh fees/taxes using [the existing platform-cost analysis](etf-platform-net-return-2026-08.md); its historical assumptions are not independently verified by this note.

## Sources

- [Vanguard VCMM forecasts](https://corporate.vanguard.com/content/corporatesite/us/en/corp/vemo/vemo-return-forecasts.html) — live page; figures above refer to the June 2026 model run retrieved for this discussion.
- [Vanguard valuation framework](https://corporate.vanguard.com/content/corporatesite/us/en/corp/vemo/how-stock-bond-valuations-changed.html).
- [Vanguard: AI-driven equity returns](https://corporate.vanguard.com/content/corporatesite/us/en/corp/articles/how-much-upside-remains-for-ai-driven-equity-returns.html).
- [VT](https://advisors.vanguard.com/investments/products/vt/vanguard-total-world-stock-etfp) and [VOO](https://advisors.vanguard.com/investments/products/voo/vanguard-sp-500-etf) fund descriptions.
- [IRS: nonresident US-situated assets](https://www.irs.gov/individuals/international-taxpayers/some-nonresidents-with-us-assets-must-file-estate-tax-returns) — the US$60,000 threshold concerns estate filing requirements; it is not a flat 40% tax on all excess assets.
