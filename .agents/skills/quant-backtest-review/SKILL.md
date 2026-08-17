---
name: quant-backtest-review
description: >
  Adversarially review new or changed backtest, scoring, and signal-generation
  code in repos/ai-stock-analysis before its output is trusted for a real
  trade. Use this skill whenever the user asks to review a backtest change,
  add a new strategy or feature to the backtest/scorer/portfolio modules,
  interpret a backtest report's numbers, decide whether a hit rate or Sharpe
  is "real", or asks "does this signal actually work" / "can I trust this
  number" — even if they don't say "backtest" or "statistics" explicitly.
  Also trigger before any wealth-manager decision that cites a backtest
  result the user hasn't had checked yet. This skill checks for lookahead
  bias, overfitting, unrealistic transaction costs, and statistical
  significance problems (deflated Sharpe, multiple testing, small samples) —
  it does not do general code review or multi-repo integration checks.
allowed-tools: Bash, Read, Glob, Grep
---

# Quant Backtest Review

`repos/ai-stock-analysis` already has real statistical rigor built in — effective
sample size, Wilson/Fisher intervals, an exact Student-t tail, and a Deflated
Sharpe Ratio, all documented as load-bearing invariants in that repo's
`CLAUDE.md`. That is exactly what makes this skill necessary rather than
redundant: the existing machinery does the right thing by default, and the
failure mode this skill exists for is a change that *bypasses* it — a new
feature that reads a future value, a new strategy added to `portfolio.simulate`
without widening the DSR comparison, a report that quotes a bare hit rate
outside `Scorer.to_markdown`. The bar is not "is the math correct" (`stats.py`
already gets that right); it's "does the new code route through the existing
guardrails, and if it adds a new one, does it hold up."

## Ownership boundary

This skill owns statistical and methodological validation of quant code in
`repos/ai-stock-analysis`. It does not own:

- General code quality, style, or architecture review → `repo-review`
- Cross-repo submodule state, dirty trees, integration order → `repo-orchestrator`
- Whether a signal should change the user's actual holdings → `wealth-manager`
  (hand it a *pass/fail* verdict on the backtest; let it make the money decision)

If asked to "review this PR" with no quant angle, defer to `repo-review`. If
asked "is my portfolio okay", defer to `wealth-manager` — pull this skill in
only if that conversation leans on a backtest number.

## When there's no code diff to review

The user may just paste a backtest report (`Scorer.to_markdown` output, an
`.md` file under `repos/ai-stock-analysis/docs/`) and ask if the number is
real. In that case skip straight to the **Report-reading checklist** below —
there's nothing to diff, just numbers to interrogate.

## Review checklist

Work through these in order. Each references the actual file that owns the
invariant — read it, don't assume the docstring is still accurate for the
diff in front of you.

### 1. Lookahead bias / leakage

The leakage guard lives in `src/stock_analysis/memory/outcomes.py`:
`OutcomeRecord.visible_on()` admits a record only when its *exit* date is
before the analysis date. If a diff touches `memory/outcomes.py`,
`backtest/runner.py`, or any feature/label construction:

- Does every value used as a feature at `as_of_date` come from data that
  existed *at or before* `as_of_date`? Check price series slicing in
  `runner.py` (`_fetch_price_series`, `_price_on_or_after`) — a change that
  fetches a window ending after `as_of_date` and doesn't trim it is a leak.
- Does `OutcomeStore.load(..., before=...)` get called with the analysis
  date, not some other date that would let unresolved or future outcomes in?
- If a diff adds a new data source (e.g. analyst revisions, restated
  fundamentals), does it have a "when was this actually known" timestamp
  distinct from "when does this row say it's for"? Restated fundamentals in
  particular are a classic silent leak — the value in the row often postdates
  the period it's labeled with.
- `backtest/scorer.py` also carries a **training-data contamination** guard
  distinct from the above: `MODEL_TRAINING_CUTOFFS` in `scorer.py` marks
  trials at-or-before a model's training cutoff as unreliable, because the
  LLM may recall the outcome instead of forecasting it. If a diff adds a new
  model alias to the pipeline, does `MODEL_TRAINING_CUTOFFS` get a
  corresponding entry? A missing entry doesn't error — it just silently
  drops that model's trials out of the pre/post-cutoff split, understating
  contamination risk instead of flagging it.

### 2. Overfitting / strategy search

`backtest/portfolio.py` runs multiple strategies (`simulate()`, default six)
and reports `n_strategies_tested` so the winner's Sharpe can be checked
against `deflated_sharpe_ratio` (`_attach_selection_bias_metrics`). If a diff
adds a strategy, a parameter sweep, or a tuning loop:

- Does the new strategy get counted in `n_strategies_tested`? Adding a
  strategy without it flowing into that count is the single easiest way to
  quietly understate selection bias in this codebase.
- Is a parameter (horizon, threshold, model choice) being swept and the best
  value reported without folding the sweep width into `n_strategies_tested`
  or an equivalent multiple-testing correction? A grid search over 20
  thresholds is 20 implicit strategies even if the code never calls it that.
