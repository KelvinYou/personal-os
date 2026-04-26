# Profile Optimization Methodology

详细方法论。SKILL.md 在 Step 3-5 引用本文档。

## 1. XYZ Formula（Bullet 重写核心）

来源：Google recruiter 的公开建议，被 SEA fintech / 大厂招聘普遍接受。

> **Accomplished [X], as measured by [Y], by doing [Z].**

- **X (What)**: 你做出的具体成果（不是 task，是 outcome）
- **Y (Measure)**: 量化指标——百分比、绝对数、时间节省、用户量、GMV 等
- **Z (How)**: 关键技术决策或方法（让人能判断你是 senior/junior）

### 好坏对照

❌ "Worked on the payment system to improve performance."
- 没有 X（improve 多少？），没有 Y（measured by 什么？），Z 太泛

✅ "Reduced p99 payment API latency from 800ms to 180ms (-77%) by introducing
   request coalescing and replacing SQL N+1 with a single JOIN."
- X: latency reduction
- Y: 800ms → 180ms (-77%)
- Z: request coalescing + SQL refactor

### 当用户没有量化数据时

不要瞎编。在重写候选里**留 placeholder**，明确告诉用户要补什么：

> "Reduced checkout drop-off by **[X%]** via Stripe + local PSP integration with
> idempotent retry layer. **请补充：drop-off 改善的具体百分比，或换用户量等其他指标。**"

宁可留 `[X%]` 让用户自己填，也不要写 "significantly improved"。

### XYZ 的三种变体（按场景选）

1. **XYZ-strict**: 三段都齐，适合 senior 关键 bullet。
2. **Outcome-first**: 把 X+Y 提到句首，Z 用介词短语带过。适合需要前 6 秒抓眼球的
   top 3 bullet。
3. **Tech-emphasis**: Z 在前，X+Y 在后。适合目标岗位非常 tech-heavy（如 ML infra、
   distributed systems），recruiter 是 tech lead 而不是 HR 的场景。

---

## 2. Skill Gap 三色分类规则

输入：
- `user_skills` — 从 profile 文本中提取的所有 skill 关键词（含 skills section、experience bullets、projects 描述）
- `jd_top_skills` — `data/jobs/trends.json` 中目标方向的 top-30 频次

### 归一化

合并以下变体到一个 canonical 名：
- "Postgres" / "PostgreSQL" / "psql" → `PostgreSQL`
- "k8s" / "Kubernetes" → `Kubernetes`
- "JS" / "JavaScript" / "ECMAScript" → `JavaScript`
- "AWS" 单独算一类，但 "AWS Lambda" / "AWS S3" 单独算（细粒度服务）

归一化表维护在脚本里（如果未来抽出脚本），现在 LLM 自己判断。

### 分类阈值

| 类别 | JD 频次（占样本%）| 用户 profile 出现 | 行动 |
|------|------------------|-------------------|------|
| ✅ Hit | ≥ 30% | 是 | 保留；检查 phrasing 是否和 JD 主流一致 |
| ⚠️ Gap | ≥ 30% | 否 | **重点关注**：你会但没写？不会但该学？标记给用户 |
| 🟡 Niche-strength | < 30% 但 > 10% | 是 | 保留作为差异化卖点 |
| ❌ Dead-weight | < 5% | 是 | 评估下沉/删除 |

频次的"占样本%"指：在抓到的 N 条 JD 中，有多少条提到了这个 skill。
样本 < 30 条时**不可靠**，在报告里明确标注。

### 高频但用户没写时的两类区分

⚠️ Gap 区里要进一步分：

- **Type A: 会但没写** — 用户其他 bullet / project 里有暗示（例如做过 backend 但 skills section 没写 SQL）。建议加进 skills section 或在某条 bullet 显式提一下。
- **Type B: 不会** — 完全没出现过任何相关信号。建议要么去学（如果是核心 skill），要么放弃这个方向。

不要混为一谈给同一种行动建议。

---

## 3. Section 排序启发式

### Experience 默认排序

时间倒序是行业标准，**不要颠倒**。但可以：
- 在 summary / about 里 "spotlight" 一条更早但更相关的经历
- 在 skills section 把目标方向的关键 skill 放最前

### Projects 排序公式

打分 = `JD_keyword_match_count × outcome_strength`

- `JD_keyword_match_count`: 这个 project 描述里出现 top-30 JD 关键词的数量
- `outcome_strength`: 0-3 分
  - 0: 没量化数据
  - 1: 有定性 outcome（"shipped to production"）
  - 2: 有量化指标但范围小（个人 project）
  - 3: 有量化指标且影响范围大（团队/公司/用户量）

