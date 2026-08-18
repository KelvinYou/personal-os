# Investment Decision Framework

Wealth-manager 做投资分析和建议时的决策框架。主 SKILL.md 定义工作流，本文件存放投资哲学和判断准则。

> **本文件只覆盖 satellite 层（个股选择）。** 整体方案骨架——资金分层、资产配置、core-satellite、
> 再平衡、DCA 证据——见 `wealth-building-playbook.md`；MY 税务/工具/UCITS ETF 见 `malaysia-wealth-vehicles.md`。
> 做个股建议时务必同时看组合是否已有 index core，别让用户只堆 satellite。

## Investor Profile Inputs

This framework does not embed a personal age, broker, cash balance, income, or risk tolerance. Read those from the
runtime finance files and user profile before applying the framework. The relevant trade-offs are:

- **Long horizon / growth**: a long, verified horizon can justify tolerating short-term drawdowns for higher expected
  return; a short horizon or near-term liability should lower equity risk.
- **Risk capacity vs. risk tolerance**: stable cash flow and a sufficient emergency reserve may support volatility,
  but the allocation must still be one the investor can hold through a drawdown.
- **Buy-the-dip vs. momentum**: match the decision to verified cash-flow cadence and portfolio policy, not a baked-in
  monthly amount.

## 单股分析框架

### Buy 条件（至少满足 2/4）
1. **估值折扣**：P/E 低于行业平均 or 低于自身 5 年均值
2. **价格位置**：距 52 周高点 >15%，且在技术支撑位附近
3. **基本面完好**：最近一季营收/利润同比增长，无重大负面事件
4. **催化剂**：有明确的价值释放事件（财报、新产品、政策利好）

### Watch 条件
- 基本面好但价格还没到位（距支撑位还有 >5% 空间）
- 或者有不确定因素待解（财报即将公布、监管审查中）

### Hold 条件
- 已持有，基本面未恶化，但价格不在加仓区间

### Avoid / 考虑止损的信号
- **基本面恶化**：连续 2 季营收下滑、管理层变动、行业结构性逆风
- **技术破位**：跌破关键支撑且无反弹迹象
- 注意区分"暂时性回撤"和"基本面恶化"——前者是买入机会，后者是止损信号。
  判断标准：导致下跌的原因是**一次性事件**（关税、短期供应链问题）还是**结构性变化**
  （市场份额持续流失、技术路线被颠覆）

### 止损纪律
- 单只股票亏损 >25% 且基本面恶化 → 强制 review，倾向止损
- 单只股票亏损 >25% 但基本面完好 → 视为加仓机会，但需确认不是在"接飞刀"
  （检查：下跌是否有明确底部支撑？同行是否也在跌？机构是否在增持？）

## 组合层面分析

每次做 stock analysis 时，除了分析单只股票，还应评估组合整体健康度：

### 集中度风险
- 单只股票不应超过组合总值的 30% — 因为即使基本面好，单一公司的黑天鹅事件
  （财务造假、突发监管）无法预测，分散是唯一的免费午餐
- 单一行业不应超过 50% — 行业轮动是常态，过度集中会放大周期性波动

### 地域/货币分布
- 美股持仓按 USD 计价，受 USD/MYR 汇率影响
- 当美元走强时，美股的 MYR 回报会被放大；反之亦然
- 分析时应同时展示 USD 原始回报和 MYR 折算回报，让用户看到真实的本币收益

### 行业相关性
- 如果多只持仓高度相关（如 MSFT/NVDA/META 都是美国大型科技股），
  要明确提示"这些股票在大盘回调时会同步下跌，分散效果有限"
- 建议时考虑与现有持仓的互补性（不同行业、不同市场、不同风格）

## 仓位管理 — DCA 策略

按 `data/finance/portfolio.yaml` 或 policy 中已验证的可投资现金流制定分批逻辑：

- **基础原则**：不要一次 all-in，用 2-3 个月的资金分批建仓
- **市场正常时**：按月定投到目标标的
- **明显低估时**（指数级别回调 >10%）：可以加速投入（把 2-3 个月的额度集中使用），
  但仍保留至少 1 个月的现金缓冲
- **估值偏高时**：减缓投入，积累现金等待机会
