# Wealth-Building Playbook — 整体理财方案框架

> 这是 wealth-manager 的**整体方案层**。`investment-framework.md` 解决"买哪只股票"，
> 本文件解决"钱应该怎么分层、按什么顺序投、组合骨架长什么样"。
> 本文件不假定当前持仓或券商；若 runtime portfolio 以个股为主，应把它视为 satellite，并检查 core 与资金分层是否缺失。
>
> **最后研究日期: 2026-06-02。** 利率/税务额度会变，引用具体数字前先核对（见文末 Sources + SKILL.md 的 Data Freshness 节）。

---

## 0. 核心诊断：从"选股"升级到"方案"

若投资者的做法是直接挑 MY/US 个股，这等于可能**只有 satellite，没有 core**——
若所有钱都压在高波动、需要主动判断的个股上，现代最佳实践（Bogleheads /
core-satellite 共识）是反过来的：

- **先搭 core（指数骨架）**：占组合 60–75%，用全市场低成本指数 ETF，闭着眼睛拿，捕获市场平均回报。
- **再加 satellite（高信念个股）**：占 25–40%，才是用户现在做的选股。允许 alpha，但即使全错，core 也能兜底。

研究反复证明：绝大多数主动选股者长期跑输指数；散户因频繁交易 + 追涨杀跌产生"行为缺口"
（behavior gap），实际回报比其持有的基金本身还低。core-satellite 的意义就是**用结构对抗人性**——
把大部分钱锁进无需判断的 core，把"想跑赢市场"的冲动限制在 satellite 里。

> 给用户做任何 stock analysis 时，都应在组合层面提醒：satellite 仓位是否已超过 40%？core 建了没有？

---

## 1. 资金分层 — Financial Order of Operations（先后顺序）

下一块钱该去哪，按"哪一步边际回报最高"排序。MY 本地化版本：

| 顺序 | 动作 | 目标额度 | 理由 |
|------|------|----------|------|
| 1 | **起步应急金** | RM3k–6k（1 个月开销） | 防止一遇意外就砍仓/借贷 |
| 2 | **清高息债** | 任何 >7–8% 的债（信用卡、PTPTN 除外按情况） | 还掉 18% 信用卡 = 无风险 18% 回报，没有投资能稳定跑赢 |
| 3 | **完整应急金** | 3–6 个月开销，放高流动性高息处（见 malaysia-wealth-vehicles.md） | 投资前的安全垫；让你能在熊市拿得住 |
| 4 | **税务优惠额度** | PRS RM3,000/年（见 §税务） | 一次性约 21–24% 的"税务回报"，是确定性最高的一步 |
| 5 | **指数 core 定投** | 月现金流主力 | 全球/美股指数 ETF，长期复利引擎 |
| 6 | **satellite 个股** | core 建好后的余量 | 用户现在做的选股，限制在 25–40% |
| 7 | **专项目标** | 买房/进修等 | 用对应期限的工具（FD/MMF/债），不要用高波动资产 |

**关键判断**：应急金没满之前，不要把全部现金投进股市；高息债没清之前，投资是负和的。
若已验证现金储备覆盖第 1–3 步，重点是把第 3 步以上的"过剩现金"
按 §3 部署，而不是无限囤现金（现金长期被通胀侵蚀）。

---

## 2. 资产配置骨架 — 年龄与风险匹配

对具有 30+ 年周期、moderate-growth 风险承受力的投资者，常见参考是 **85–90% 股票 / 10–15% 防御资产（债/现金/MMF）**。
不要因为"moderate"就压到 60/40——那是接近退休的配置，年轻人最大的资产是时间，过度保守反而是风险。

### 推荐 core 骨架（三选一，复杂度递增）

**A. 极简一只（推荐起步）**
- 100% 全球股票指数：`VWRA`（Vanguard FTSE All-World, Acc, 爱尔兰注册, TER 0.22%）
- 一只搞定全球分散，自动再投资，无需再平衡。适合还在累积期、不想操心的人。

**B. 经典三基金（Bogleheads three-fund 的本地化）**
- 60% 美股全市场（`CSPX` S&P500 或 `VWRA` 的美国部分）
- 20% 国际股票（除美外发达 + 新兴）
- 10–20% 防御（MY 债基金 / MMF / 现金）
- 2026 年该组合 10 年年化约 11%，总费率可低至 0.03–0.22%。

