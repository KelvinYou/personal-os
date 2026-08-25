# Personal-OS — Decisions

> **本文件是「已经决定过的事」的唯一 owner**，用途只有一个：下一次会话有人重提某个
> 方案时，先来这里看它是不是已经被拒过、拒的理由是什么。
>
> 收录标准：**取舍与理由**，不是实施记录。谁在哪个 commit 做了什么，git log 比这里准。
>
> 不变量与契约在 `../ARCHITECTURE.md §8` —— 那是代码必须遵守的规则；本文件是产品决定。
> 未完成的工作在 [ROADMAP.md](ROADMAP.md)。

---

## 1. 明确不做（避免旧话重提）

### 数据与自动化

1. **Zepp Life body 数据自动同步** —— 手填是刻意的选择（memory: `feedback-body-data-manual`），不重启 `sync_scale.py`
2. **cron / launchd / GitHub Actions 定时任务** —— 单用户本地系统的偏好，非能力限制。所有流程走显式 `make`
3. **`make today` 自动链 `sync-coros`** —— 副作用风险（网络慢、API 变动），手动双步更安全
4. **事件驱动 pipeline**（如 daily-report 完成自动触发 `make check`）—— 复杂度 tax 无收益
5. **COROS 官方 API key 申请** —— 非官方 client 覆盖够用
6. **SQLite / 任何 DB 作 source of truth** —— 破坏「人类可读优先 + 手改 md 立即生效」的核心体验（ARCHITECTURE §1）。作为查询缓存可以，作为事实源不行
7. **schema versioning（`schema_version: 2` 字段）** —— schema 每年大改约 1 次，一次性 migration 模式足够
8. **LLM 直接改 daily.md frontmatter（绕过 daily-report skill）** —— 保持单一入口，否则字段必漂

### schema 字段

9. **`bedtime` / `wakeup` 字段** —— COROS API 不暴露，硬加只会制造空字段。真需要的话从 activity 时间戳反推，不需要模板字段
10. **`sleep.quality` 三级分类（Good/Fair/Poor）** —— 已换成计算型 derivation，不重建
11. **`patch_coros.py` 改为「读取时合并」（single source: `data/fitness/*.yaml`）** —— 评估过：能消除双写，但牺牲 daily.md 自包含性（grep / 人读价值下降）。当前 sync + patch 够用。此 tradeoff 已写入 ARCHITECTURE §5

### 产品边界

12. **Public dashboard / hosted UI** —— Personal-OS 是本地工具
13. **多人 / 团队化 / multi-tenant** —— 设计为 single-user
14. **决策辅助**（"我该不该跳槽"）—— 那是 coach-planner 的活，decision-log 只做记录
15. **决策模板库**（Cunningham、Bezos 双向门等框架）—— 保持 schema 极简
16. **决策可视化 dashboard** —— CLI grep 已足够
17. **NLP 自动从 daily log 抽取决策** —— 既不准，也违背「显式捕获」原则
18. **与 Notion / Roam 集成** —— 本地 markdown，保持一致
19. **pytest** —— 继续用 `unittest`。（pydantic 是例外，已接受为 schema 层必要依赖）

---

## 2. 关键决策与被拒的替代方案

### Decision journal（L1）

