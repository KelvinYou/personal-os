# Plan: 个人理财仪表盘 (Tracked Assets Dashboard)

> Status: **v3 — Phase A / B / C ✅ 已完成 (2026-08-11) · Phase D–E 待实施**
> Owner: Kelvin
> 修订: v3 — 2026-08-11，基于对仓库实际状态的核实重写
> 相关 repo: `data` (submodule, private) · `repos/ai-stock-analysis` (submodule, **public**)

---

## 0. v3 相对 v2 的变更

v2 的两个前提在核实后已经不成立，其中一个推翻了主架构。

| # | v2 的说法 | 核实结果 | 影响 |
|---|-----------|----------|------|
| 1 | "两个 repo 的 public/private 状态待确认" | `ai-stock-analysis` = **PUBLIC**，`personal-os-data` = **PRIVATE** | **主架构改向**：仪表盘不再做进 `ai-stock-analysis` |
| 2 | "`data` submodule 未 checkout，无法确认字段名，这是前置阻塞" | 已 checkout，`data/finance/` 三个文件均在 | 阻塞解除 |
| 3 | 未提及 `savings.yaml` | 存在，且已是 cash 持仓的 source of truth | Phase 1 从"设计 schema"降级为"补齐校验" |
| 4 | Phase 0 建 append-only 写入路径，列为最高优先 | `data` 是 private git repo，history 天然 append-only | **Phase 0 删除** |
| 5 | Phase 4 = unit trust / MMF 的 NAV 与 P&L | 无 unit trust 持仓；标 `mmf` 的账户实为按利率计息 | **Phase 4 删除**（空集合） |
| 6 | Phase 3（FD 到期监控）排第三 | `gxbank` FD **2026-09-03 到期** | **提为 Phase A**（唯一有真实 deadline 的模块） |

v2 中判断正确、v3 原样保留的部分：按**经济行为**而非 vehicle 名称分流；Net Worth → Tracked Assets 改名；拒绝为 `listTickers()` 引入整套 snapshot module；不在 UI 前铺 validator + fixtures + 通用 generator 的脚手架。

---

## 1. 动机与架构改向

### 1.1 原动机（不变）

`wealth-manager` skill 已积累 MMF / FD / unit trust / digital bank 的知识
（`references/malaysia-wealth-vehicles.md`、`references/wealth-building-playbook.md`、
`data/finance/interest_rates.yaml`），但这些内容只活在 prose markdown 里，
从未被浏览、对比或结构化查询过。同时没有任何"我的钱分布长什么样"的总览视图。

### 1.2 为什么不能做进 `ai-stock-analysis`

```
KelvinYou/ai-stock-analysis   →  PUBLIC   (MIT license, README badge, 作品集项目)
KelvinYou/personal-os-data    →  PRIVATE
```

且 `ai-stock-analysis` 配有 **daily fetch GitHub Action，会自动 commit `data/`**。
任何落进该目录的文件不是"可能被提交"，而是**会被自动推上公开仓库**。

v2 把这件事写成"落盘位置待定"。实际它不是落盘细节，而是架构冲突：
把净资产仪表盘做成一个刻意公开的作品集 repo 的 feature，等于亲手拆掉
private/public 的隔离——而 v2 自己也承认那个隔离是有意为之。

### 1.3 改向后的架构

仪表盘做成 **personal-os 下的 local-only web app**（`/web/`），
把 `repos/ai-stock-analysis/data/<TICKER>/` 当作**只读数据源之一**消费。

```
personal-os/web/                    ← 新增，local-only，不部署
  ├─ 读 data/finance/*.yaml         ← private submodule，持仓与现金
  └─ 读 repos/ai-stock-analysis/    ← public submodule，只读 ticker 分析产物
     data/<TICKER>/*.json
```

收益：
- 财务数据一行都不进公开仓库；`ai-stock-analysis` 继续作为作品集独立演进。
- 股票与财务保持**两条独立读取路径**——正是 v2 Phase 2 想要的效果，
  这里作为架构副产品免费得到，不需要专门设计。
- `ai-stock-analysis` 继续作为公开的行情/研究数据源；它不读取 private holdings，
  portfolio valuation、concentration 和 sizing 由 `personal-os` 自己负责。

---

## 2. 现状盘点

### 2.1 数据层：`data/finance/`（private submodule，已 checkout）

| 文件 | 角色 | `updated` | 状态 |
|------|------|-----------|------|
| `savings.yaml` | **真实现金持仓** + liabilities | 2026-06-02 | **stale 70 天** |
| `portfolio.yaml` | 股票持仓 + investor profile | 2026-07-17 | |
| `interest_rates.yaml` | **市场利率 catalog** | 2026-07-17 | |

