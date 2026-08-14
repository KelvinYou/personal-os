# Deep Analysis Pipeline — 操作手册

> 从 `SKILL.md` 抽出的执行步骤（审计 §3.8）。SKILL.md 只保留触发条件与指针，
> 避免每次触发该 skill 都付这一整套操作细节的上下文成本。
> 触发条件满足时再读本文件。


`repos/ai-stock-analysis` 是独立 submodule（[ai-stock-analysis](https://github.com/KelvinYou/ai-stock-analysis)）。
它跑一个 4 层 multi-agent pipeline（Fundamentals/Sentiment/Technical/MacroFX → bull/bear 多轮 debate →
conviction score + signal convergence），比单纯 WebSearch 出的一次性判断更结构化、更抗单边偏见。
**这是持仓/正式候选股票的研究信号源；portfolio valuation、concentration 和 sizing 仍由
`personal-os` 自己处理。** WebSearch 只用来补最新新闻和做交叉核对，不再是唯一信息源。

### 何时触发完整 pipeline（而不只是读缓存）

对**用户实际持仓**（`data/finance/portfolio.yaml` 里的股票）或**用户明确要认真评估的候选股票**
（不是随口一问的 "你觉得 X 怎么样"），执行以下检查：

1. 看 `repos/ai-stock-analysis/data/<TICKER>/briefing.json` 是否存在，读其中的 `date` 字段
   （**不是文件 mtime**——submodule checkout 会把所有文件时间戳重置成 clone 时间，mtime 完全不可信）。
2. **触发重新运行的条件**（满足任一）：
   - `data/<TICKER>/` 目录不存在（这个 ticker 从没跑过深度分析）
   - `briefing.json` 存在但 `date` 距今 > 14 天
   - 用户明确要求"最新分析"/"重新跑一下"
   - **WebSearch-only 分析本身出现明显分歧**：分析师共识与基本面红旗冲突（如 consensus Strong Buy
     但 FCF/利润率在恶化）、bull/bear 论点势均力敌、或你自己判断不出"暂时性回撤 vs 结构性恶化"——
     这种情况**不要含糊带过或自己硬编一个结论**，按下面第 3 步（含环境自检）走完整流程，跑不了就在输出里把它列为
     明确的下一步行动项（例如 "建议对 META 跑一次完整 pipeline 拿 conviction score"），不要只是
     一句"数据可能不准"就结束。
3. **触发时的执行步骤**：
   0. **环境自检（先自己尝试修，别一上来就放弃）**：
      - 检查 `<repo>/.venv/bin/python -c "import stock_analysis"` 能不能 import；不能的话在
        `repos/ai-stock-analysis` 目录下自动跑 `python3 -m venv .venv && source .venv/bin/activate &&
        pip install -e .`（用仓库自己的 venv，不装到系统 Python），装完再试一次 import。
      - 检查 `ANTHROPIC_API_KEY` 环境变量是否存在：
        - **存在** → 走 (a)(b)(c) 的官方 CLI 路径（`stock-analysis` 命令，claude-agent-sdk 内部调用
          Haiku/Opus/Sonnet 混合路由）。
        - **不存在**（Claude Code 会话里通常就是这样，没有独立的 API key）→ **不要问用户要 key，
          也不要因此放弃深度分析**。直接走 §In-Session Pipeline Mode（见下），用当前会话自己的推理
          能力顶替 claude-agent-sdk 的 4 个分析师 + debate + synthesis，Layer 1（价格/财务，纯
          yfinance，无需 LLM）和 Layer 4 的风险计算（纯确定性数学）仍然复用 repo 里的真实代码，
          不是自己瞎编一套。
   a. （有 API key 时）先刷新 Layer 1：`cd repos/ai-stock-analysis && git pull origin main`，
      submodule 落后太多再 `git submodule update --remote repos/ai-stock-analysis`（回根目录执行，
      会改 `.gitmodules` 指针，提交前告诉用户）。
   b. （有 API key 时）跑 `stock-analysis <TICKER> --market US -v`（MY 股票用 `--market MY` +
      代码如 `1155`/`4197`），在 `repos/ai-stock-analysis` 目录下执行。
   c. 如果 ticker 从未被 `stock-fetch` 抓过（不在 FBM KLCI/S&P500 等自动 universe 里的马股，
      像 BIMB/5258），先跑 `stock-fetch <TICKER> --market MY` 补 Layer 1。
   d. 完整 pipeline 跑一次有实际成本（有 key 时是 API 费用；没 key 用 In-Session 模式则是这次对话的
      token/时间）。**只对持仓和用户明确要求深度评估的候选触发，不要对每一句随口的股票问题都跑**——
      随口问题继续用 WebSearch 快速回答即可。
4. **读不到就不要装**：如果两条路径都跑不成（venv 装不上、In-Session 模式也被用户明确叫停），
   直接用 WebSearch 分析并在输出里注明 "非结构化深度分析，仅基于当前搜索"，不要暗示这是
   conviction-scored 的结果，并且**明确留一句行动项**告诉用户下次想要更准的信号该怎么跑。

### In-Session Pipeline Mode（没有 `ANTHROPIC_API_KEY` 时的默认深度分析方式）

官方 CLI 的 Layer 2-4（4 个分析师 agent + bull/bear debate + synthesis）靠 `claude-agent-sdk` 单独
调 Anthropic API，需要 `ANTHROPIC_API_KEY`。Claude Code 会话本身没有这个 key 很正常——**不代表深度
分析跑不了，只代表要换一种跑法**：用当前会话自己（通过 Agent 工具起子 agent）顶替那几个 LLM 调用，
Layer 1（数据抓取）和风险计算部分继续复用 repo 的真实代码，不用自己重新发明。

**执行步骤**（`repos/ai-stock-analysis` 已经 `pip install -e .` 过一次之后，之后的分析都可以走这条路，
不需要每次都重装环境）：

1. **Layer 1（确定性，无需 LLM）**：`repos/ai-stock-analysis/.venv/bin/stock-fetch <TICKER> --market
   US|MY -v` 刷新 `data/<TICKER>/{price_history.csv, fundamentals.json, technicals.json}`。
   如果 yfinance 的 `news_headlines` 抓回来标题是空的（yfinance 这块经常失效），用 WebSearch 补最近
   新闻，喂给下面的 Sentiment 分析师当真实输入，不要让它对着空数据分析。
2. **Layer 2（4 个分析师，并行起 4 个 Agent 调用）**：分别用
   `src/stock_analysis/agents/{fundamentals,sentiment,technical,macro}.py` 里的 system prompt
   （原文照抄，这是这几个分析师人设的唯一权威来源，不要自己改写）+ 对应的真实数据（Layer 1 的
   JSON/CSV + Macro 用 WebSearch 查当前真实的 Fed/BNM 利率环境，不要用 repo 里硬编的旧
   `MACRO_CONTEXT`），要求每个 agent 只输出符合
   `src/stock_analysis/models/agent_reports.py` 里对应 schema（`FundamentalsReport` /
   `SentimentReport` / `TechnicalReport` / `MacroFXReport`）的 JSON。
3. **Layer 3（bull/bear debate，2 轮即可，成本考虑不用跑满 3 轮）**：按
   `src/stock_analysis/debate/engine.py` 的 `BULL_SYSTEM`/`BEAR_SYSTEM` prompt + 上一轮的论点摘要，
   顺序起 Agent 调用（bull 第 1 轮 → bear 第 1 轮 → bull 第 2 轮 → bear 第 2 轮），最后再起一个
   moderator agent 按 `SUMMARY_OUTPUT_SCHEMA` 做总结（agreement/disagreement/unresolved）。
4. **Layer 4（synthesis，1 个 Agent 调用）**：用 `src/stock_analysis/synthesis/synthesizer.py` 的
   system prompt + `BRIEFING_OUTPUT_SCHEMA`，把 4 份分析师报告 + debate 结果丢进去，要求输出
   `overall_signal` + `conviction`（score/signal_convergence/explanation）+
   `executive_summary`/`bull_case`/`bear_case`/`key_uncertainties`/`catalysts_upcoming`/
   `agent_signal_breakdown`。**score 符号必须和 signal 方向一致**（sell 类必须是负数），这是
   synthesizer prompt 里明确要求的规则，照做。
5. **Layer 4 风险计算（纯数学，不要自己心算，调真代码）**：把上面 3 步的 JSON 分别存成临时文件，
   跑 `.agents/skills/wealth-manager/scripts/finalize_briefing.py`（用
   `repos/ai-stock-analysis/.venv/bin/python` 执行，见脚本顶部 docstring 的用法）。这个脚本直接
   import repo 真实的 `RiskChecker`（`synthesis/risk_checker.py`）和 Pydantic 模型来算
   ATR 止损/止盈位、historical drawdown、risk/reward——这些是确定性数学，脚本算的结果和官方 CLI 跑出来的
   分毫不差，不要让 LLM 自己去估算这些数字。
6. 脚本会把 `analyst_reports.json` / `debate_result.json` / `briefing.json` 写回
   `repos/ai-stock-analysis/data/<TICKER>/`，并打上 `"pipeline_mode": "in-session-claude-code"`
   标记——这样以后任何人（包括你自己下次读缓存时）都知道这份结果是当前 Claude Code 会话自己跑出来的，
   不是官方 Haiku/Opus/Sonnet 混合路由跑出来的，两者严谨程度接近但模型配置不同，别混着当成同一件事。
7. 用完之后把这次分析在给用户的输出里标注为 "In-Session Pipeline"，而不是含糊地说"深度分析"——
   保持前面 General Guidelines 里"披露产出模式"的原则。

### 如何使用 pipeline 输出

- `briefing.json`: `overall_signal`、`conviction.score` (−1.0~+1.0)、`conviction.signal_convergence`
  (0=四层分歧, 1=完全一致)、`executive_summary`、`bull_case`/`bear_case`、`key_uncertainties` ——
  这是给用户的核心结论，直接引用 conviction score 和 convergence，不要重新编一套自己的判断。
- 如果 `signal_convergence` 低（<0.5）或 conviction 接近 0，**明确告诉用户这是"分歧大/低把握"的信号**，
  不要把它包装成一个干脆的 Buy/Sell。
- `technicals.json` / `fundamentals.json`: 补充具体数字（RSI、P/E、支撑位）到输出表格里。
- 把 `key_uncertainties` 列进 "⚠️ Review / At Risk" 或单独一节，让用户知道结论背后没解决的问题是什么。