| 决策 | 选择 | 替代方案 | 拒绝理由 |
|---|---|---|---|
| 存储粒度 | 每条决策一个 md 文件 | 单一 append-only `decisions.log` | grep / 手编 / git diff 都更友好，且与 daily.md 模式一致 |
| `review_date` 默认 | **30 天** + `too_early` 自动 push | 90 天；或每条手填 | 90 天意味着 12 周 kill window 内零个完整闭环 —— 只能验证捕获习惯，无法验证回顾习惯。30d 保证每条至少被 touch 一次 |
| 置信度字段 | `decision_type`（proactive / reactive / default） | `confidence: 0.0–1.0` | 没有校准基础设施的 confidence 会变成无脑 0.7。decision_type 不需要任何基础设施就能揭示模式（"80% reactive = 你在响应生活而非驾驭它"）。confidence 延迟到有 12+ 条 reviewed 决策、能算 Brier score 之后 |
| markdown body 结构 | 自由文本 | 四段式（上下文 / 选项 / 假设 / 担忧） | 实测填写 ~5 分钟，远超 2 分钟目标。想补结构可以补，不补也合法 |
| 写入方 | 专属 `/decision-log` skill | 让 `/daily-report` 顺手写 | daily-report 已经够忙；混入会让两个 skill 都失焦。折中：daily-report 只**提示**「检测到可能的决策」 |
| 与 weekly-review 的耦合 | 轻量：weekly_synthesis 输出一行决策计数 | 完全解耦 / 深度集成 | 完全解耦 → 决策日志隐形化；深度集成 → weekly-review 膨胀 |
| 记录门槛 | stakes ≥ medium（high = 改变 ≥ 1 年轨迹，medium = 影响 ≥ 1 个月） | 全都记 | grocery 级决定不记；否则 stakes 通胀，字段失去区分力 |
| 触发 review 的方式 | `make check` 输出 + 主动调 `/decision-review` | cron / 推送通知 | 与「无 cron，显式 make 触发」一致 |

### 架构

| 决策 | 选择 | 拒绝理由 |
|---|---|---|
| 共享代码命名空间 | `scripts/lib/<module>.py` | 两个聚合脚本各写一遍解析 / 评估逻辑，是 Wave 1 schema drift 的**结构性根因**；不是失误，是缺 library layer |
| scoring rubric 位置 | 进 `thresholds.yaml` 的 `scoring:` 块，AI 只做 qualitative 判断 | 原打算 defer 为 P3。让 LLM 同时给分又解释，分数无法复现 |
| Sleep debt 双变量 | display 用本周累计，breaker fill 用 rolling 7d | 两者语义本来就不同，强行统一会让其中一个失真 |
| `signal_convergence`（ai-stock-analysis） | 确定性计算，丢弃 LLM 自报值 | 它 gate 了 RiskChecker 是否报精确价位；LLM 自报等于让模型说服自己开仓 |

### 连续 Poor Sleep 的缺日语义（2026-08-18）

| 决策 | 选择 | 替代方案 | 拒绝理由 |
|---|---|---|---|
| streak 的连续性 | 按**已存在的日志记录**连续计数；缺失日期视为未知，不算恢复；已有日志但不满足 Poor 条件才会打断 streak | 把缺失日期当作健康日，或要求日历日期严格相邻 | 没有日志不能证明睡眠恢复；把沉默当作恢复会低估风险，同时也不改变现有日志的明确语义 |

该语义适用于 `scripts/lib/metrics.py::_consec_poor_up_to` 与逻辑引擎的连续 Poor
告警；若未来要改成严格日历连续，必须同时更新这两个 owner 及回归测试。

### Session eval —— 审计 agent 自己（2026-08-24）

`make eval` 把 Claude Code 的 transcript 转成 `data/reports/evals/` 里一条记录。
动机：Personal-OS 的每一条回路（daily / breakers / weekly / identity-audit）审计的
都是**我**，没有任何东西审计 **agent**。会话跑砸时，证据是 `~/.claude/projects` 里
一堆没人会打开的 JSONL，于是同一个失败模式反复发生，而 AGENTS.md 什么都学不到。

