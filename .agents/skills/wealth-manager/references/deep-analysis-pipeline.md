# Deep Analysis Pipeline — Operating Manual

> Execution steps extracted from `SKILL.md` (audit §3.8). SKILL.md only keeps the trigger
> conditions and a pointer, to avoid paying the context cost of this whole operational detail
> every time the skill triggers.
> Read this file once the trigger conditions are met.


`repos/ai-stock-analysis` is an independent submodule ([ai-stock-analysis](https://github.com/KelvinYou/ai-stock-analysis)).
It runs a 4-layer multi-agent pipeline (Fundamentals/Sentiment/Technical/MacroFX → multi-round
bull/bear debate → conviction score + signal convergence), which is more structured and more
resistant to one-sided bias than a single WebSearch-derived judgment.
**This is the research signal source for holdings/formal candidate stocks; portfolio valuation,
concentration, and sizing are still handled by `personal-os` itself.** WebSearch is only used to
supplement the latest news and cross-check — it is no longer the sole information source.

### When to trigger the full pipeline (rather than just reading the cache)

For the **user's actual holdings** (stocks in `data/finance/portfolio.yaml`) or a **candidate stock
the user explicitly wants seriously evaluated** (not a casual "what do you think of X"), perform
the following checks:

1. Check whether `repos/ai-stock-analysis/data/<TICKER>/briefing.json` exists, and read its `date`
   field (**not the file mtime** — a submodule checkout resets all file timestamps to the clone
   time, so mtime is not trustworthy at all).
2. **Conditions that trigger a rerun** (any one of):
   - The `data/<TICKER>/` directory does not exist (this ticker has never had a deep analysis run)
   - `briefing.json` exists but its `date` is > 14 days old
   - The user explicitly asks for "the latest analysis" / "rerun it"
   - **The WebSearch-only analysis itself shows a clear divergence**: analyst consensus conflicts
     with fundamental red flags (e.g. consensus Strong Buy but FCF/margins deteriorating), bull/bear
     arguments are evenly matched, or you yourself can't judge "temporary pullback vs. structural
     deterioration" — in this case **don't gloss over it or hard-code a conclusion yourself**; follow
     the full process in step 3 below (including the environment self-check), and if that can't run,
     list it in the output as an explicit next action item (e.g. "recommend running a full pipeline
     on META to get a conviction score") instead of ending with just "the data may be inaccurate".
3. **Execution steps once triggered**:
   a. **Environment self-check (try to fix it yourself first — don't give up immediately)**:
      - Check whether `<repo>/.venv/bin/python -c "import stock_analysis"` can import; if not, run
        `python3 -m venv .venv && source .venv/bin/activate && pip install -e .` in the
        `repos/ai-stock-analysis` directory automatically (use the repo's own venv, don't install
        into system Python), then try the import again.
      - Always use §In-Session Pipeline Mode below. Do not inspect, request, or use
        ANTHROPIC_API_KEY, the Anthropic API, or the official SDK-backed stock-analysis path.
   b. If the ticker has never been fetched by `stock-fetch` (a Malaysian stock not in the
      auto-universe like FBM KLCI/S&P500, e.g. BIMB/5258), first run `stock-fetch <TICKER> --market
      MY` to backfill Layer 1.
   c. Running the full pipeline has a conversation token/time cost. **Only trigger it
      for holdings and candidates the user explicitly wants deeply evaluated — don't run it for
      every casual stock question**; an explicit request to analyze a full watchlist authorizes a
      run for every listed ticker.
4. **Don't fake it if data/code cannot be read**: explain the blocker. If necessary, provide a
   clearly labeled unstructured analysis based on available sources; do not imply it has a
   deterministic conviction score or risk calculation.

### In-Session Pipeline Mode (always use for this user)

The SDK-backed CLI calls the Anthropic API separately. For this user, always run analyst, debate,
and synthesis work through the current assistant session and its available agent collaboration.
Do not check for or depend on an API key. Layer 1 (data fetching) and risk calculations continue
to use the repository's real code.

**Execution steps** (once `repos/ai-stock-analysis` has been `pip install -e .`'d once, subsequent
analyses can all take this path without reinstalling the environment every time):

1. **Layer 1 (deterministic, no LLM needed)**: `repos/ai-stock-analysis/.venv/bin/stock-fetch
   <TICKER> --market US|MY -v` refreshes
   `data/<TICKER>/{price_history.csv, fundamentals.json, technicals.json}`.
   If yfinance's `news_headlines` comes back empty (this part of yfinance frequently breaks), use
   WebSearch to supplement recent news and feed it to the Sentiment analyst below as real input —
   don't let it analyze against empty data.
2. **Layer 2 (4 analysts, run 4 Agent calls in parallel)**: for each, use the system prompt from
   `src/stock_analysis/agents/{fundamentals,sentiment,technical,macro}.py` verbatim (this is the
   sole authoritative source for these analyst personas — don't rewrite it yourself) plus the
   corresponding real data (Layer 1's JSON/CSV; for Macro, use WebSearch to look up the current
   real Fed/BNM interest-rate environment instead of the repo's hard-coded, outdated
   `MACRO_CONTEXT`), and require each agent to output only JSON matching the corresponding schema
   in `src/stock_analysis/models/agent_reports.py` (`FundamentalsReport` / `SentimentReport` /
   `TechnicalReport` / `MacroFXReport`).
3. **Layer 3 (bull/bear debate, 2 rounds is enough — skip the 3rd round for cost reasons)**: follow
   the `BULL_SYSTEM`/`BEAR_SYSTEM` prompts in `src/stock_analysis/debate/engine.py` plus the
   previous round's argument summary, running Agent calls in sequence (bull round 1 → bear round 1
   → bull round 2 → bear round 2), then finally run one moderator agent to summarize per
   `SUMMARY_OUTPUT_SCHEMA` (agreement/disagreement/unresolved).
4. **Layer 4 (synthesis, 1 Agent call)**: use the system prompt from
   `src/stock_analysis/synthesis/synthesizer.py` plus `BRIEFING_OUTPUT_SCHEMA`, feed in all 4
   analyst reports plus the debate result, and require output of `overall_signal` +
   `conviction` (score/signal_convergence/explanation) +
   `executive_summary`/`bull_case`/`bear_case`/`key_uncertainties`/`catalysts_upcoming`/
   `agent_signal_breakdown`. **The score's sign must match the signal direction** (sell-type signals
   must be negative) — this is a rule explicitly required by the synthesizer prompt; follow it.
5. **Layer 4 risk calculation (pure math — don't compute it mentally, call the real code)**: save
   the JSON from the analyst, debate, and synthesis steps into temp files. If Layer 3.5 produced
   a `ResearchVerdict`, save that separately as `/tmp/<ticker>_research_verdict.json`, then run
   `.agents/skills/wealth-manager/scripts/finalize_briefing.py` (executed with
   `repos/ai-stock-analysis/.venv/bin/python`; pass `--research-verdict /tmp/<ticker>_research_verdict.json`
   when that file exists. See the usage in the script's top-of-file docstring.
   This script directly imports the repo's real `RiskChecker` (`synthesis/risk_checker.py`) and
   Pydantic models to compute ATR stop-loss/take-profit levels, historical drawdown, and
   risk/reward — this is deterministic math, and the script's results match the official CLI's
   output exactly; don't let the LLM estimate these numbers itself.
6. The script writes analyst_reports.json / debate_result.json / briefing.json and, when
   supplied, research_verdict.json back to repos/ai-stock-analysis/data/<TICKER>/, tagged with
   pipeline_mode=in-session so downstream readers know these were produced through the
   current assistant session.
7. Once done, label this analysis in the output to the user as "In-Session Pipeline" rather than
   vaguely saying "deep analysis" — this keeps to the "disclose which mode produced the verdict"
   principle from the General Guidelines above.

### How to use the pipeline output

- `briefing.json`: `overall_signal`, `conviction.score` (−1.0 to +1.0), `conviction.signal_convergence`
  (0 = the four layers disagree, 1 = fully aligned), `executive_summary`, `bull_case`/`bear_case`,
  `key_uncertainties` — this is the core conclusion for the user; quote the conviction score and
  convergence directly instead of composing your own separate judgment.
- If `signal_convergence` is low (<0.5) or conviction is near 0, **explicitly tell the user this is
  a "high-divergence/low-confidence" signal** — don't dress it up as a clean-cut Buy/Sell.
- `technicals.json` / `fundamentals.json`: supplement specific numbers (RSI, P/E, support levels)
  into the output table.
- Include `key_uncertainties` in the "⚠️ Review / At Risk" section or a separate section, so the
  user knows what unresolved issues sit behind the conclusion.
