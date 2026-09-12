# ETF × 平台 净回报模型 — 2026-08-12

> **这份文件回答一个问题**：同样一笔钱、同样的底层指数，放在不同平台买不同注册地的 ETF，
> 十年下来「扣掉手续费、平台费、股息预扣税、汇兑成本」之后，年化到手回报差多少。
>
> **它不预测市场。** 毛回报是一个写死的假设（7%），对所有全球股票方案取同一个值 ——
> 这样表里的差异 100% 来自成本与税，不来自"我猜哪个指数会赢"。
>
> 数据检索日 2026-08-12。费率与 TER **会变**，引用超过 3 个月请重新核对（见 §6 来源）。

---

## 1. 结论先行

| # | 结论 | 量化 |
|---|------|------|
| 1 | **注册地比平台重要。** 爱尔兰注册 UCITS（CSPX/VWRA）对美国注册（VOO/VT）的优势来自股息预扣税，不是手续费 | S&P500 口径省 **0.19 pp/年**；全球口径省 **0.39 pp/年** |
| 2 | **moomoo 买不到 UCITS。** moomoo MY 只有 US / HK / SG / MY / CN-A 五个市场，**没有 LSE** —— 想买 CSPX/VWRA 必须开 IBKR | 这是结构性限制，不是费率问题 |
| 3 | **IBKR 的固定费必须靠批量摊薄。** 每笔 USD 1.70 佣金 + USD 2.00 换汇低消 = RM15.1 固定成本 | 月投 RM3,000 → 入场成本 0.50%；季投 RM9,000 → 0.17%。**改季投 = 白捡 0.07 pp/年** |
| 4 | **Robo（StashAway / Wahed）是最贵的一档**，贵在包装费不在交易 | 年化落后自购 UCITS **1.1–1.3 pp**；十年终值差 ~RM30,000 |
| 5 | **Bursa 上市的美股 ETF（0827EA）是两头挨打**：TER 0.475% 且基金层面仍吃 30% 预扣（马美无税收协定） | 比 CSPX@IBKR 差 **0.65 pp/年** |
| 6 | **美国遗产税不是远虑。** 按 RM36,000/年 投 VOO，USD 60,000 门槛约在**第 6 年**触及 | 现有 3 只美股 ~USD 1,000，尚安全；但这个计划会自己走过去 |

---

## 2. 十年 DCA 净年化（可比组：全球/美国大盘股票）

假设见 §4。毛回报统一 7.0%，年供 RM36,000，十年，总投入 RM360,000。

| 方案 | 平台 | 年度侵蚀 | 每笔入场成本 | **净年化 IRR** | 落后毛回报 | 十年终值 |
|------|------|---------:|-------------:|---------------:|-----------:|---------:|
| CSPX（爱尔兰 UCITS, S&P500）**季投** | IBKR | 0.258% | 0.168% | **6.691%** | 0.309 pp | RM502,335 |
| CSPX 月投 | IBKR | 0.258% | 0.503% | 6.626% | 0.374 pp | RM503,374 |
| SWRD（爱尔兰 UCITS, 发达市场）季投 | IBKR | 0.340% | 0.168% | 6.603% | 0.397 pp | RM500,091 |
| VOO（美国注册, S&P500）月投 | moomoo | 0.405% | 0.316% | 6.505% | 0.495 pp | RM500,240 |
| VWRA（爱尔兰 UCITS, 全球）季投 | IBKR | 0.470% | 0.168% | 6.464% | 0.536 pp | RM496,578 |
| VOO 月投 | Rakuten US | 0.405% | 0.633% | 6.443% | 0.557 pp | RM498,647 |
| VWRA 月投 | IBKR | 0.470% | 0.503% | 6.399% | 0.601 pp | RM497,516 |
| VT（美国注册, 全球）月投 | moomoo | 0.700% | 0.316% | 6.189% | 0.811 pp | RM492,184 |
| 0827EA（EQ8 DJ US Titans 50）月投 | Bursa 本地行 | 0.865% | 0.174% | 6.041% | 0.959 pp | RM488,437 |
| StashAway Growth | robo | 1.494% | 0 | **5.401%** | 1.599 pp | RM472,693 |
| Wahed Aggressive | robo | 1.503% | 0 | 5.392% | 1.608 pp | RM472,460 |

**怎么读这张表**