| 决策 | 选择 | 拒绝的替代 | 理由 |
|---|---|---|---|
| 谁填 `judgement` / `notes` | 生成时**一律写 null**，由 `/meta-coach` 或人事后填 | 让生成器顺手给这次会话打个分 | 自己给自己打分的 auditor，等于对被审计对象有写权限 —— 与 `decision-log` 里那个坑同源。脚本只产出事实与机械 signal，每条 signal 附「什么证据能推翻它」 |
| signal 阈值放哪 | 脚本内一个具名常量块，**不进** `config/thresholds.yaml` | 与其它阈值统一收进 YAML | 那份 YAML 经 pydantic 校验、要走 `.venv`。而 eval 最该能跑的时刻，正是 `.venv` 本身坏掉的时候 |
| 依赖 | stdlib-only（含 `lib/transcript.py`） | 复用现有 lib 层 | 同上：故障期可用性优先于代码复用 |
| 重新生成的语义 | 覆盖 facts 块，但**拒绝**覆盖已填的 review 字段（除非 `--force`） | 幂等重写整份文件 | 人填的判断比机器采的事实贵，不能被一次手滑的 `make eval` 抹掉 |
| 证据单位 | 单条 eval 不作数，看 `make eval-rollup` 的月度分布 | 逐条 review | 同一个 signal 一个月内命中过半 → 那是 AGENTS.md 的 bug，不是那次会话的 bug。这是 kill criteria 的同一套逻辑 |

当前 11 个 signal：`write-before-read` / `unverified-mutation` / `verified-mutation` /
`tool-error-loop` / `recovered-from-error` / `user-correction` / `high-tool-churn` /
`context-gathered` / `review-first` / `ended-on-question` / `looks-clean`。

---

### 阈值调参三则（2026-08-24 从 ROADMAP §5 结案）

这三条曾长期挂在 ROADMAP「待拍板」表里，但代码其实早已按建议实现 —— 只是没人回头
删表。结案记录在此，ROADMAP 侧已移除。

| # | 问题 | 决定 | 落点 |
|---|---|---|---|
| Q1 | HRV threshold 用绝对值还是相对 baseline | **两者都要**：绝对 30 作红线（触发熔断），`hrv_rel_baseline_min: 0.85` 作黄线（只 log 不熔断）。baseline 54 时 HRV 45 就值得注意，远早于跌到 30 | `config/thresholds.yaml` `sleep.hrv_warning_low` / `readiness.hrv_rel_baseline_min` |
| Q2 | `awake_min_max: 20` 太严 | 放宽到 40，并改名 `awake_min_warning`（它是预警不是硬上限）。实测 70min 那晚睡 7.65h、HRV 50，不算差 | `config/thresholds.yaml` `sleep.awake_min_warning` |
| Q3 | `migrate.py --apply` 要不要改 `data/` git 历史 | **不做 filter-branch**。单开分支批量 rewrite frontmatter，人审 diff，一次 `chore(data): migrate schema` commit。`--apply` 已实现为 dry-run by default | `scripts/lib/migrate.py` |

教训与 §4 同源：**「待拍板」表也需要执行「做完就删」的规则**。一个决策落地后留在待决
清单里，成本不是磁盘空间，是每次 review 都要重新判断一遍它到底做没做。

---

---

## 3. Kill criteria —— decision journal 三级熔断

任一触发就重新评估，不许「再跑一个季度看看」：

| 级别 | 条件 | 验证什么 | 行动 |
|---|---|---|---|
| **Capture kill** | 12 周内决策数 < 5 | 捕获习惯没形成 | schema 太重或入口不对 —— 重新设计或放弃 L1 |
| **Review kill** | 12 周内 reviewed + pushed < 2 | 回顾习惯没形成 | surface 机制无效（`make check` 被忽略？）—— 修 nudge 或放弃 |
| **Value kill** | 6 个月内 0 条 lesson 影响后续行为 | 日志是 write-only | 有捕获价值无学习价值 —— 降级为纯归档，不投入 Phase 2 |

**成功长什么样**（6 个月）：≥ 12 条 reviewed；≥ 1 条 `calibration_delta: worse` 且其 lesson
被后续 daily / weekly 引用；用户至少一次主动说「我去查一下决策日志」；`decision_type` 里
proactive ≥ 30%（否则日志只记录了被迫应对）。

---

## 4. 已撤回的审计结论，与那条元教训

2026-08 那轮审计复核共撤回 12 条结论。其中 **4 条源于同一个原因**：环境观测与结论撰写
之间存在时间差，而观测没有在定稿前复采一次。

