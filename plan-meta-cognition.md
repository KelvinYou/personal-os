# Plan — Meta-Cognition Layer for Personal-OS

> **Status**: **All phases implemented** · 2026-04-25 · v3
> **Scope**: 在现有 daily/weekly/coach 三层之上，新增**判断追踪**与**自我审计**层
> **Sibling docs**: `plan.md`（master roadmap）, `architecture.md`（系统不变量）

---

## 0. TL;DR

Personal-OS 当前追踪三类信号：**行为**（daily log）、**身体**（COROS）、**产出**（deep work / weekly score）。
缺的是**判断**——你做的非琐碎决定（跳槽、加仓、推迟一个项目）从未被结构化记录，更没被回头校准。
判断质量是 25 岁起复利最猛的能力，不追踪它等于放弃复利。

本 plan 提议三层渐进式 meta-cognition：

| 层 | 解决什么 | 工时估算 | 风险 |
|----|---------|---------|------|
| **L1 Decision Journal** | 捕获决定 + 预期结果 + 校准日 | 6h MVP | 容易变成形式主义 |
| **L2 Meta-Coach** | 审计 weekly-review / coach-planner 自身的优化建议质量 | 6h | 需要积累 3+ 个月数据才有信号 |
| **L3 Identity Audit** | 季度对齐"声称的我"与"行为数据反映的我" | 3h | 容易陷入自责，需中性叙事 |

**只先做 L1 的 MVP**。L2/L3 先冻结设计但不实现，等 L1 跑 8-12 周后再评估。

---

## 1. 假设与反驳

### 假设
1. 用户做的非琐碎决定数量 ≥ 1/周（看 daily log 的 blocker / next steps 出现频率支持这点）
2. 决定捕获摩擦 < 30 秒时（一句话 brain dump），用户会真的写
3. 6 个月后回看，至少 30% 的决定的 actual outcome 显著偏离 expected outcome——这是校准信号的来源
4. AI agent（weekly-review、coach-planner）有"自我合理化"倾向，会为用户/自己开脱，这种 bias 只能由独立的 meta agent 揭露

### 反驳（必须先想清楚）

**R1: "决策日志会变成形式主义。"**
风险真实。Tim Ferriss 等人推过决策日志，多数人坚持不到 3 个月。
缓解：(a) 极简捕获——一句话 brain dump，AI 推断 enum，用户只纠偏；(b) review_date 到期时由 `make check` 主动 surface，而不是依赖用户自查；(c) 30 天 review 窗口让习惯闭环尽快形成；(d) 接受 60% 衰减——只要每月留下 2-3 条质量决定，6 个月就有 12+ 条样本。

**R2: "Meta-coach 是 over-engineering。"**
有道理。weekly-review 自带反思机制。但反思的对象是用户行为，不是 agent 自身建议质量。当 coach-planner 连续 4 周建议晨跑、用户连续 4 周没做，谁来 flag 这是 plan 不合理而非用户失败？
缓解：先冻结设计，等 L1 数据积累后再判断是否需要。

**R3: "Identity Audit 太软。"**
确实软。这一项最容易做成 self-help 鸡汤。
缓解：审计严格基于行为数据（时间分配、消费类目、deep_work 主题），不读用户的"我想成为"自述。是行为数据驱动的，不是叙事驱动的。

**R4: "为什么不直接扩展 weekly-review？"**
weekly-review 只看一周，meta-cognition 需要月度/季度横向对比。混在一起会让 weekly-review skill 膨胀失焦。架构上职责不同，应分开。

---

## 2. 三层设计

### L1 — Decision Journal

**核心 entity**: `data/decisions/YYYY-MM-DD-<slug>.md`

**Schema**（`templates/decision.md`）：

```yaml
---
id:                       # YYYY-MM-DD-<slug>，与文件名一致
date_decided:             # YYYY-MM-DD
category:                 # career | finance | health | relationship | project | tooling
stakes:                   # medium | high (low 不记——见 §6 Q1)
                          # high = 改变 ≥ 1 年生活轨迹; medium = 影响 ≥ 1 个月
reversibility:            # easy | costly | irreversible
decision_type:            # proactive | reactive | default
                          # proactive = 主动发起; reactive = 被迫应对; default = 选择不变
expected_outcome:         # 1 句话，必须可证伪
review_date:              # 触发回顾的日期（默认 +30d）
status:                   # open | reviewed | pushed | expired
# 以下字段由 /decision-review 写入
actual_outcome:           # null 直到 review
calibration_delta:        # null | "as_expected" | "better" | "worse" | "too_early" | "irrelevant"
lesson:                   # null | 1-2 句话
---

# 决定: <一句话标题>

<自由文本：上下文、考虑过的选项、假设、担忧。不强制分段——写多少算多少。>
```