- 「年度侵蚀」= TER + 股息预扣税拖累 + 包装费，每年吃总资产。**这是复利级伤害。**
- 「入场成本」= 佣金 + 平台费 + 换汇，只吃当期新钱。**这是一次性伤害，随余额变大而稀释。**
- 所以 CSPX 月投的终值反而略高于季投（钱更早入场），但 IRR 更低（同样的钱花了更多手续费）。
  **IRR 是对的比较口径**；终值受入场时点影响，别用它排序。
- 最好 vs 最差是 **1.29 pp/年**，十年 RM30,000 —— 全部来自结构选择，一次决定，此后零维护。

### 同一张表换个问法：假如毛回报不是 7%

净年化 ≈ (1 + 毛回报) × (1 − 年度侵蚀) − 1 − 入场摊销。侵蚀是**乘性**的，
毛回报越高，同一个百分点的费率吃掉的绝对金额越多。上表的排序不随毛回报假设改变。

---

## 3. Bursa 上市 ETF 全清单（13 只）

这些的底层资产各不相同，**不能和 §2 共用一个毛回报假设** —— 所以这里只列成本，不列净回报。
共同的交易成本：佣金 ~0.10%（Rakuten 低至 RM1/笔）+ 清算费 0.03%，两者均加 **8% SST**
（2025-10-01 起 ETF/REIT/凭单的佣金与清算不再免 SST）；**印花税豁免至 2028 年底**。

| 代码 | 名称 | 底层 | TER | 备注 |
|------|------|------|----:|------|
| 0800EA | ABF Malaysia Bond Index | MYR 政府/准政府债 | ~0.35% ⚠️ | TER 未核实；债券 ETF 用 0.35% 吃收益，对比 KDI Save 3.88% 无锁定，**优势存疑** |
| 0820EA | FTSE4Good Bursa Malaysia | 马股 ESG | 0.59% | 管理费 0.50 + 信托费 0.05 |
| 0821EA | EQ8 DJ Islamic Malaysia Titans 25 | 马股 shariah | 0.49% | |
| 0823EA | Principal FTSE China 50 | 中国 H 股 | ~0.60% ⚠️ | TER 未核实 |
| 0824EA | EQ8 MSCI Malaysia Islamic Dividend | 马股高息 | 0.505% | |
| 0825EA | EQ8 MSCI SEA Islamic Dividend | 东南亚六国 | 0.775% | |
| 0827EA | EQ8 DJ US Titans 50 | 美国大盘（MYR 计价） | 0.475% | 见 §5 陷阱 C |
| 0828EA | TradePlus Shariah Gold Tracker | 实物黄金 | 0.76% | 黄金无股息，TER 就是全部持有成本 |
| 0829EA/EB | TradePlus S&P New China | 中国 ex-A | ~0.60% ⚠️ | 有 MYR / USD 两个柜台 |
| 0834EA | Kenanga KLCI Daily 2x Leveraged | KLCI 每日 2 倍 | ~1%+ ⚠️ | **每日重置，有波动衰减，不适合长持** |
| 0835EA | Kenanga KLCI Daily -1x Inverse | KLCI 每日反向 | ~1%+ ⚠️ | 同上 |
| 0838EA | VP-DJ Shariah China A-Shares 100 | 中国 A 股 | 0.90% | Bursa 最贵的一只 |
| 0839EA | EQ8 FTSE Malaysia Enhanced Dividend Waqf | 马股高息 + waqf | 0.74% | 部分收益捐出，非纯投资回报 |

⚠️ = TER 来自二手来源，未在基金 factsheet 上逐条核实。用到之前先查招股书。

**对用户的判断**：Bursa ETF 的 TER 普遍 0.5–0.9%，是 UCITS（0.07–0.22%）的 3–10 倍。
唯一站得住脚的理由是「不想有 FX 敞口 / 不想开海外券商」。**0828EA（黄金）** 是个例外 ——
它提供的是本地渠道拿不到的资产类别，0.76% 是为「实物黄金 + MYR 计价 + 交易所流动性」付的钱，
不是为一个能更便宜买到的指数付的钱。

---

## 4. 模型假设（全部可反驳）

