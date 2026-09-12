# 健康 App「免费人群 → B2B 合作变现」可行性与 Forecast — 2026-09-10

> **这份文件回答一个问题**：以 AI native solo dev 的身份做一个健康记录 App，
> 免费攒人群，然后靠健康餐 / 营养品 / 营养师 / 保险的合作分成赚钱 —— 这个模式的
> 成本、价值、和 24 个月的财务轨迹是什么。
>
> **它不预测市场规模，它预测你这一个人的产出。** 所有留存 / 转化 / CAC 都取行业
> 公开基准的中位数，差异来自「你能拿到多少用户」而不是「我猜市场会涨」。
>
> 数据检索日 2026-09-10。佣金率、CPI、法规状态**都会变**，引用超过 3 个月请重新核对（见 §8 来源）。
> 特别是 §5 的 BNM 保险聚合业务注册要求处于 exposure draft 阶段，落地条款未定。
>
> ---
>
> **⚠️ 2026-09-10 同日补充：§7 的 B2B2C 反转方案已被证伪。** 本文初稿在否定 B2C 之后提出「把工具卖给
> 已有人群的渠道方」作为出路。同日后续调研（马来西亚企业健康采购）推翻了它 —— 见 **§11**。
> **结论变为：健康方向两种形态均不成立。** §7 保留原文不删，作为判断被推翻的记录；阅读时须先读 §11。

---

## 1. 结论先行

| # | 结论 | 量化 |
|---|------|------|
| 1 | **B2B 合作变现在 solo dev 规模下算术上不成立。** 这是本文最硬的结论 | Affiliate 收入 **$0.01–0.05/MAU**，而 AI 每日反馈 API 成本 **$0.12–0.24/MAU** —— 每个免费用户倒亏 3–10× |
| 2 | **我此前给你的 40–60% 佣金率是错的（美国数字）。** 马来西亚本地实际约 **3.46%** | Involve Asia 自家健康类案例：MYR 100 销售额付 **MYR 3.46**。差 10 倍以上 |
| 3 | **即使做到 9.5 万次安装（P80 上行），affiliate 也只占总收入 2.8%** | P80 时订阅 RM 28,560/月 vs affiliate RM 542–1,083/月 |
| 4 | **「免费人群 → B2B 变现」没有任何公开成功先例**；走通的 solo dev 全是订阅制 | Health IQ 破产（负债 $257M）；MyFitnessPal 2026 才上广告网络，那是几亿用户之后 |
| 5 | **付费投放这条路结构性封死** | 健康类 12 月 install LTV **$1.21** < 最便宜的 TikTok CPI **$1.20–2.40**。每个 D30 留存用户成本 $30–100 |
| 6 | **全成本口径下 24 个月期望值为负**；只有把你自己的时间算作免费才转正 | EV 净收入 **RM 36,355** vs 全成本 **RM 76,150** → **−RM 39,795**。折算 **RM 41/小时**，约为你日常工时价的一半 |
| 7 | **你唯一真正差异化的资产是马币零售价数据**，不是营养数据本身 | 46 个食物条目带 2026-08 马来西亚零售价。全球营养 App 都有 USDA 宏量数据，没人做本地成本结构化 |
| 8 | ~~应该反转成 B2B2C：把工具卖给已经有人群的一方~~ **← 已证伪，见 §11** | 供应商资格关（ISO 27001 + 三年案例）先于产品价值关；且 Naluri 已自建 AI 食物日志 + 注册营养师，AIA Vitality 已有营养咨询 —— 头部买家已自建完毕 |

---

## 2. 现有资产盘点（决定成本起点）

已验证存在于本仓库 / `repos/notes`：