- Is there an out-of-sample slice at all? `scorer.py`'s pre/post training
  cutoff split is the only out-of-sample boundary in this codebase today — if
  a new evaluation path bypasses `Scorer.score` entirely, it likely bypasses
  that boundary too.

### 3. Transaction costs / slippage

`Scorer.score(result, cost_bps_per_side=...)` charges a round-trip cost to
directional trials only, and `to_markdown` refuses to hide the gross number
even when a net one is available (see the `⚠ Costs not modelled` line when
`cost_bps_per_side` is 0). Check:

- Does a new report path call `Scorer.to_markdown` (inherits the warning) or
  hand-roll its own markdown that could drop the gross/net distinction?
- Is the assumed `cost_bps_per_side` realistic for the instrument? The
  repo's own `CLAUDE.md` flags Bursa small caps as thin enough that costs can
  exceed the entire edge — a diff that hardcodes a cost assumption tuned for
  a liquid US large-cap and reuses it for a Bursa ticker is importing that
  risk silently.
- Does `portfolio.py`'s equity simulation (`_simulate_one`, `flush_exits_up_to`)
  apply cost consistently with the scorer's convention (charged only where a
  position was actually taken), or does a new code path double-charge /
  under-charge relative to that?

### 4. Statistical significance

`backtest/stats.py` is the single source of truth for every interval and
p-value in this codebase — Wilson intervals for hit rates, Fisher-z for the
information coefficient, an exact Student-t tail, and PSR/DSR for Sharpe, all
computed on `effective_n` rather than the nominal trial count
(`effective_sample_size` in `stats.py`, used via `_compute_partition` in
`scorer.py`). Red flags in a diff:

- A new metric reported as a bare point estimate with no interval — this
  codebase's whole design principle (see `stats.py`'s module docstring) is
  that a point estimate without an interval reads as an edge whether or not
  it is one. Any new headline number should get a CI or a p-value next to it,
  not just a percentage.
- A p-value or t-statistic computed against `len(trials)` instead of
  `n_eff` — check whether `effective_sample_size` was actually threaded
  through, not just imported.
- A new call to `probabilistic_sharpe_ratio` or `deflated_sharpe_ratio` with
  hand-computed skew/kurtosis instead of `stats.skewness`/`stats.kurtosis` —
  `kurtosis()` in `stats.py` returns **non-excess** kurtosis specifically
  because the PSR formula is written against that convention; a normal-3.0
  vs. excess-0.0 mismatch silently shifts every PSR by `(3/4)·SR²`.
- Below-30 effective sample size reported without the escalating warning
  `_small_sample_warning` already produces — if a new report path exists
  alongside `Scorer.to_markdown`, confirm it surfaces the same warning rather
  than quietly dropping it.

### 5. Survivorship bias in the ticker universe

Less code-visible than the above — this is a question to ask about the data,
not a specific function to check:

- Does the backtest's ticker list include names that have since been
  delisted, gone bankrupt, or been acquired at a loss? A universe built from
  "tickers currently in `repos/ai-stock-analysis/data/`" is implicitly
  survivorship-biased — anything that failed badly enough to get dropped from
  active tracking isn't in there to drag the average down.
- If the diff adds a fixed ticker list (vs. pulling from an index membership
  file with historical constituents), flag it as a known limitation rather
  than treating the backtest's win rate as clean — this codebase doesn't yet
  have a point-in-time index membership source, so this is usually a
  disclosure, not a blocking fix.

## Report-reading checklist

When there's no diff — just a rendered `Scorer.to_markdown` report or a
pasted number — ask, in order:

1. Is there a confidence interval or p-value attached? If not, treat the
   number as noise until one is computed.
2. Does the hit-rate or IC interval span the null (50% / 0)? If so, say so
   plainly — `stats.py`'s own helpers already flag this
   (`_coin_flip_note`, `_zero_note`) but a user skimming the number may miss it.
3. Is this the pre-cutoff or post-cutoff slice? Only post-cutoff is genuine
   out-of-sample; a pre-cutoff number may reflect model recall, not forecast
   skill.
4. Gross or net of cost? If gross, ask what a realistic cost assumption
   would do to it before treating the edge as real.
5. Was this the best of several strategies or parameters? If
   `n_strategies_tested > 1`, check the DSR line rather than the raw PSR.

## Output format

Report findings the same way `repo-orchestrator` does — `[Status: OK]` when
the diff or report clears all five checks, `[Status: Warning]` for a
disclosed-but-unaddressed issue (e.g. survivorship bias with no point-in-time
universe available yet), `[Status: Critical]` for anything that would let a
falsely-significant number reach a real trade decision (leakage, an
uncounted strategy search, a bare point estimate presented as an edge).

For each finding: name the specific file/function, what it's doing wrong
(or what's missing), and what passing looks like — point at the analogous
existing pattern in `stats.py`/`scorer.py`/`portfolio.py` rather than
inventing a new convention.

Hand a **verdict, not a recommendation** back to whichever skill or
conversation asked for the review — "this backtest is [Status: OK] to cite
as evidence of edge" or "this number is [Status: Critical] — do not let it
move a real position until X is fixed" — since making the actual buy/sell
call belongs to `wealth-manager`, not here.