v2 设计的 "holding facts / rate catalog" 三层分离，**大部分已经实现**：
`savings.yaml` 的文件头注释就写着「与 interest_rates.yaml 区分：那个是市场利率参考表，
这个是真实持仓」。缺的只是第三层 **valuation observation**（把推导值从手写变成算出来）。

### 2.2 已存在的数据债务（Phase 1 的真实工作内容）

v2 只点出了股票 current price 的双 owner 问题。实际范围更广，且**已在产生偏差**：

1. **手写推导值**：`savings.yaml: summary.*` 四个字段（`total_cash` /
   `weighted_avg_rate` / `liquid_now` / `locked`）全部是可计算量，却靠注释
   「更新账户后请同步此处」维持。
2. **跨文件手工同步**：`portfolio.yaml: total_savings` 与
   `savings.yaml: summary.total_cash` 是同一个数字的两份手抄。
3. **staleness skew 已发生**：`savings.yaml` 停在 06-02，另两个在 07-17。
4. **分类与利率两边对不上**：`savings.yaml` 记 boost_bank 为 `type: mmf, rate: 3.30`；
   `interest_rates.yaml` 归其为 digital bank，`base 2.50 / promo 4.00`。
5. **持仓数据泄漏进 rate catalog**：`interest_rates.yaml` 的 `ryt_bank.notes` 里
   写着用户在该账户的具体持仓额，并据此断言"仍按 4% 计息"——市场利率表里
   混进了持仓事实，正是三层分离要治的病。**用它当 Phase 1 的验收用例。**
6. **股票 price 双 owner**（v2 已指出）：`portfolio.yaml` 内联 `current_price*`，
   `ai-stock-analysis/data/<TICKER>/` 也有价格。必须定唯一 owner。

### 2.3 `ai-stock-analysis` 侧

- **Pipeline**：`RiskChecker`（deterministic，无 LLM）等模块专属于股票，
  **不要**强行抽象成通用资产分析模块。
- **UI**：`web/app/page.tsx` · `[ticker]/page.tsx` · `dashboard/page.tsx`，
  全部假设"资产 = 一个 ticker"。改向后这三个页面**零改动**。
- **`listTickers()` 隐患**（`web/lib/data.ts:84`，已核实）：裸 `readdir` +
  `isDirectory()`，对目录名无格式校验。`DATA_DIR` 默认指 `../data`，
  仅当 `STOCK_DATA_DIR` 被改指上层目录时才会把 `finance/` 渲染成 ticker 页。
  改向后风险进一步降低。**修法：加一条 ticker 正则。** 优先级低，
  不为它引入任何 module。

---

## 3. 目标架构：三层分离

1. **知识层 (Knowledge)** — 静态参考资料（税务规则、ETF 扣税、PRS 减免、
   各 vehicle 一般特性）。保持 markdown，但应能在 UI 里浏览/分类导航。

2. **数据层 (Positions)** — 用户实际持有的东西，拆三类：
   - **Holding facts**：账户、余额、份额、成本价、锁定期。
   - **Valuation observation**：`current_value` 是**推导值**，不手工填写。
   - **Rate catalog**（产品属性，非持仓属性）：年化方式、tier/cap、promo 条件、
     流动性、PIDM 保障、有效期。

3. **分析层 (Analysis)** — 按**经济行为**分流，不按 vehicle 名称分流：
   - **Market-valued**（有价格/NAV，会涨会跌）：stock、ETF、unit trust、真 MMF
   - **Yield / maturity**（有利率和到期日）：FD、digital bank、按息计的储蓄
   - **Cross-asset**：allocation、FX exposure、liquidity、数据 freshness

### 3.1 命名：Tracked Assets，不叫 Net Worth

叫 Net Worth 会给出"精确但错误"的总资产数字。除 v2 已列的理由外补一条硬约束：
`savings.yaml` 的 liabilities 段**明确只记月供 + 结束日期，不追踪 outstanding 本金**
（只有 `monthly_debt_service` 一个月供合计，房贷建期利息 + 车贷分列，均无本金）。
净资产**在数据层就算不出来**——这不是命名偏好问题。

若日后坚持要用 Net Worth，必须先定义全部五项：base currency（建议 MYR）、
FX rate 与 valuation timestamp、allocation 的分母、stale/unpriced 资产的处理、
liabilities 与 excluded assets 的范围。

---

## 4. 分阶段计划

> 排序原则：**有真实 deadline 的排最前**，其次是不可逆的，其余按能否事后重构排。

### Phase A — FD / digital bank 到期与利率监控 ⏰ ✅ 已完成 (2026-08-11)

**为什么排第一**：纯计算、无 LLM、不依赖 NAV、不依赖新 schema，
且 `gxbank` FD **2026-09-03 到期（约 3 周后）**——唯一有硬 deadline 的模块。

**交付**：`make wealth`（可选 `DATE=` 预演未来日期）