| 资产 | 规模 | 复用价值 |
|------|------|---------|
| 食物营养数据集 | **48** 条，其中 **45** 条带 USDA 来源微量营养素（含 FDC ID） | 中。质量高但量太少，MyFitnessPal 有 1,400 万条 |
| **马来西亚零售价数据** | **46** 条，`prices/my-retail-2026-08.yaml` | **高 —— 这是唯一的护城河**。见 §7 |
| `scripts/lib/nutrition/` Python 适配器 | 190 行（basis 换算 + 宏量/成本推导） | 中。逻辑可移植，但要重写成服务端 |
| `FoodsExplorer` React 查询 UI | ~18KB，可运行 | 中。Web 组件，移动端要重做 |
| `rda_reference.yaml` + `schema.yaml` | — | 高。RDA 对比逻辑是现成的 |

**结论**：技术底子有，数据量不够。但如果定位收窄到「马来西亚日常食材的预算-营养优化」，48 → 300 条就够覆盖，这是可控工作量（§3 已计入 50 小时）。

---

## 3. 成本模型（24 个月）

### 3.1 时间成本

机会成本按 **RM 75/小时**（马来西亚资深前端 ~RM 12K/月 ÷ 160h）。

| 项目 | 小时 |
|------|-----:|
| 移动端外壳（Expo/RN）+ 认证 + onboarding | 60 |
| 记录 UI（食物搜索、份量、每日汇总） | 50 |
| 同步后端（Supabase）+ schema | 30 |
| AI 反馈管线 | 25 |
| 付费墙 + RevenueCat + 双商店上架 | 30 |
| 数据集扩充 48 → 300 条（USDA 查询 + 本地价格核实，AI 辅助 ~12 分钟/条） | 50 |
| PDPA 同意流程 + 隐私政策 + DPO 设置 | 25 |
| **一次性构建合计** | **270** |
| 运营期（维护 12h/月 + ASO/内容 16h/月）× 22 月 | 616 |
| **24 个月总计** | **886** |

→ 时间机会成本 **RM 66,450**

### 3.2 现金成本

| 项目 | 24 月 (RM) |
|------|----------:|
| Apple Developer（$99 × 2 年） | 940 |
| Google Play（$25 一次性） | 119 |
| Supabase（M1–12 免费，M13–24 Pro $25/月） | 1,425 |
| 域名 + landing page | 200 |
| PDPA 法务审查（隐私政策 + 同意书，马来西亚律师低档报价） | 4,000 |
| LLM API（见 §3.3） | 3,000 |
| RevenueCat（$2.5K MTR 以下免费） | 0 |
| **现金合计** | **9,684** |

### 3.3 LLM 成本（决定免费层能不能给 AI）

假设：每次调用 ~2,000 input（日志 + 缓存 system prompt）+ ~400 output tokens。

| 档位 | 成本/用户/月 |
|------|-----------:|
| Haiku 4.5，每日反馈 | ~$0.12 |
| Sonnet 5，每日反馈 | ~$0.24 |
| + prompt caching（读取 0.1×） | ~$0.06–0.13 |
| **免费层：每周反馈（非每日）** | **~$0.02–0.04** |

**这是本模式最致命的陷阱**：免费层给每日 AI 反馈 = $0.12–0.24/MAU 成本，对应 affiliate 收入 $0.01–0.05/MAU。
**设计约束：AI 每日反馈必须在付费墙之后，免费层只能给每周一次。**

### 3.4 总成本

| 口径 | RM |
|------|---:|
| 现金 | 9,684 |
| 时间机会成本 | 66,450 |
| **全成本** | **76,134** |

---

## 4. 收入 Forecast（24 个月，三情景）

### 4.1 定价与基准假设

- 定价：RM 15/月 或 RM 120/年。假设 60% 选年付 → 混合 **RM 12/月/付费用户**
- 商店抽成：15%（Small Business Program，年收入 <$1M 适用）→ **净 RM 10.20/月/付费用户**
- Install → 付费转化：**4.7%**（RevenueCat：11.2% install-to-trial × 42.2% trial-to-paid）
- 月流失：**9.2%**（2026 年健康类订阅基准，年化 68.4%）
- D30 留存：**4%**（健康类，AppsFlyer 2.78%–4%，全行业 5–7%）
- 付费投放不可用（见 §1 结论 5）→ **纯自然增长**
- 对标爬坡曲线：HabitKit（98% 用户来自商店自然搜索，零广告）—— 2022-11 上线，14 个月后排到 "habit tracker" 关键词才出现拐点，3 年做到 $28K MRR

