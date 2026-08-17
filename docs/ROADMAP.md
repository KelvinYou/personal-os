# Personal-OS — Roadmap

> **本文件是「还没做的事」的唯一 owner。** 做完的条目从这里**删掉**，不留 strike-through
> —— 完成记录归 git log，设计取舍归 [DECISIONS.md](DECISIONS.md)。
>
> 这条规则是从被它删掉的三份文档里学来的：`plan.md` 曾长到 898 行，其中 ~85% 是已完成
> 项的历史；读者要翻过四个 Wave 的 ✅ 才能找到唯一还活着的 Wave 4。计划文档一旦兼任
> 归档，就没人读了。
>
> 上游：`../ARCHITECTURE.md`（系统不变量）· [VISION.md](VISION.md)（产品方向）

---

## 0. 现在的状态

| 层 | 状态 |
|---|---|
| daily / weekly / coach 三层 | ✅ 运行中 |
| Library layer (`scripts/lib/`) | ✅ 已落地（schema / daily_log / metrics / breakers / score / logger / migrate） |
| Meta-cognition L1–L3（decision-log / meta-coach / identity-audit） | ✅ skill 已就绪，等数据积累 |
| Wealth: Tracked Assets Phase A–C | ✅ 已落地 |
| **plan → measure 闭环** | ❌ 缺失 —— 见 §2，本仓库最大的结构性空洞 |

---

## 1. 小项（无前置依赖，随时可做）

- [ ] **`scripts/lib/paths.py` —— 路径常量收敛**。全仓 24 处各自计算 repo root
      （22 处 production + `sys.path` 注入 6 处），写法还有 `parents[N]` 与
      `parent.parent` 两种变体，导致 grep 不到全集。收敛成单一 `ROOT` 常量。