**C. Core-Satellite（最契合用户）**
- **Core 65–75%**：`VWRA` 或 `CSPX`（全球/美股指数）
- **Satellite 25–35%**：runtime portfolio 中的 MY + US 个股（按 investment-framework.md 选）
- 规则：satellite 总值不得超过组合 40%；单只 satellite ≤ 组合 15%（呼应 framework 的集中度上限）。
- 自检：若 satellite 连续 3 年跑不赢 core，把更多钱挪回 core。

> 若投资者已经在做 satellite，正确的方案是先检查 core 是否达到目标，再把选股限制为有边界的 alpha 尝试。

---

## 3. 投入节奏 — DCA vs Lump Sum（用证据说话）

- **Vanguard 研究（1976–2022, MSCI World）**：一次性投入（lump sum）在约 **68%** 的 12 个月周期里
  跑赢分批投入（DCA），因为市场上涨月份多于下跌月份。所以**有一笔已验证的过剩现金时，
  尽快部署 > 慢慢 DCA**——除非估值明显偏高或心理上扛不住。
- **若主资金是每月定量流入**（金额读 `data/finance/portfolio.yaml` 的
  `investor_profile.monthly_savings`）——这本质上就是 DCA，不是 lump-sum 的对立选择，而是
  现金流的自然形态。继续按月定投 core 即可。
- **DCA 的真正价值是心理纪律**：能让人在熊市继续买、不踏空。如果一次性投入会让用户半夜睡不着、
  回调时恐慌割肉，那把过剩现金分 2–3 个月投入是值得的"安心溢价"。
- **回调时加速**：指数级别回调 >10% 时，把后续 2–3 个月额度集中投入 core（不是 satellite），
  保留 ≥1 个月现金缓冲。呼应 investment-framework.md 的 DCA 策略。

---

## 4. 再平衡纪律 — Rebalancing

不再平衡，组合会随上涨自动漂移成"高波动版"，风险悄悄放大。

- **频率**：每年一次（如每年 1 月）即可，过于频繁徒增成本与税。
- **阈值法（5/25 规则）**：当某资产类别偏离目标 **>5 个百分点**（绝对）或 **>25%**（相对）时再平衡。
  例：目标 core 70%，涨到 76% 或跌到 64% 时拉回。
- **优先用新增资金再平衡**：用每月新增资金优先补"低于目标"的部分，尽量少卖出（省手续费、避免实现盈亏）。
- satellite 跑赢导致占比膨胀时，再平衡正好强制"高位减仓 alpha、回补 core"——反人性但正确。

---

## 5. 行为纪律 — 对抗 behavior gap

最佳方案 90% 是行为，不是选股。给用户建议时反复强化：

- **不择时**：踏空的代价通常大于回调的代价；缺席市场最好的少数几天会severely拖累长期回报。
- **不追热点**：satellite 频繁交易者长期跑输持有者。新闻驱动的冲动交易是 alpha 杀手。
- **看年不看天**：30 年周期里，单日/单周波动是噪音。月度复盘看的是定投执行率，不是浮盈浮亏。
- **自动化优先**：能设自动定投就别手动——手动给了"这个月先不投"的心理缺口。
- **写下卖出理由**：买入时就定义"thesis 何时算破"（见 framework 的止损纪律），避免事后情绪化。

---

## Sources（2026-06 检索，定期复核）

- Vanguard — Lump sum vs cost averaging（68% 结论）: https://investor.vanguard.com/investor-resources-education/news/lump-sum-investing-versus-cost-averaging-which-is-better
- Bogleheads three-fund portfolio: https://www.bogleheads.org/wiki/Three-fund_portfolio
- Optimized Portfolio — 3-fund 2026 review: https://www.optimizedportfolio.com/bogleheads-3-fund-portfolio/
- Core-satellite 策略: https://waterloocap.com/core-satellite-investing-guide/ ; https://www.home.saxo/learn/guides/diversification/core-satellite-approach-a-smarter-way-to-diversify-your-investments
- Vanguard 资产配置模型: https://investor.vanguard.com/investor-resources-education/education/model-portfolio-allocation
- Money Guy — Financial Order of Operations: https://moneyguy.com/guide/foo/