### 4.2 三情景

| | **P20（下行）** | **P50（中位）** | **P80（上行）** |
|---|---:|---:|---:|
| 触发条件 | ASO 始终未排上 | 缓慢自然爬坡 | 出现 HabitKit 式关键词突破（~M14） |
| M24 累计安装 | 2,520 | 13,380 | 95,000 |
| M24 当月新增安装 | 150 | 1,300 | 12,000 |
| M24 在册付费用户 | ~50 | ~380 | ~2,800 |
| **M24 MRR (RM)** | **510** | **3,876** | **28,560** |
| M24 MRR (USD) | 107 | 816 | 6,013 |
| 24 月累计净收入 (RM) | 3,960 | 27,500 | 165,000 |

**P50 交叉验证**：M24 MRR USD 816 —— 低于健康类 solo dev MRR 中位数 **$1,449**（n=166），
合理，因为该中位数含已成熟多年的 App，M24 处于中位数之下符合预期。模型自洽。

### 4.3 B2B 合作收入在三情景下的实际贡献 —— 本文的关键打击

MAU 按累计安装的 12% 估算（对应 4% D30 留存 + 复访）。
Affiliate 按 **$0.01–0.02/MAU**（取区间低端，因为马来西亚本地佣金率 3.46% 远低于美国的 40%）。

| | P20 | P50 | P80 |
|---|---:|---:|---:|
| M24 MAU | 302 | 1,606 | 11,400 |
| Affiliate 收入/月 (RM) | 14–29 | 76–152 | 542–1,083 |
| 订阅收入/月 (RM) | 510 | 3,876 | 28,560 |
| **Affiliate 占总收入** | **2.7–5.4%** | **1.9–3.8%** | **1.9–3.7%** |

**即使做到 9.5 万次安装，合作分成也只是订阅收入的 2–4% 零头。**
你最初设想的「靠合作方赚钱」在任何情景下都不构成一条业务线。

**保险线索是唯一例外，但被法规锁住**：
P80 情景下 11,400 MAU，若 2%/年产生合格保险线索 = 228 条/年。
按美国费率（$6–28/条）= RM 6,500–30,300/年 = **RM 540–2,525/月** —— 确实优于 affiliate。
但：马来西亚已把保险聚合列为**需向 BNM 注册的业务类别**；马/新本地线索费率**未公开**。见 §5。

---

## 5. 法规硬约束（这一节决定哪些路直接不能走）

| 约束 | 内容 | 对本模式的影响 |
|------|------|--------------|
| **马来西亚 PDPA 修正案 2024**（2025 年 1/4/6 月分阶段生效） | 健康数据明确列为**敏感个人数据**；控制者**和**处理者自 2025-06 起**强制任命 DPO**；强制泄露通报；罚则 **RM250,000 和/或 2 年监禁**；**跨境白名单已取消**，仅可传输至「实质相似/充分」司法辖区 | 收集健康数据即触发全套义务。solo dev 可自任 DPO，但同意流程和跨境（如用美国云）必须真做。§3.2 已计入 RM 4,000 法务费，**这是低档报价** |
| **新加坡 PDPA** | 每个组织**无论规模**强制 DPO；泄露须 **3 个自然日内**报 PDPC；未经明示同意向保险公司分享医疗数据是明确违规 | 「攒健康数据卖给保险公司」的原始设想，在新加坡是直接违规，除非有逐项明示同意 |
| **马来西亚 BNM — 保险与回教保险聚合业务** | 已成为**需注册**的业务类别（exposure draft 阶段） | 「收集健康数据 → 按线索收费转给保险公司」在马来西亚是**受监管活动**，不是自由的 affiliate 玩法。**建模这条路之前必须先读这份 draft 的门槛与资本要求** |
| **新加坡 MAS Notice FAA-N02** | **存在合法路径**：持牌/豁免 FA 可委任 **introducer**。约束：强制披露、须用 FA 提供的话术脚本、**不得接触客户资金、不得提供建议** | 保险线索在新加坡可合法做，前提是严格非建议性。这是马/新之间的关键差异 |
| **马来西亚 Allied Health Professions Act 2016 (Act 774)**，2020-07-01 生效，2022 年附表修正覆盖 16 个专业 | **dietitian 和 nutritionist 均为受保护称号**，无论行业，执业须向 MAHPC 注册并持执业证书；罚则含罚金与监禁 | 个性化 AI 营养建议处于灰区，**不能挂 nutritionist/dietitian 名义**，除非有注册执业者。见 §7 的定位规避方案 |