| 参数 | 取值 | 来源 / 理由 |
|------|------|-------------|
| 年供 | RM36,000 | `data/finance/policy.yaml` → `cash_flow.monthly_investable_amount` × 12 |
| 期限 | 10 年 | 任意选定。期限越长，「年度侵蚀」权重越大、「入场成本」权重越小 |
| 毛回报 | 7.0% 名义总回报 | **假设，非预测。** 全球股票长期实际 ~5% + 通胀 ~2%。对所有 §2 方案取同值 |
| USD/MYR | 4.0806 | `market/fx.yaml`, as_of 2026-08-11 |
| VOO/CSPX 股息率 | 1.25% | S&P500 当前口径 |
| VT/VWRA 股息率 | 1.9–2.1% | 全球口径含较高派息的非美市场 |
| 美国注册 ETF 预扣 | 30% × 股息率 | 马美**无**税收协定，非美国人拿不到 15% 优惠税率 |
| 爱尔兰 UCITS 预扣 | 基金层面 15%（美国部分）；投资人层面 0% | 爱尔兰—美国税收协定；爱尔兰不对非居民征 ETF 派息税 |
| moomoo 换汇点差 | 0.15%（单向） | ⚠️ **假设。** moomoo 声明「换汇不收费」，但汇率内含点差且未公开。实测请自行核对 |
| Rakuten 换汇点差 | 0.30%（单向） | ⚠️ **假设**，同上 |
| IBKR 换汇 | 0.002%，低消 USD 2.00 | 官方费率，接近银行间价 |
| IBKR LSE ETF 佣金 | USD 1.70/笔 | ⚠️ Fixed 档口径；Tiered 档可能更低（~0.05%，低消 GBP 1），未逐条核实 |
| moomoo US | 佣金 0.03% + 平台费 USD 0.99/笔 + 交收 USD 0.003/股 | 官方费率表（180 天新客免佣期后的标准价） |
| Bursa ETF 交易 | 佣金 0.10% + 清算 0.03%，二者 ×1.08 SST；印花税豁免 | 2025-10-01 SST 扩围后口径 |
| StashAway | 0.8%（<RM50k 档）× 1.08 SST = 0.864% + 底层 TER | 官方定价页 |
| Wahed | 0.79% × 1.08 = 0.853% + 底层 TER | 二手来源 |

**没有建模的东西**（说清楚比假装全面重要）：

- 买卖价差（bid-ask spread）。Bursa 冷门 ETF 的价差可能比一整年 TER 还贵 ——
  0838EA / 0825EA / Kenanga 两只杠杆产品尤其要注意。
- 卖出时的成本。表里只算了买入；卖出还有 SEC/TAF（美股，极小）与再换汇回 MYR 的点差。
- 汇率涨跌本身。USD/MYR 十年的走向对终值的影响远大于上表所有费率之和 —— 但它不可预测，
  所以不在模型里。这不代表它不重要，只代表它不该被伪装成可计算。
- 税务居民身份变化、UCITS 基金层面的证券出借收益（可小幅抵消 TER）。

---

## 5. 三个结构性陷阱

**陷阱 A — 股息预扣税 30% vs 15%。** 非美国人直接持有美国注册 ETF，股息被预扣 30%，
且**不可抵扣**（马来西亚不对海外资本利得/股息征税，所以你没有可以拿去抵的税基）。
爱尔兰 UCITS 靠爱美税收协定把基金层面降到 15%，投资人层面 0%。
全球口径下这是 **0.39 pp/年**，十年复利下来不是零头。

**陷阱 B — 美国遗产税 40%。** 非美国居民持有的「美国 situs 资产」（含美国上市股票与 ETF），
超过 **USD 60,000** 免税额的部分，身故时面临最高 40% 美国遗产税。
**通过 moomoo 等外国券商持有不改变 situs。** 爱尔兰注册基金不是美国 situs 资产。

> **对本人的时间线**：现有美股 MSFT/NVDA/GOOGL 各 1 股 ≈ USD 1,000，远未触线。
> 但若按 RM36,000/年（≈USD 8,822）全投 VOO，7% 增长下约 **第 6 年**跨过 USD 60,000。
> 也就是说这不是「以后再说」，而是「现在选注册地，就不用以后处理」。

**陷阱 C — 本地包装不等于避税。** 0827EA 在 Bursa 用 MYR 买美国大盘，看起来绕开了美国。
实际上基金层面持有的仍是美股，同样吃 30% 预扣（马美无协定），
再叠加 0.475% 的 TER —— 所以它比 CSPX@IBKR **差 0.65 pp/年**。
它买到的是「不用开海外户 + 无 FX 敞口 + 非美国 situs」，代价明码标价。