- [ ] **`make audit-env`** —— 输出 commit / submodule status / `.venv` 是否存在 /
      remote 可见性。理由见 [DECISIONS.md §4](DECISIONS.md#4-已撤回的审计结论与那条元教训)：
      手写环境观测已经害过一次，环境事实必须由脚本采集。
- [ ] **breaker 加 `enforcement: auto | advisory` 字段**。Spending Surge 的三条 action
      没有一条能被 `breakers.py` 执行，全是给 agent 读的 prose，但结构上和可执行
      breaker 混在一起，看不出区别。
- [ ] **`.codex/hooks/` 目录不存在**，而 `.codex/hooks.json` 引用它 —— 真 bug。
      同时把 hooks.json 与 `weekly-review/SKILL.md` 里的绝对路径 `/Users/kelvin/...`
      换成 `$CLAUDE_PROJECT_DIR`（当前值是对的，问题是不可移植）。
- [ ] **Logic engine 单元测试覆盖**（`tests/`，继续用 `unittest`，不引入 pytest）。

---

## 2. Wave 4 — Planned-vs-Actual 闭环 ⏸ deferred

**为什么它重要**：现系统有 measure → diagnose → plan 三段，缺 plan → measure 回路。
coach-planner 排了周一 09:00–12:00 DW Project X，当晚 `/daily-report` 记
`deep_work_hours: 6`，但没有任何结构化字段记录「6h 里多少是 Project X」。周报只能靠
叙事推断「好像按计划走了 70%」。Wave 4 把执行率变成硬指标。

**总成本** ~5h + 2–4 周观察期。**启动条件**：E1/E2 先落地并跑满 1 周，确认 coach-planner
的输出仍然顺手，再做 E3/E4。

| # | 内容 | 关键文件 | 成本 |
|---|---|---|---|
| **E1** | `daily.md` frontmatter 新增 `planned_schedule[]` + `actuals[]` 两块；`lib/schema.py` 加 `PlannedBlock` / `Actual`；`lib/migrate.py` 让老日志默认 `[]` | `templates/daily.md`, `lib/schema.py`, `lib/migrate.py` | ~45min |
| **E2** | coach-planner 排期时**同时**写 markdown（给人看）和目标日 `planned_schedule`（给聚合用）；新增 `scripts/apply_schedule.py` | `coach-planner/SKILL.md`, `scripts/apply_schedule.py` | ~1.5h |
| **E3** | `/daily-report` 先读 `planned_schedule`，再从 Brain Dump 对账填 `actuals[]`；计划外活动记 `block_ref: null` | `daily-report/SKILL.md` | ~1h |
| **E4** | `lib/metrics.py::compute_adherence()` → `AdherenceReport`（done / partial / missed / replaced、adherence_pct、按 type 分组）；weekly-review 把它作为 **Habits 分的子项**（不新增第五维度，避免分数膨胀）；coach-planner 读上周 adherence 决定下周排多少 block | `lib/metrics.py`, `weekly_synthesis.py`, 两个 SKILL.md | ~1.5h |

**回滚计划**：任一阶段发现 AI 对账质量差或用户抗拒，回滚到当前状态 —— schema 字段保留
默认 `[]`，不 break 已有流程。E3 是最脆的一环（依赖 Brain Dump 的自然语言质量）；砍掉
E3/E4 仍能保住 E1/E2 的结构化排期价值。

---

## 3. 其他线（详细计划在各自文档里，这里只登记状态）

| 线 | 待办 | 详细计划 |
|---|---|---|
| Wealth dashboard | Phase D（知识库浏览页）· Phase E（历史趋势展示） | [plan-wealth-dashboard.md](plan-wealth-dashboard.md) §4 |
| Public mirror | 3 项发布前检查（阈值泄漏核对 / `demo/` fixture 数据 / 仓库命名） | [personal-os-public-readme-draft.md](personal-os-public-readme-draft.md) |
| LinkedIn / JobStreet | headline · About · DTCPay bullets · skills 排序，外加 4 项数字核实 | [profile-updates-2026-08-14.md](profile-updates-2026-08-14.md) |

> 这三条**只在那边维护**。在这里复制一份 checklist 是两处并存的起点 ——
> `AGENTS.md` / `CLAUDE.md` 已经因此漂移过一次。

---

## 4. 技能缺口（2026-08-17 招聘数据复盘）

目标：MY 市场 RM 11k/月档。根据 `market/jobs/` 45 份 MY AI/full-stack JD，
backend ownership 58% / cloud 56% / system design 56% / RAG 38%。当前 portfolio 的
证据链是 frontend-shaped，**唯一的硬缺口是「云上生产 + 可观测」**。

- [ ] **P0 — 一个真实后端服务上云**（6–8 周）。拿 `ai-stock-analysis` 的 FastAPI 层，
      别新开项目：
    1. 容器化跑在 ECS / Cloud Run / Fly（**不是** Vercel），自己配 secrets 与 migration
    2. GitHub Actions：build → test → deploy，带 rollback
    3. 结构化日志 + p50/p95 latency + error rate dashboard
    4. 产出一句能写进简历的话：`p95 <XXXms at N rps, $Y/mo`
      —— 整个 portfolio 目前没有任何一个 production reliability 数字，这一条才是真正值钱的。
- [ ] **P1 — RAG / retrieval + eval**（~2 周）。outcome-memory 与 calibration reporting
      已经是 eval 思维，缺的只是 vector retrieval 那一段，可以直接接进现有 pipeline。
- [ ] **P2 — system design 的表达**。素材已经有了（FX rate lock / per-row settlement /
      RFI state machine），缺的是讲成取舍的能力。这是面试丢分点，不是简历丢分点。

> 只在 skills 列表里写 AWS/GCP 而不做上面这些，是空头 claim ——
> `repos/portfolio-website/src/constants/data.ts` 的 `skills.delivery` 处留了同样的注释。

---

## 5. 待拍板（决定了就搬去 DECISIONS.md）

| # | 问题 | 现有建议 |
|---|---|---|
| Q1 | HRV threshold 用绝对值 30 还是相对 baseline？ | 两者都要：绝对 30 作红线（触发强制恢复日），另加 `hrv_rel_baseline_warning: 0.85` 作黄线（只 log，不触发 breaker）。用户 baseline 54 → HRV 45 就值得注意，远早于跌到 30 |
| Q2 | `awake_min_max: 20` 太严？ | 调到 40。实测 70min 那晚睡 7.65h、HRV 50，并不算差 |
| Q3 | `migrate.py --apply` 要不要改 `data/` 的 git 历史？ | 不做 filter-branch。单开分支批量 rewrite frontmatter，人审 diff，一次 `chore(data): migrate schema` commit |
| Q4 | `planned_schedule.time` 的格式？ | 保留人类友好的 `"09:00-12:00"` 字符串，在 `lib/schema.py` 里 parse 成 tuple。不用 ISO duration —— 过度工程 |
| Q5 | D4 scoring 上线后要 backfill 历史周报吗？ | 生成 `*-backfill-score.md` 记新旧对比，不替换原 report |

---

## 6. 中长期（VISION 的演进方向，尚未拆解）

- COROS / Zepp 数据自动导入（CSV / API）—— 注意 body.* 字段是刻意手填的，见 DECISIONS §1
- 历史数据查询层（SQLite 作**查询缓存**，不是 source of truth —— 见 DECISIONS §1）
- 睡眠债务预测模型（时序分析）
- 训练负荷周期化（mesocycle 自动排期）
- 支出燃烧率预警（月度 burn-rate projection）
- Mobile companion（时间表推送 + 快速 brain dump）
- 穿戴设备实时流（心率 / HRV → 自动触发 breaker）
- 多用户抽象（从 personal tool → 可复用框架）