---

## 6. 竞争格局（为什么「自己攒人群」这条路已经被占）

| 对手 | 状况 | 含义 |
|------|------|------|
| **BookDoc**（马来西亚，2015） | **和你设想的模式完全一致**：运动追踪 + 奖励，**12 国 90+ 奖励合作方**（Grab / Uber / Airbnb / TripAdvisor / Agoda），获 MOH、旅游部、SOCSO 背书，2023 年承办 PERKESO Activ@Work。仍在运营 | 模式能成立 —— 但用了十年，且靠**政府 + 企业渠道**才攒出这张合作网。不是 solo dev 的起点 |
| **Naluri**（马来西亚，2017） | 6 轮融资 **$19.9M**（21 家投资方，含 Telus），靠**企业/保险合同**变现，**不是**消费端 affiliate | 区域内的钱都在 B2B 这条路上。强信号 |
| **HPB Healthy 365**（新加坡） | **政府出资的免费 App，直接给用户走路发钱**；National Steps Challenge 有 **696,907** 成年人参与的评估研究；eVoucher 通行 30+ 商户品牌 | 在新加坡你要对打一个免费且倒给用户发钱的国家级 App |
| **AIA Vitality / Prudential Pulse**（马来西亚） | 保险公司自建 wellness App（Pulse 对非投保人开放） | 保险公司**既是你这个位置的竞争者，也是你唯一现实的买家** |

---

## 7. 反转方案：B2B2C，而不是 B2C 攒人群

> **⚠️ 本节已于同日（2026-09-10）被后续调研证伪 —— 见 §11。原文保留不删，作为判断被推翻的记录。**
> 本节的逻辑（把获客和留存的负担转给渠道方）本身没错，错在**没有检查渠道方那一端的准入条件和现有供给**。
> §7 末尾把「合同价位」列为唯一待验证项，这是漏判：真正的阻塞是供应商资格与头部已自建，不是价格。

前面所有数字都指向同一个结论：**问题不在变现方式，在于你要自己承担获客和留存**。

健康类的结构性困境是三个数字同时成立：
- CPI **$1.20–2.40** > install LTV **$1.21** → 买不起用户
- D30 留存 **4%** → 自然来的用户也留不住
- Affiliate **$0.01–0.05/MAU** → 留住了也换不成钱

**把工具卖给已经有人群的一方，三个问题同时消失**：

| B2C 攒人群 | B2B2C 卖给渠道方 |
|---|---|
| CAC $30–100/留存用户 | **CAC = 0**（客户自带人群） |
| 收入依赖消费者养成习惯 | 收入是**年度合同**，与个体留存解耦 |
| 你是 PDPA 数据控制者，全套义务 | **企业客户是数据控制者**，你的合规负担大幅下降 |
| $0.01–0.05/MAU | 合同制，单用户价值高出若干个量级 |
| 无成功先例 | **Naluri $19.9M / Noom / BookDoc 都在这条路上** |

**你的具体切入点 —— 用马币成本数据，不用营养数据**