> **Schema 设计决策**:
> - **`decision_type` 替代 `confidence`**：Phase 1 没有校准基础设施，confidence 会变成无脑 0.7。decision_type（proactive/reactive/default）无需校准就能揭示模式（"80% reactive = 你在响应生活而非驾驭它"）。`confidence: 0.0-1.0` 延迟到 Phase 2 引入，届时有 12+ 条 reviewed 决策支持 Brier score 分析。
> - **review_date 默认 30d（非 90d）**：90d 意味着 12 周 kill window 内零条完成 review，只能验证捕获习惯却无法验证回顾习惯。30d 保证至少经历一次完整闭环。到期后 outcome 不明确 → review 时选 `calibration_delta: too_early`，skill 自动 push review_date +30d。
> - **Markdown body 不分段**：原 4-section 结构（上下文/选项/假设/担忧）实测 ~5 分钟填写，远超 2 分钟目标。改为自由文本，skill 从 brain dump 自动填充——用户想补结构可以补，不补也合法。

**写入路径（brain-dump 优先）**：

用户两种方式触发：
1. **一句话 brain dump**：`/decision-log 决定不续约健身房，改全 home gym。省 RM150/月，赌自己能坚持哑铃 3x/week` → skill 从 brain dump 推断 category/stakes/reversibility/decision_type/expected_outcome → 展示推断结果让用户纠偏 → 写入文件。**目标 < 30 秒捕获。**
2. **交互式引导**：`/decision-log`（无参数）→ skill 逐步引导填写。适合用户想深度思考的场景。

**Review 路径**：
- `make decisions-due` 列出 `review_date <= today` 且 `status == open` 的决定
- `make check` 输出末尾 append 同样列表（与现有熔断告警并列）
- 用户对 Claude 说 "review 一下到期的决策" → `/decision-review` skill → 引导评估 actual_outcome → 写入
- **Push 机制**：outcome 尚不明确时，review 中选 `calibration_delta: too_early` → skill 自动将 status 改为 `pushed`，review_date += 30d。避免"到期了但没结果所以跳过"的死循环

### L2 — Meta-Coach（**冻结，不实现**）

**目的**：每月一次审计 weekly-review 和 coach-planner 的建议质量，不审计用户行为。

**输入**：
- 最近 4 周 weekly reports
- 最近 4 周 coach-planner 排期（**前提：必须先开始归档，见 §5 prerequisite**）
- 同期 daily logs

**输出**（拟）：`data/reports/YYYY-MM-meta-audit.md`
- **Plan vs reality delta**: coach-planner 建议的 deep_work 总时数 vs 实际，按周
- **Repeated misses**: 哪些 P0/P1 目标连续 ≥ 3 周未达成？建议是否应该拆小或放弃
- **Optimism index**: 排期目标完成率的滚动均值；< 70% 触发 "plan 太乐观" 信号
- **Self-justification flags**: weekly-review 在解释 miss 时使用的归因模式（"心智过载"、"熔断"、"外部干扰"），找出过度归外的迹象

**冻结理由**：
1. 没有归档的 coach-planner 历史，分析无样本
2. 现在只有 ~5 份 weekly report（W12-W16），meta 分析至少需要 12+ 份才有信号
3. 设计与 L1 解耦——L1 不需要 L2

### L3 — Identity Audit（**冻结，不实现**）

**目的**：季度一次，输出"行为反映的我" vs "声称的我"的差距。

**数据驱动，不读自述**：
- 时间分配热力图（deep_work 主题分类、训练时长、社交频率推断自 spend categories）
- 消费类目占比（投资 vs 消费 vs 学习 vs 享乐）
- 学习投入（learning-agent 的雷达项变化）
- 决策类目分布（L1 数据：career 决定多还是 health 决定多？）
- 健康趋势（HRV / 体重 / 睡眠 baseline）

