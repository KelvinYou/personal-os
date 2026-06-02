# Malaysia Wealth Vehicles & Tax — 本地化方案

> wealth-manager 在做储蓄分配、税务优化、ETF 选择时的 MY 本地知识库。
> 美国博客讲的 401k/Roth IRA/HSA 对马来西亚人无效——本文件是这些概念的 MY 对应物。
>
> **最后研究日期: 2026-06-02。** 税务额度按 YA 2025（2026 报税）；利率随时变。
> 引用具体利率/额度前务必 WebSearch 核对（见 SKILL.md Data Freshness 节）。

---

## 1. 税务优惠额度 — Malaysia 版的"税优账户"

马来西亚没有 Roth IRA，但有几项 individual tax relief 能直接降低应税收入。对一个月存 RM3k、
年收入大概率落在 21–24% 边际税率的 25 岁上班族，**用满相关 relief = 确定性最高的一笔回报**。

| Relief | 上限 (YA2025) | 对用户的意义 | 备注 |
|--------|--------------|-------------|------|
| **EPF / KWSP** | RM4,000（与人寿险合计上限 RM7,000） | 月薪 ≥ RM36,364/年 时，11% 强制缴款已自动顶满 | 多半已自动达标，无需额外动作 |
| **PRS（私人退休金）** | RM3,000，**独立于 EPF** | ⭐ 最值得主动做的一步：21–24% 税率下，存 RM3,000 当年省税约 RM630–720 | relief 延长至 YA2030；55 岁前提取受限/被罚税 |
| 人寿/Takaful 保费 | 与 EPF 合计 RM7,000 内 RM3,000 | 有保单才用得上 | |
| 医疗/教育保险 | RM3,000 | 商业医疗卡保费可计 | |
| Lifestyle（书/电子/健身/上网） | RM2,500 | 顺手即可，不为省税专门消费 | |
| SSPN（子女教育储蓄） | 净存款 RM8,000 | 用户暂无子女，忽略 | YA2025 起每孩仅一位家长可claim |

**PRS 的正确定位**：它的钱锁到 55 岁、且基金选择有限、费用高于自购 ETF。所以**不要**把 PRS 当成
股票 core 的替代品。把它当作组合里"税务优化的防御/退休 sleeve"——用 RM3,000/年 换确定的税务回报，
仅此而已，余下资金仍走指数 core（§3）。给建议时要明确这个 trade-off，别让用户为省税牺牲流动性与成长。

> 决策口径：先确认用户的边际税率（问年收入或看 daily 日志推算）。若边际税率 ≥ 19%，PRS RM3,000 值得做；
> 若还在免税/3% 档（年应税 < RM35k），税务回报太小，不如把这笔钱直接投指数 core。

---

## 2. 现金 / 储蓄分层 — MY 工具落地（2026 行情）

呼应 playbook §1 的应急金与专项目标。具体工具（**利率会变，引用前核对 interest_rates.yaml + WebSearch**）：

| 层级 | 用途 | 2026 大致行情 | MY 工具示例 |
|------|------|--------------|-------------|
| 即时流动 | 日常 + 起步应急 | 0–2% | TNG GO+、传统活期 |
| 高息活期/数字银行 | 完整应急金（要随取随用） | 2–4% | GXBank（~2%，每日计息）、Ryt（高息储蓄可达 ~4%/pots ~3%）、Boost、AEON |
| 货币基金 MMF | 短期停泊（<6 月）、收益略高于活期 | ~3–3.7% | 各家 cash management（如券商 MMF）；非 Bumi 可用作 ASB 替代 |
| 定存 FD | 锁定期可接受的中期资金（6–12 月） | 标准 2.6–3.3%；promo（fresh fund）3.5–4.0% | 各行 promo，盯 rates.my 比价 |
| ASB / ASNB | 长期保本增值 | ASB 历史派息 5.5%+（**仅限 Bumiputera**） | 非 Bumi → ASNB 固定价格基金 / MMF 替代 |