全球营养 App 都有 USDA 宏量数据，你拼不过。但「**每克蛋白质在马来西亚要多少林吉特**」这种本地成本结构化数据，`prices/my-retail-2026-08.yaml` 是我在公开范围内没看到第二份的东西。

这个定位同时解决三件事：
1. **护城河**：本地价格数据要持续采集，海外玩家做不了，MyFitnessPal 不会做
2. **规避 Act 774**：定位成「预算约束下的成本-营养优化」= 你在做**价格与宏量的算术**，不是在提供营养建议。不碰 nutritionist 受保护称号
3. **对渠道方有真实价值**：马来西亚大众市场的企业健康计划、保险公司 wellness 模块，最缺的正是「怎么在有限预算内吃够营养」—— 这是本地痛点，不是发达市场那套卡路里赤字叙事

**待验证（我没有硬数据，不编）**：马来西亚企业健康计划的实际合同价位、保险公司 wellness 模块的采购流程与预算。
这是下一步该做的调研，也是决定这条路能否成立的关键未知量。

---

## 8. 期望值与决策

### 8.1 EV 计算

概率权重（HabitKit 式突破罕见，故上行给低权重）：

| 情景 | 概率 | 24 月累计净收入 (RM) | 加权 |
|------|---:|---:|---:|
| P20 | 50% | 3,960 | 1,980 |
| P50 | 35% | 27,500 | 9,625 |
| P80 | 15% | 165,000 | 24,750 |
| **EV** | | | **36,355** |

| 口径 | 结果 |
|------|------|
| EV vs **现金**成本 RM 9,684 | **+RM 26,671**（正） |
| EV vs **全成本** RM 76,134 | **−RM 39,779**（负） |
| 折算时薪（EV ÷ 886h） | **RM 41/小时**，约为日常工时价 RM 75 的 **55%** |
| 回本时点（P50，现金口径） | ~M16–18 |
| 回本时点（P50，全成本口径） | **24 个月内不回本**，需 ~M40+ |

### 8.2 诚实的判断

**作为财务投资**：以你的工程时间计价，EV 为负。这不是「有风险但值得赌」，是期望值本身就低于你把同样 886 小时投入本职或接单。

**作为其他东西，它可能值**：
- 期权价值：P80 有 15% 概率通向 RM 28K/月，且真突破了会自我加速
- 学习与作品：AI native 全栈交付一个上架产品，对你的 profile 是真实资产
- 已有系统的副产品：这些数据你本来就在为自己生成（personal-os 的日志 + 营养适配器）—— 边际成本低于从零开始

**如果要做，唯一说得通的顺序**：
1. 不要先建 App。先拿现有的 48 条数据 + `FoodsExplorer` 做一个 Web 工具验证需求（成本 <30 小时）
2. 同期做 §7 待验证项的调研：找 2–3 家马来西亚企业健康计划或保险公司谈，问他们缺不缺这个
3. **只有渠道方表达了真实兴趣，才投入那 270 小时构建移动端**
4. 订阅是唯一主收入线；affiliate 只能当 50K MAU 之上的 <10% 加成，永不作为主模型

---

## 9. 来源