| 曾经断言 | 实际 |
|---|---|
| `data/` submodule 未初始化，目录空且无 `.git` | 已 checkout 到 `heads/main`，内含 daily/ decisions/ finance/ fitness/ jobs/ |
| 隐私隔离靠本机 `.git/config` 的 `submodule.data.update = none` | **该配置不存在**。真正的隔离机制是 `personal-os-data` remote 为 private |
| `.venv` 不存在，`make report` 在 lint 环节就失败 | `.venv` 存在。假绿的真实条件是「`.venv` 就绪 + 当周无日志」 |
| 配置里的 `/Users/kelvin/...` 是旧用户名旧路径 | ~~用户名和路径都是当前值~~ **这条撤回本身是错的（2026-08-24 复核）**：真实身份是 `kelvin.you`，真实路径是 `~/Documents/dev/personal-os`，`/Users/kelvin` 目录不存在。原审计结论正确，hook 是死的。详见下方补记 |

**元教训**：这比任何单条技术债都值得先修 —— 它决定整份报告的可信度上限。
**环境事实由脚本采集，不手写**，审计报告的环境节直接贴脚本输出；要加检查就扩
`make doctor`，不要新开 make target（原计划的 `make audit-env` 已从 ROADMAP 撤掉，
理由见 [ROADMAP §3](ROADMAP.md#3-没有时钟的--想做就做不做也不亏)）。

**2026-08-24 补记 —— 这条元教训第二次被自己验证。** 上表第 4 行的「撤回」是手写的
环境观测，而它是错的：`.codex/hooks.json` 里写的是 `/Users/kelvin/Documents/coding/
personal-os`，实际是 `/Users/kelvin.you/Documents/dev/personal-os`，`/Users/kelvin`
根本不存在。也就是说，一份以「不要手写环境事实」为教训的文档，用手写环境事实撤销了
一条**正确**的发现，并让那个坏掉的 hook 多活了一段时间。

**处置**：`.codex/hooks.json` 已整体删除 —— 它唯一的内容就是那个坏掉的 SessionStart
hook，指向的 `.codex/hooks/` 目录从未存在过，所以没有「修好」这个选项，只有删。
`.codex/config.toml` 与此无关，保留。同批补上了 `tests/test_logic_engine.py`：
逻辑引擎此前一条断言都没有，而它恰好是「坏了也不报错、只是安静地不告警」的类型。

撤回一条结论所需的证据强度，不低于当初提出它所需的强度。

另外三条方法论修正，值得在下次审计时记住：

- **白名单不能基于数值** —— 同一个字面量可以同时是公开税务额度和个人现金流，必须行级豁免
- **`extra="allow"` 有 10 处不是 1 处**，且做 owner 测试时要区分「配置对象属性」与「日志对象属性」，否则误判
- **先标 owner 再测试** —— 曾同时主张「这五个配置块不是脚本输入」和「断言所有 `sleep.*` 键都被消费」，两条规则互相打架。正确顺序是先给每块标 owner（engine / skill），再按 owner 分别测

---

## 5. 风险登记

| # | 风险 | 缓解 |
|---|---|---|
| R1 | pydantic 严格 schema 会暴露「以前能 load 但不符合新 model」的老日志 | `migrate.py` dry-run 先列出，apply 前人审 |
| R2 | 形式主义衰减 —— 决策日志变成打卡 | 极简 schema + 主动 surface；触发 Capture kill 就停 |
| R3 | review 时事后合理化 —— 把 `expected_outcome` 改造成已发生的结果 | review 流程要求**先**朗读原文 expected 再写 actual；expected 字段 immutable |
| R4 | 决策内容比 daily log 更敏感（人际 / 薪资 / 关系） | 已在 private submodule；考虑 `private: true` flag 让 weekly review 跳过引用 |
| R5 | Wave 4 的 actuals 对账质量取决于 Brain Dump 的详细程度 | 质量差就回滚 E3/E4，保住 E1/E2 的结构化排期 |