要点：
- **应急金别锁 FD**——要随取随用，放数字银行高息活期。
- **过剩现金别长期躺活期**——长期被通胀蚀本金，按 playbook §3 部署进 core。
- 用户档案：非 Bumiputera 的话 ASB 用不了，对应替代是 ASNB 固定价格基金或 MMF；这点在建议里要先确认。

---

## 3. 全球指数 ETF — Malaysian 投资者的正确买法（重要）

用户在 moomoo 直接买**美国上市**的美股/ETF。这有两个常被忽略的税务陷阱，长期会侵蚀回报。
给 core 选标的时，**优先推荐爱尔兰注册（Ireland-domiciled）UCITS ETF**，而非美国上市 ETF：

### 陷阱 A — 股息预扣税 30% vs 15%
- 非美国人直接持美国上市 ETF/股票，股息被预扣 **30%**。
- 通过爱尔兰注册 UCITS ETF 持有同样的底层资产，凭爱尔兰—美国税收协定，基金层面预扣降到 **15%**。
- 对长期复利，这 15% 的差额逐年累积，非常可观。

### 陷阱 B — 美国遗产税（estate tax）40% 的尾部风险
- 非美国居民直接持有的"美国 situs 资产"（含**美国上市股票/ETF**），超过 **USD 60,000** 免税额的部分，
  身故时面临最高 **40%** 的美国遗产税。
- **关键**：通过 moomoo 等外国券商持有**不改变** situs——美国上市股票仍算美国资产，仍受此约束。
- 爱尔兰注册 UCITS 基金**不是**美国 situs 资产 → 这层风险直接消失。
- 这正是"任何认真投全球股票的马来西亚人都应通过 UCITS 而非美国上市基金"的核心理由。

### 推荐 core 标的（爱尔兰注册 UCITS, Acc 累积型，自动再投资）
| Ticker | 跟踪 | TER | 说明 |
|--------|------|-----|------|
| `VWRA` | FTSE All-World（全球发达+新兴） | 0.22% | 一只全球分散，core 首选 |
| `CSPX` | S&P 500 | 0.07% | 只要美国大盘、费用更低 |
| `VUAA` | S&P 500 | 0.07% | CSPX 的 Vanguard 等价物 |

操作要点：
- 开户时填 **W-8BEN**，券商会自动按 15% 处理预扣。
- 选 **Acc（accumulating）**版本——股息自动再投资，省去手动复投，也利于 MY 投资者（无需处理派息）。
- 这些 ETF 多在 LSE（伦敦）等交易所以 USD 交易；确认 moomoo 是否支持，或用支持 LSE 的券商
  （如 IBKR）。**用户当前可能没在用 UCITS——这是给方案时最具体、最高价值的一条升级建议。**

> 注意：满足 satellite 里的个股偏好（如想直接持 NVDA/特定美股）时，直接持美国上市股仍可以——
> 只是要让用户知道这部分有 30% 股息预扣 + 遗产税敞口，所以 core（大头）走 UCITS 更优。

---

## Sources（2026-06 检索，定期复核）

- RinggitPlus — 2026 报税 tax relief 全清单: https://ringgitplus.com/en/blog/tax/everything-you-can-claim-as-income-tax-relief-in-malaysia-2026-filing-for-ya-2025.html
- LHDN/HASIL 官方 tax reliefs: https://www.hasil.gov.my/en/individual/individual-life-cycle/income-declaration/tax-reliefs/
- EPF vs PRS 对比: https://emasgold.com.my/comparing-epf-and-prs-contributions-for-effective-retirement-planning-in-malaysia-2026-13/
- 数字银行/FD 行情: https://wise.com/my/blog/best-digital-bank-malaysia ; https://ringgitwise.co/blog/best-fixed-deposit-rate-malaysia-2026 ; https://rates.my/
- 爱尔兰注册 ETF 降预扣税: https://www.ziet.co/investing/ireland-domiciled-etf/ ; https://www.bogleheads.org/wiki/Nonresident_alien_investors_and_Ireland_domiciled_ETFs
- 美国遗产税（非居民 USD 60k 门槛）: https://www.irs.gov/businesses/small-businesses-self-employed/estate-tax-for-nonresidents-not-citizens-of-the-united-states ; https://www.bogleheads.org/wiki/Nonresident_alien_taxation