**输出**（拟）：`data/reports/YYYY-Q#-identity.md`
- 从行为数据反推"过去一季最重视的 3 件事"
- 与 user_profile.md 中的声明对比
- 不打分、不批判，只呈现 gap

**冻结理由**：现在做太早。需要 L1 + L2 至少各 1 个完整周期才有素材。

---

## 3. 与现有架构的契合

### 3.1 不变量（architecture.md §8）合规性检查

| 不变量 | L1 影响 | 处理 |
|-------|--------|------|
| 8.1 Schema 所有权 | 新增 `templates/decision.md` 为 schema source | 与 daily.md 同级声明；新建 `lib/schema.py::Decision` pydantic 模型（Wave 2.5 D1 完成后） |
| 8.2 字段写入所有权 | 新文件类型，无冲突 | `/decision-log` 写所有字段（除 actual_outcome / calibration_delta / lesson）；`/decision-review` 独占写后三者 |
| 8.3 读契约 | weekly-review 不读 decisions（保持职责分离） | meta-coach 读 decisions（L2 实施时） |
| 8.4 Breaker 不变量 | 不影响 | N/A |
| 8.5 时间契约 | review_date 用 KL 本地日期 | 与 daily.md 一致 |
| 8.6 失效模式 | YAML 解析失败 → skip 该 decision，不崩 | 沿用 weekly_synthesis 模式 |

### 3.2 与 Wave 2.5 Library Layer 的关系

L1 MVP **不阻塞 Wave 2.5**，但应**复用** Library Layer 出现后的 API：

- `lib.schema.Decision` pydantic 模型（D1 之后加）
- `lib.decision_log.load(path) / iter_open() / iter_due(today)` （新增模块，平行于 `daily_log.py`）
- `lib.config.Thresholds.decision_review_default_days` —— 新阈值（默认 30）

**实施顺序约束**：如果 Wave 2.5 D1 还没合（先 check `plan.md`），L1 第一版可以先走"裸 yaml.safe_load"；D1 合入后再迁移。但**不能反过来**——L1 不能阻挡 D1。

### 3.3 Makefile 集成

新增 target：

```make
## 列出今日到期需 review 的决策
decisions-due:
	@$(PYTHON) $(SCRIPTS_DIR)/decisions_due.py

## 创建一条新决策（交互式，但通常通过 /decision-log skill 触发）
decision-new:
	@if [ -z "$(SLUG)" ]; then echo "用法: make decision-new SLUG=<slug>"; exit 1; fi
	@$(PYTHON) $(SCRIPTS_DIR)/decision_new.py --slug $(SLUG)
```

`make check` 内部 append `decisions_due.py` 的输出，让用户每次跑 logic engine 时都看到 "今日有 N 条决策待 review"。

---

## 4. 阶段化 rollout

### Phase 0 — Coach-planner 归档（独立 PR，~30min）

**与 L1 无依赖，但越早做越好**——每多一天不归档就少一天 L2 ground truth。

- coach-planner skill 在产出 timetable 时同步写入 `data/reports/YYYY-MM-DD-timetable.md`
- 不改变 coach-planner 的任何行为逻辑，纯粹加一步 Write
- **独立 PR，不与 Phase 1 打包**

### Phase 1a — L1 基础设施（PR #1，~3h）

机械基础设施，不含 AI skill——先验证 `make` 工具链跑通。

1. `templates/decision.md` — schema 定义（如 §2.L1 所示）
2. `data/decisions/.gitkeep` — 在 data submodule 中建目录
3. `scripts/decisions_due.py` — 扫描 `data/decisions/*.md`，输出 review_date <= today 且 status ∈ {open, pushed} 的列表
4. `scripts/decision_new.py` — 从 template 创建新文件（slug + date 占位）
5. `Makefile` — 加 `decisions-due` 和 `decision-new` 两个 target
6. `architecture.md` — 在 §4 ER 图加 `DECISION` 实体；在 §8 加该实体的不变量
7. `README.md` — 在快速命令加 `make decisions-due`

### Phase 1b — Decision-log skill（PR #2，~3h，Phase 1a 合入后）

AI 交互层，建在已验证的基础设施之上。