| 文件 | 作用 |
|------|------|
| `scripts/lib/wealth/` | pydantic 模型 + 到期/候选/cap/staleness 全部纯函数（审计 §3.9 拆包）|
| `scripts/wealth_check.py` | CLI，`[Status: OK/Warning/Critical]` 输出 |
| `config/thresholds.yaml` `wealth:` 块 | 5 个阈值，无硬编码魔法数字 |
| `tests/test_wealth.py` + `tests/fixtures/finance/` | 23 tests；跑 fixture 而非真实持仓，更新持仓不会让测试变红 |

**验收结果**：跑出 `gxbank` 2026-09-03 到期告警（Warning，剩 23 天；`DATE=2026-09-01`
时升级 Critical）。候选去处唯一通过筛选的是 **versa_cash 5.50%（+1.50%）**。

实施中发现并处理的三件事：

1. **两个 promo 其实已经过期**，`interest_rates.yaml` 只把日期写在 prose notes 里：
   `cimb_bank` eFD-i（2026-08-03 止）、`aeon_bank` Savings Pots（2026-05 止）。
   已把这三处（含 `standard_chartered` 2026-09-30）转成结构化 `promo_valid_until`。
   **没有这个字段，工具会推荐一个已经关闭的 CIMB 3.60% 活动。**
2. **`cimb_bank` 只有 promo_rate、没有 base_rate**，promo 过期后会从候选列表里
   **静默消失**——读起来像"评估过后被拒"，实际是根本没参与评估。改为以
   `rate=None` 显式列出并说明原因。`general_board_rates`（只有 prose `rate_range`）同理。
3. **cap headroom 交叉引用**：`ryt_bank` 4.00% 看似平配，实际余额已顶到
   promo cap 的 98% 以上，剩余 headroom 不到 cap 的 2%，迁入无意义。
   工具现在自动交叉核对 `savings.yaml` 的 cap。

**已知限制**（留给 Phase B）：promo 的 spend 条件、stamp 数、tier 表仍是 prose，
工具只能原样透传 `notes`，不做结构化判断。

### Phase B — 数据债务清理（原 Phase 1）✅ 已完成 (2026-08-11)

不是"设计新 schema"，是**消灭手写推导值 + 对齐已有 schema**。

**价格归属决策：以 ai-stock-analysis pipeline 为准。**
`portfolio.yaml` 只留 holding facts（`shares` / `avg_cost`），现价从
`repos/ai-stock-analysis/data/<TICKER>/technicals.json` 的 `close` + `as_of_date` 读取
（马股按数字 `code` 查，不是 symbol）。

| 债务项 | 处理 |
|--------|------|
| `summary.*` 四字段手写 | 从 `savings.yaml` **移除**，改由 `make wealth` 推导。不做回写同步任务——没有第二份就没有漂移 |
| `total_savings` 跨文件重复 | 从 `portfolio.yaml` 移除，现金唯一归 `savings.yaml` |
| 股票 price 双 owner | 移除全部 `current_price*`；未覆盖标的用显式 `manual_price` + `manual_price_as_of` 兜底 |
| `ryt_bank` 持仓泄漏进 rate catalog | 持仓引用迁回 `savings.yaml`（连带记下 4% 需 opt-in 的未核实状态）|
| boost_bank 分类/利率冲突 | **不猜**——工具报冲突，人工定夺（见下）|
| staleness | 三个 yaml 的 `updated` + 每个持仓的价格 `as_of` 都纳入检查 |

**新增能力**：`make wealth` 现在同时输出现金汇总、股票估值/P&L、价格来源与新鲜度、
跟踪资产合计。测试 36 个，跑 fixture（含一份 pipeline 价格 fixture），不碰真实持仓。

实施中发现的三件事：

1. **手写价格已经严重过期**，这直接印证了归属决策。手写价停在 07-17，pipeline 是 08-07：
   MSFT `401.10 → 499.99` (+24.7%)、META `666.62 → 592.10` (−11.2%)、
   GAMUDA `4.15 → 4.46` (+7.5%)。按旧数据算出来的组合估值和 P&L 全是错的。
2. **`SIME` (4197) 不在 pipeline watchlist 内**，是唯一使用手工兜底价的持仓，
   现已显式标记来源与 25 天账龄。最干净的修法是把 4197 加进 ai-stock-analysis 的
   watchlist，然后删掉兜底字段。
3. **`boost_bank` 的 3.30% 在 catalog 里对不上任何档位**（base 2.50 / promo 4.00）。
   哪个数字是真的取决于用户实际在哪个 tier，两个文件都推不出来——
   工具报冲突并明说"不替你选一个数字"，**留待人工确认**。

**同步改动**：`wealth-manager` skill 原本在 §5 指示 WebSearch 后回写 `current_price`
到 `portfolio.yaml`，与新归属直接冲突，已改写为"跑 pipeline，不要手补 YAML"，
并新增 Price Ownership 一节。