---

## 6. 建议动作（按性价比排序）

1. **开 IBKR，core 走 CSPX 或 VWRA，季度定投**（不是月投）。
   相对现状（moomoo 买美股）年化 +0.19～0.30 pp，且顺手消掉遗产税敞口。
   代价：IBKR 不在 SC 监管与马来西亚投资者保护范围内 —— 这是要自己接受的 trade-off。
2. **不要用 robo 做 core。** StashAway/Wahed 年化落后自购 UCITS 1.1–1.3 pp。
   它们的价值在「零决策 + 自动再平衡」，如果自律不是问题，这个溢价不值。
3. **moomoo 保留给 satellite（个股）。** 现有 7 只个股全是 satellite，
   `policy.yaml` 的 `equity_sleeve.core_target_pct` 目前是 `null` —— 组合没有 core。
   这份文件解决的是「core 该买什么、在哪买」，**core 占比多少仍未定，需要先填 policy**。
4. **Bursa ETF 只在有独特资产类别时用**（0828EA 黄金）。用它买美股或马股宽基，
   TER 是 UCITS 的 3–10 倍，付出的钱买不到对应的东西。
5. **换汇成本自己实测一次。** 表里 moomoo 0.15% / Rakuten 0.30% 是假设。
   下次换汇时记下 app 成交汇率与当时中间价，差额就是真实点差 —— 一次实测胜过十次估计。

---

## 7. 复现方法

表格由下列模型生成。改假设重跑即可，不要手改表里的数字。

```python
# 净年化 = 现金流 IRR；余额按 (1+gross)*(1-drag)-1 复利，交易成本吃当期投入
def run(gross, drag, trades_per_year, fee_pct, fee_fixed_myr, years=10, annual=36000):
    per  = annual / trades_per_year
    step = ((1 + gross) * (1 - drag)) ** (1 / trades_per_year) - 1
    bal, flows = 0.0, []
    for _ in range(years * trades_per_year):
        bal = bal * (1 + step) + per * (1 - fee_pct) - fee_fixed_myr
        flows.append(-per)
    lo, hi = -0.9, 1.0                                   # 二分求 IRR
    for _ in range(200):
        mid = (lo + hi) / 2
        npv = sum(f / (1 + mid) ** (i + 1) for i, f in enumerate(flows)) \
              + bal / (1 + mid) ** len(flows)
        lo, hi = (mid, hi) if npv > 0 else (lo, mid)
    return (1 + (lo + hi) / 2) ** trades_per_year - 1

# drag      = TER + 预扣税拖累 + 包装费
# fee_pct   = 佣金% + 换汇点差%
# fee_fixed = 平台费/佣金低消/换汇低消，折算成 MYR（USD × 4.0806）
```

---

## 来源（2026-08-12 检索）

- moomoo MY 美股费率: https://www.moomoo.com/my/support/topic9_136 ; 定价页 https://www.moomoo.com/my/pricing
- moomoo MY 换汇: https://www.moomoo.com/my/support/topic9_33
- Rakuten Trade 费率: https://www.rakutentrade.my/fees ; https://www.rakutentrade.my/faqs/charges-and-fees
- IBKR 换汇与 LSE 费率: https://www.interactivebrokers.com/en/pricing/commissions-stocks.php
- Bursa 交易成本 / SST 扩围: https://www.bursamalaysia.com/trade/post_trade/transaction_costs_fees_charges
- Bursa ETF 全清单: https://myetf.com.my/etf/ ; https://www.bursamalaysia.com/sites/5d809dcf39fba22790cad230/assets/69f16052cd34aa6ec2f4ee0e/List_of_ETFs_March_2026.pdf
- StashAway 定价: https://www.stashaway.my/pricing
- 爱尔兰注册 ETF 预扣税: https://www.bogleheads.org/wiki/Nonresident_alien_investors_and_Ireland_domiciled_ETFs
- 美国遗产税（非居民 USD 60k 门槛）: https://www.irs.gov/businesses/small-businesses-self-employed/estate-tax-for-nonresidents-not-citizens-of-the-united-states

以上为个人分析参考，非投资建议。