1. `.agents/skills/decision-log/SKILL.md` — brain-dump 一句话捕获 + 交互式引导双模式
2. `/daily-report` 集成钩子（见下方 §4.1）

**显式不做**：
- ❌ pydantic 模型（等 Wave 2.5 D1）
- ❌ `/decision-review` skill（Phase 2）
- ❌ 校准 / Brier score / `confidence` 字段（Phase 2）
- ❌ 修改 `make check` 的输出（Phase 1.5）

### Phase 1.5 — Surface integration（~1h，Phase 1 跑两周后）

只有当 Phase 1 真的有 ≥ 3 条决策时才做：
- `report_gen.py` 末尾 append 到期决策列表
- `weekly_synthesis.py` 输出追加一行统计：`本周记录 N 条决策，M 条待 review（最近到期: slug）`——只做计数，不解析内容，weekly-review skill 不膨胀
- 验证 nudge 效果（用户是否真的会去 review）

### Phase 2 — L1 Review + 校准（~4h，Phase 1 跑 ≥ 8 周后）

需要有 ≥ 5 条已到期的决定才有 review 素材：
- `.agents/skills/decision-review/SKILL.md` — 引导 review 流程（含 push 机制：`too_early` → review_date += 30d）
- 引入 `confidence: 0.0-1.0` 字段（此时有足够样本支持校准）
- `scripts/calibration.py` — 输出 confidence vs actual 的 calibration plot（terminal-friendly）
- 月度集成到 weekly review？**待定**——倾向于不集成，保持 weekly-review skill 不膨胀

### Phase 3 — L2 Meta-Coach（~6h，Phase 2 跑 ≥ 3 个月后）

**Prerequisite**：Phase 0 的 coach-planner 归档已跑 ≥ 12 周（至少 12 份 timetable）。

### Phase 4 — L3 Identity Audit（~3h，Phase 3 之后）

季度触发。`make quarterly` 新 target。

---

### §4.1 Daily-report 集成钩子（Phase 1b 的一部分）

**不让 `/daily-report` 写决策**——保持职责分离。但让它**发现并提示**：

当 `/daily-report` 处理 brain dump 时，如果检测到非琐碎决定的信号（"决定…"、"I decided…"、选了 A 不选 B、重大取舍），在输出末尾追加一行提示：

> 💡 检测到可能的决策：`<一句话摘要>`。要记到决策日志吗？→ `/decision-log <摘要>`

用户复制粘贴即可触发。这样决策捕获搭载在已有习惯（每日 brain dump）上，不依赖独立的记忆和动机。

---

## 5. 关键决策与替代方案

| 决策 | 选择 | 替代方案 | 拒绝理由 |
|------|------|---------|----------|
| 决策存储粒度 | 每条一个 md 文件 | 单一 append-only `decisions.log` | grep / 手编 / git diff 都更友好；与 daily.md 模式一致 |
| review_date 默认 | **30 天** + push 机制 | 90 天 / 用户每条手填 | 90 天在 12 周 kill window 内零闭环；30d + `too_early` push 保证每条决策至少被 touch 一次 |
| Phase 1 用 `decision_type` | proactive/reactive/default | `confidence: 0.0-1.0` | confidence 无校准基础是噪音；decision_type 无需基础设施就能揭示模式。confidence 延迟到 Phase 2 |
| 写入方 | 专属 `/decision-log` skill | 让 `/daily-report` 顺手写 | daily-report 已经够忙；混入会让两个 skill 都失焦。但 daily-report **提示**用户有潜在决策（§4.1 钩子） |
| 与 weekly-review 关系 | **轻量耦合**：weekly_synthesis 输出决策计数（1 行） | 完全解耦 / 深度集成 | 完全解耦 → 决策日志隐形化；深度集成 → weekly-review 膨胀。1 行计数是最小可见度 |
| L2/L3 现在做不做 | 冻结设计，不实施 | 一次性全做 | 没数据 = 设计无法验证；先收集 8-12 周 L1 数据 |
| coach-planner 归档时机 | **现在就做**（Phase 0，独立 PR） | 等 L2 启动时再做 | 数据积累不可追溯，晚一天少一天样本，且归档本身 ≤ 30 min |
| 触发 review 的 UI | `make check` 输出 + `/decision-review` 主动调用 | 写 cron / 推送通知 | 与 Personal-OS "无 cron / 显式 make 触发" 原则一致（architecture.md §1） |