### 单位经济学与基准
- [Health & Fitness App Benchmarks 2026 — Business of Apps](https://www.businessofapps.com/data/health-fitness-app-benchmarks/)
- [Adapty — In-app subscription benchmarks for Health & Fitness](https://adapty.io/blog/health-fitness-app-subscription-benchmarks/)
- [RevenueCat — State of Subscription Apps 2026](https://www.revenuecat.com/state-of-subscription-apps)
- [Fitness App Retention & Churn 2026 — RetentionCheck](https://retentioncheck.com/churn-benchmarks/fitness-apps)
- [Day-1/7/30 Retention Benchmarks 2026](https://semnexus.com/day-1-day-7-day-30-retention-benchmarks-app-category-2026)
- [DAU/MAU Stickiness Benchmarks 2026](https://vmobify.com/blog/dau-mau-stickiness-benchmarks)
- [TikTok Ads for Fitness App Growth 2026](https://www.rocketshiphq.com/tiktok-ads-fitness-app-growth/)
- [Fitness App Advertising: 7 Channels Compared](https://adwave.com/resources/fitness-app-advertising)
- [App Revenue Potential 2026 — Forasoft（affiliate per-MAU）](https://www.forasoft.com/blog/article/app-revenue-potential)
- [Ad Monetization for Subscription Apps — RevenueCat](https://www.revenuecat.com/blog/growth/ad-monetization-subscription-apps)
- [Claude API Pricing — Anthropic docs](https://platform.claude.com/docs/en/about-claude/pricing)

### 案例
- [Bloomberg Law — Health IQ intends to liquidate](https://news.bloomberglaw.com/bankruptcy-law/vc-backed-life-insurance-startup-health-iq-intends-to-liquidate)
- [Forbes — a16z-backed Health IQ files for bankruptcy](https://www.forbes.com/sites/katiejennings/2023/09/11/andreessen-horowitz-backed-startup-health-iq-files-for-bankruptcy/)
- [MyFitnessPal Ads media network launch](https://finance.yahoo.com/news/myfitnesspal-launches-advertising-media-network-130000188.html)
- [Noom revenue & strategy — Sacra](https://sacra.com/c/noom/)
- [HabitKit growth playbook — AfterMVP](https://www.aftermvp.com/playbooks/habit-kit)
- [Habit Pixel $0→$1K MRR — Indie Hackers](https://www.indiehackers.com/post/from-0-to-1k-mrr-in-8-months-bootstrapping-habit-pixel-as-a-solo-dev-684b6c056d)
- [Solo Developer SaaS Revenue Examples 2026](https://bigideasdb.com/solo-developer-saas-monthly-revenue-examples)

### 马来西亚 / 新加坡市场
- [Fitness Apps – Malaysia, Statista](https://www.statista.com/outlook/dmo/digital-health/digital-fitness-well-being/digital-fitness-well-being-apps/fitness-apps/malaysia)
- [Digital Fitness & Well-Being – Singapore, Statista](https://www.statista.com/outlook/dmo/digital-health/digital-fitness-well-being/singapore)
- [Involve Asia — health affiliate case study](https://involve.asia/blog/health-affiliate-program-case-study/)
- [iHerb Affiliate Program on Involve Asia](https://involve.asia/blog/iherb-affiliate-program/)
- [NutriProfits affiliate directory — UpPromote](https://uppromote.com/affiliate-directory/nutriprofits/)

### 法规
- [BNM — Exposure Draft on Insurance and Takaful Aggregation Business](https://www.bnm.gov.my/-/exposure-draft-on-insurance-and-takaful-aggregation-business-registration-procedure-and-requirements)
- [Baker McKenzie — Insurance Sales, Advisory and Distribution, Malaysia](https://resourcehub.bakermckenzie.com/en/resources/asia-pacific-insurance/asia-pacific/malaysia/topics/guide-for-insurance-sales-advisory-and-distribution)
- [MAS Notice FAA-N02 — Appointment and Use of Introducers](https://www.mas.gov.sg/regulation/notices/notice-faa-n02)
- [Mayer Brown — Malaysia PDPA amendments & cross-border guidelines](https://www.mayerbrown.com/en/insights/publications/2025/07/from-legislative-reform-to-practical-guidance-key-amendments-to-malaysias-pdpa-and-the-launch-of-cross-border-transfer-guidelines)
- [Singapore PDPA Guide 2026 — DPO & 3-day breach rule](https://vucense.com/tech-guides/security-101/singapore-pdpa-compliance-guide-2026/)
- [Guidelines of Allied Health Professions Act for Nutritionists (Act 774)](https://nutriweb.org.my/pdf/Guidelines-for-Nutritionist-Under-AHP-Act-774.pdf)

### 竞争格局
- [HPB — National Steps Challenge](https://www.hpb.gov.sg/newsroom/article/national-steps-challenge-expands-to-include-corporates-in-new-season-and-targets-to-get-250-000-singaporeans-moving)
- [Evaluation of a population-wide mobile health programme in 696,907 adults, Singapore](https://pmc.ncbi.nlm.nih.gov/articles/PMC9238668/)
- [BookDoc — Go Activ Get Rewards](https://www.bookdoc.com/download-bookdoc-app/)
- [Naluri company profile — Tracxn](https://tracxn.com/d/companies/naluri/__7WDcOYYd4JjSupM_dHv5565EscHHRQJk1dfhrZyF01k)
- [AIA Vitality Malaysia](https://www.aia.com.my/en/aia-vitality/about-aia-vitality.html)

---

## 10. 本文的已知弱点

诚实标注，避免未来自己引用时当成硬结论：

1. **马来西亚企业健康计划 / 保险 wellness 模块的合同价位没有公开数据** —— §7 的反转方案缺最关键的一个数字，我没有编。这是下一步调研的第一优先项。
2. **马/新的保险线索费率未公开** —— §4.3 用的是美国费率（$6–28/条）做上界示意，本地实际值可能显著更低。
3. **BNM 保险聚合业务注册要求处于 exposure draft 阶段**，门槛与资本要求在 PDF 内未取得。建模保险线索路径前必须先读。
4. **Statista 马来西亚数据是 2023 基线**外推至 2027，且明确排除广告与下载收入、仅覆盖 B2C —— 只能当人群规模代理，不是收入天花板。
5. **安装量爬坡曲线是我建的模型，不是观测值**。锚点是 HabitKit 的公开披露（一个样本），P20/P50/P80 的分布形状带有主观判断。
6. **概率权重（50/35/15）是我的判断，不是数据**。EV 结论对这个权重敏感 —— 若上行概率是 30% 而非 15%，全成本 EV 即转正。

---

## 11. 三方向横向对比（2026-09-10 同日补充）

初稿完成后又跑了三轮并行调研：马来西亚企业健康采购、fintech 垂直 AI、AI copilot 垂直。
结论是 **§7 的反转方案被证伪，且健康方向整体出局**。

> **本节是结论摘要。** Fintech 与 AI copilot 两个方向的完整证据、以及与方向选择无关的
> AI 时代 solo dev 经济学（收入分布、毛利结构、定价设计），见
> **`docs/analysis/solo-dev-direction-scan-2026-09.md`**。

### 11.1 健康方向为什么两种形态都不成立

| 形态 | 死因 | 证据 |
|------|------|------|
| **B2C 攒人群**（§1–§6） | 算术死结：服务成本高于变现 | Affiliate $0.01–0.05/MAU vs AI 反馈成本 $0.12–0.24/MAU；install LTV $1.21 < 最低 CPI $1.20–2.40 |
| **B2B2C 卖渠道**（§7） | **供应商资格关先于产品价值关** | 马来西亚 GLC/大型企业 RFP 普遍要求 ISO 27001 + 同类项目三年经验；Sdn Bhd 首年全成本 RM 3,500–10,000 |
| — 补充死因 | **头部买家已自建完营养层，且带着 Act 774 下你拿不到的资质** | Naluri 已有 AI 食物日志（拍照→评分）+ 自家注册营养师；AIA Vitality 已有 Nutrition Consultation，其合作方是 Jaya Grocer/Guardian/Garmin 这类零售折扣品牌，不是数据供应商 |
| — 补充死因 | 国家级渠道无第二供应商位 | PERKESO Activ@Work 由 BookDoc 独家承接，对雇主与员工全免费 |

**剩余可售空间**：把马币价格数据授权给一个已有资质、缺本地成本数据的小玩家（ThoughtFull 营养层最薄；
Diet Ideas 有认证营养师、缺成本数据）。量级是**四位数令吉的一次性数据授权**，不是可复利的 SaaS 收入。

价位参考（补充 §7 待验证项）：数字营养模块落在采购金字塔最底层，全球「基础数字平台」地板价
**$3/用户/月**，营养只是其中一个功能。保险公司 wellness 模块外采价**完全未公开**。

### 11.2 三方向对比

| | 健康 | Fintech 垂直 AI | **AI copilot 垂直** |
|---|---|---|---|
| 监管 | **三重锁死**：PDPA 敏感数据 + Act 774 受保护称号 + BNM 保险聚合注册 | 「比较」二字落入 BNM 财务顾问牌照范围 → 信用卡/汇款比价全red。**绿灯只剩 LHDN 税务口** | 视细分而定；文档/流程工具层不需资质，做「建议」则触线 |
| 单位经济 | 死结：$0.01–0.05/MAU 变现 vs $0.12–0.24/MAU 成本 | B2B RM100–2,500/月，无死结 | B2B self-serve CAC **$702**，垂直 SaaS LTV:CAC **3.5–4.2:1**（自举型最优 8.7×） |
| 竞争 | BookDoc（十年+政府渠道）、Naluri（$19.9M）已占位 | 绿灯通道已挤满（Zoho/BDO/jomeinvoice/easyinvoice/advintek），且执法推迟至 2028 → 买方无紧迫感 | 视细分；薄壳必死（Jasper $120M→$55M，−54%） |
| 你的独有资产 | 马币零售价数据（但买家已自建营养层） | **无** | 视细分 |
| **排序** | 3 | 2 | **1** |

**AI copilot 排第 1 的理由不是市场更大，是约束结构可解**：健康的 LTV $1.21 < CPI $1.20–2.40 是算术，
努力改变不了；B2B self-serve 的 CAC $702 对 LTV:CAC 3.5–4.2:1 是一个有解的方程。

### 11.3 本轮最重要的一条，与方向选择无关

> **54% 的独立开发产品收入恰好为 $0，且这个分布自 2023–2024 以来纹丝不动 —— 尽管 AI 把开发速度提了一倍。**
> 前 5% 拿走 70%+ 的收入。失败被明确归因于**市场选择**，而非执行能力。

**含义：瓶颈不在「能不能做出来」，在「能不能选对细分并触达它」。** 本文全篇（含 EV 模型、
30 小时验证工具设计）都在优化「做什么」和「怎么做」，而数据说这不是稀缺项。

**AI 时代垂直工具真正有效的护城河**（多家 VC/法务口径一致）：不是模型选型、prompt 工程或 UI 包装，
而是**成为某个组织被强制留档的流程的记录系统（system of record）** —— 审计轨迹、留存周期、计费集成、
以及把你定为该受监管任务指定工具的那份内部审批。模型厂商能复制一个能力，复制不了这些。

推理成本 2022-11 至 2024-10 间下降 **280 倍**，模型已是按带宽计价的采购输入，不是竞争资产。
OpenAI 一年内吃掉 200+ 家拿过融资的 wrapper 公司。

### 11.4 结论：本文的方向已被 `docs/design/pdpa-compliance-agent.md` 取代

本轮 AI copilot 调研独立收敛到的第一推荐（马来西亚 SME 的 PDPA 合规文档与留档工具），
与该文档 **2026-09-06** 经四轮调研得出的结论一致 —— 且那份文档已经走得更远：
已排除 e-Invoice 与 Document AI、已确认 ComplyHQ 仅覆盖新加坡、已定价 RM150–350/月、
已设 **2026-09-20 时间盒验证死线**与 kill/proceed 判据。

**独立路径收敛到同一答案，是本轮最强的信号。**

**因此：健康方向到此为止。** `docs/design/budget-nutrition-optimizer-web.md`
（30 小时验证工具设计）随之**转为搁置** —— 它验证的是一个已被证伪的商业模式，
现在动手是在为一个不存在的买家造演示。该文档保留，因为其中的架构决策
（派生留 Python / 搜索放 TS，遵守既有不变量）在数据集本身继续演进时仍然适用。

**下一步不在本文，在 `pdpa-compliance-agent.md` §9 的 Open Questions 1/3/4/6。**