按总分排序，给前 3 名标 "lead with this"。

### Lead bullet 选择

每个 experience 的第一条 bullet 决定了 recruiter 是否继续读。第一条必须：
- 满足 XYZ-strict 或 Outcome-first
- 包含目标 JD 的 ≥ 2 个高频关键词
- 数字在句子前 1/3

### 删减阈值

下沉到次要 section 或删除的候选：

| 信号 | 处理 |
|------|------|
| 与目标方向无关的 skill | 删除或下沉到 "其他技能" 折叠区 |
| > 5 年前的非高分经历（非 FAANG / 非顶级项目）| 缩短到 1-2 行 |
| 重复在两个 role 都写的同类 bullet | 合并到一个 role，另一个删掉 |
| Skills section > 30 个 tag | 砍到 ≤ 20，按目标方向排序 |
| Self-promotional 形容词（"passionate"、"results-driven"）| 全删，没人看 |

---

## 4. 标杆 Profile 模式抽取

当用户粘贴了 1-3 个标杆 profile，**抽模式不抄词**。要看的维度：

### Headline（一行）

- 长度（10-15 词最常见）
- 切入角度：经验年数 / 解决的问题 / 公司+职级 / mission statement
- 是否带数字（如 "Built ML systems serving 100M+ users"）

### Summary 第一句

第一句决定打开率。常见钩子模式：
- **Numbers hook**: "10 years building payments infrastructure for SEA fintech."
- **Problem hook**: "I help fintech companies cut payment failure rates."
- **Identity hook**: "Backend engineer specializing in idempotent distributed systems."
- **Story hook**: "Started as a self-taught dev, now leading a team of 8..."

判断标杆用了哪种，对照用户最贴合哪种（基于他实际背景，不要硬套）。

### 量化数字的写法

- 用户量 / 客户量 / GMV
- 性能改进百分比
- 团队规模 / 跨团队协作数量
- 成本节省 / 收入增长

记下标杆用了什么类型的指标，因为不同岗位偏好不同。
（产品经理偏 GMV/用户量，infra eng 偏延迟/可用性。）

### Project 描述结构

- 长度：3-5 行 vs 1 段 vs 1 句
- 是否带 link（GitHub、demo、博客）
- 是否带 tech stack tag

### Skills 分组方式

- 按技术栈分（Languages / Frameworks / Tools / Cloud）
- 按能力域分（Backend / Distributed Systems / DevOps）
- 完全不分组（一长串 tag）

### 输出格式

```markdown
## 标杆对照

**标杆**: [name or "Profile A"]
**模式**: [抽取的具体模式]
**你目前**: [用户当前的对应做法]
**建议**: [基于你已有经历的具体改法，不要造新内容]
**理由**: [为什么这个模式适合 / 不适合你]
```

### 严格禁止

- 抄标杆原句
- 套用标杆的虚假人设（标杆 staff eng，你不能自称 staff eng）
- 推荐标杆用了但你没相关经历支撑的 framing

---

## 5. 报告写作规范

### TL;DR 模板

```
**Top gap**: [一句话，最关键的 skill / framing 缺口]
**Top rewrite**: [一条 bullet，原文 → 重写后]
**Top reorder**: [一个 section 调整，最大影响]
```

3 行。不要 4 行。

### 行动清单格式

每条：
- 优先级标 P0 / P1 / P2
- 预计耗时（必须 < 30 分钟，否则拆）
- 具体可执行（不要 "improve your bullets"，要 "把 dtcpay role 第一条 bullet 改成 [具体内容]"）

### 报告长度上限

- TL;DR + Skill gap 表 + 前 5 条 bullet 重写 + 排序建议 + 行动清单
- 全文 ≤ 1500 行 markdown
- 超过就分两份：`-part1.md` 优先建议，`-part2.md` 次要细节

---

## 6. 常见反模式（在报告里看到要警告用户）

- **"Passionate"、"results-driven"、"team player"** — 全是空话，删
- **"Responsible for"、"Worked on"、"Helped with"** — 没有 ownership 信号，重写
- **罗列工作内容而不是 outcome** — "Wrote APIs, did code review, attended standups" 这种
- **过长的 summary（> 5 段）** — recruiter 不读，砍到 2 段
- **重复使用同一个动词** — 整个 profile 用 5 次 "developed"，换词
- **隐藏关键 skill 在文末** — 把目标方向的核心 skill 提到 skills section 最前
- **公司没人听过却没解释**: 加一句 "(SEA fintech, 200K MAU)" 这种 context
- **Project 没 link** — GitHub / demo / blog 至少要一个，否则可信度低