---

## 6. Open Questions — 已决议

| # | 问题 | 决议 | 理由 |
|---|------|------|------|
| 1 | 决策最小粒度 | **stakes ≥ medium only** | schema 注释已明确：high = 改变 ≥ 1 年轨迹，medium = 影响 ≥ 1 个月。grocery 级决定不记 |
| 2 | 是否归档 coach-planner 输出 | **是，Phase 0 独立 PR** | 数据积累不可追溯；与 L1 解耦但应先于或平行于 Phase 1a |
| 3 | `/decision-log` skill 双语 | **是** | 与所有现有 skill 一致 |
| 4 | decisions 进 data submodule | **是** | 决策是个人数据，与 daily/finance 同级；data submodule 已私有 |

---

## 7. 风险与 Non-Goals

### 风险
- **R1 形式主义衰减**（已在 §1 讨论）—— mitigation: 极简 schema + 主动 surface
- **R2 review 偏差**：人在 review 时倾向把 expected_outcome 改造成已发生的 outcome（事后合理化）。Mitigation: review 流程要求**先**朗读原文 expected，再写 actual，且 expected 字段 immutable
- **R3 stakes 通胀**：每条都标 high。Mitigation: schema 注释已内嵌例子（high = 改变 ≥ 1 年生活轨迹；medium = 影响 ≥ 1 个月；low 不记）；且 skill 在 brain-dump 推断时会默认 medium 除非内容明显 high
- **R4 隐私**：决策内容比 daily log 更敏感（涉及人际、薪资、关系）。Mitigation: data submodule 应私有（已是？需确认）；考虑加 `private: true` flag 让 weekly review 跳过该决策的引用

### Non-Goals（明确不做）
- ❌ 决策**辅助**（"我该不该跳槽？"——这是 coach-planner 的活）
- ❌ 决策模板库（Cunningham / Bezos 的"双向门"框架等）——保持 schema 极简
- ❌ 与外部工具集成（Notion / Roam）——Personal-OS 是本地 markdown，保持一致
- ❌ 决策可视化 dashboard——CLI grep / 手读已足够
- ❌ NLP 自动从 daily log 抽决策——既不准也违背"显式捕获"原则

---

## 8. 成功指标（6 个月后回头怎么判断这事 work）

**硬指标**：
- ≥ 12 条 status=reviewed 的决策（即真的走完了一个完整周期）
- ≥ 1 条决策的 calibration_delta = "worse"，且 lesson 字段被引用到后续 daily log / weekly review 的反思中
- 用户至少有 1 次主动说"我去查一下决策日志"——证明它从被动归档变成主动工具
- decision_type 分布不全是 reactive（proactive ≥ 30%，说明日志反映了主动决策而非只记被迫应对）

**软指标**：
- weekly-review 的 P0 设定开始引用历史决策上下文
- 用户开始在 brain dump 中主动 flag 决策（而非依赖 daily-report 提示）

**Kill criteria — 三级熔断**（任一触发就重新评估）：

| 级别 | 条件 | 验证什么 | 行动 |
|------|------|---------|------|
| **Capture kill** | 12 周内决策数 < 5 | 捕获习惯没形成 | Schema 太重或入口不对，重新设计或放弃 L1 |
| **Review kill** | 12 周内 reviewed + pushed < 2 | 回顾习惯没形成 | Surface 机制无效（`make check` 被忽略？），修复 nudge 或放弃 |
| **Value kill** | 6 个月内 0 条 lesson 影响后续行为 | 日志是 write-only | 日志有捕获价值但无学习价值，降级为纯归档不投入 Phase 2 |

---

## 9. 第一步

Open questions 已决议（§6）。实施顺序：

1. **Phase 0 PR** — coach-planner 归档（~30min，可与 Phase 1a 并行）
2. **Phase 1a PR** — 基础设施：template + scripts + Makefile（~3h）
3. **Phase 1b PR** — decision-log skill + daily-report 钩子（~3h，Phase 1a 合入后）

三个 PR 总计 ~6.5h。Phase 0 和 Phase 1a 可同日开工。