### Phase C — Tracked Assets Overview 页（原 Phase 2）✅ 已完成 (2026-08-11)

**交付**：`make web` → `localhost:3000`（Next 15 + Tailwind，local-only，不部署）

**关键实现决策：页面不重算任何东西。**
所有数字来自 `scripts/wealth_check.py --json`——`make wealth` 用的同一份代码。
在 TypeScript 里重写估值数学，等于把 Phase B 刚从数据文件里消灭的 dual-owner 漂移
原样搬到代码层。`lib/report.ts` 只做三件事：起子进程、解析 JSON、渲染。
改口径只改 `scripts/lib/wealth/report.py`，CLI 和网页一起变。

为此给 CLI 加了 `--json`，并把渲染重构成 `build_report()` → `render_text()`
两段——报告 dict 现在是 CLI 与网页共同的契约，有测试守着（JSON 可序列化、
合计等于各部分之和、配置占比合 100%）。

页面结构（按"先说数据可信度，再说数字"排）：
数据健康 → KPI 行 → 资产配置（堆叠条 + 表）→ 到期监控 → 股票 → 现金与储蓄。

**验收结果**：配置图跑出四个桶（MMF / FD / 股票 / 钱包），占比合 100%；
具体百分比见 `make wealth` 输出，本文件是 public repo，不落实际配置数字。
stale 与 unpriced 全部显式标记：`SIME` 标"手工兜底 + 过期 25 天"，
`savings.yaml` 标"陈旧 70 天"，`ryt_bank` 标"未核实 + 接近 cap"，
boost_bank 利率冲突单列一行。无价格持仓不计入合计，并写明"合计因此偏低而非静默补零"。

配色按 dataviz 规范做了：分类色板 4 槽固定顺序（色相跟随类别而非排名），
`validate_palette.js` 双模式全绿；light 模式 contrast 触发 WARN → 按 relief 规则
配直接标签 + 完整表格，颜色从不是唯一通道；状态色独立于序列色，且始终带图标 + 文字。

**顺带修的**：`make wealth` 在有 Warning 时会被 make 报成 `Error 1`，与 `make check`
的约定不一致（那个也打 Critical 但退出 0）。改为默认退出 0，
新增 `--strict` 给 cron/CI 用。

### Phase D — 知识库浏览页

- 把 `malaysia-wealth-vehicles.md` 等参考文档结构化展示。
- 先做最简 markdown 渲染 + 分类导航，不一步到位做搜索。

### Phase E — 历史趋势展示

- **写入侧无需新建**：`data` 是 private git repo，每次编辑 `savings.yaml`
  即一个天然 snapshot。历史用 `git log -p finance/savings.yaml` 重建。
- 本阶段只做**读取与展示**，可安全推迟。

### 已删除的阶段

- ~~Phase 0 — append-only 写入路径~~ → git history 已提供，见 Phase E。
- ~~Phase 4 — unit trust / MMF NAV 与 P&L~~ → 当前**无 unit trust 持仓**；
  `savings.yaml` 中标 `mmf` 的 ryt / boost / tng 实为按利率计息的储蓄产品，
  归属 Phase A。此阶段目前是空集合，留在计划里只会误导排期。
  待真正持有 NAV-based 产品时再重开，届时前置条件仍是"有可靠 NAV 源，
  否则不做"——**不用手填数字凑假估值**。

---

## 5. 待确认

- **`boost_bank` 实际利率**：`savings.yaml` 记 3.30%，catalog 只有 base 2.50 / promo 4.00。
  需登录确认实际 tier（Basic Savings / Savings Jars / BoostUP Jar），再把两边对齐。
- **`ryt_bank` 4% 是否仍生效**：2026-06-18 起改为需主动 opt-in bonus campaign。
  当前按 4.00% 记账并标了 `rate_unverified: true`；若实际已回落到 base 2.05%，
  加权平均利率会从 3.74% 降到约 3.14%。
- **是否把 SIME (4197) 加进 ai-stock-analysis watchlist**，以消除唯一的手工兜底价。

### 已关闭

- ~~股票 current price 的唯一 owner~~ → ai-stock-analysis pipeline，见 Phase B。
- ~~`personal-os/web/` 是否部署~~ → 不部署，localhost only。见 Phase C 与 `web/README.md`。

- ~~两个 repo 的 public/private 状态~~ → 见 §1.2，已确认。
- ~~`data` submodule 是否 checkout / 字段名~~ → 已 checkout，见 §2.1。
- ~~总览要不要包含历史趋势~~ → git history 已是 append-only，展示推迟到 Phase E。
- ~~unit trust / MMF 的 NAV 从哪来~~ → 无相关持仓，阶段已删除。
