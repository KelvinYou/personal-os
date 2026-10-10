# Personal-OS — Roadmap

> **本文件是「还没做的事」的唯一 owner。** 做完的条目从这里**删掉**，不留 strike-through
> —— 完成记录归 git log，设计取舍归 [DECISIONS.md](DECISIONS.md)。
>
> 这条规则是从被它删掉的三份文档里学来的：`plan.md` 曾长到 898 行，其中 ~85% 是已完成
> 项的历史；读者要翻过四个 Wave 的 ✅ 才能找到唯一还活着的 Wave 4。计划文档一旦兼任
> 归档，就没人读了。
>
> **排序规则（2026-08-24 加）：按「时效 × 价值」排，不按依赖排。** 上一版按"无前置依赖"
> 把 30 分钟的路径重构放在第 1 节、把唯一有外部截止时间的上云任务放在第 4 节。文档顺序
> 就是注意力顺序 —— 这是 plan.md 那个病的变体：不是已完成项淹没活着的项，是低价值项
> 淹没高价值项。
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
| Agent self-audit（`make eval` / `eval-rollup`） | ✅ 已落地 —— 唯一审计 **agent** 而非审计我的回路；`judgement` 留空等 `/meta-coach` 或人填，见 [DECISIONS §2](DECISIONS.md) |
| daily / weekly evidence | ✅ Official COROS MCP supplies live evidence on demand; manual fields remain unknown when unrecorded |

---

## 1. 有外部时钟的 —— 拖延本身就是成本

这一节的条目和其它条目的区别：**代价随时间累积**。其它事晚一个月做，成本不变。

- [ ] **P0 — 一个真实后端服务上云**（6–8 周）。
      目标 MY 市场 RM 11k/月档。据 `market/jobs/` 45 份 MY AI/full-stack JD：
      backend ownership 58% / cloud 56% / system design 56% / RAG 38%。当前 portfolio
      的证据链是 frontend-shaped，**唯一的硬缺口是「云上生产 + 可观测」**。
      拿 `ai-stock-analysis` 的 FastAPI 层改，别新开项目：
    1. 容器化跑在 ECS / Cloud Run / Fly（**不是** Vercel），自己配 secrets 与 migration
    2. GitHub Actions：build → test → deploy，带 rollback
    3. 结构化日志 + p50/p95 latency + error rate dashboard
    4. 产出一句能写进简历的话：`p95 <XXXms at N rps, $Y/mo`

      整个 portfolio 目前没有任何一个 production reliability 数字，这一条才是真正值钱的。
      只在 skills 列表里写 AWS/GCP 而不做这些是空头 claim ——
      `repos/portfolio-website/src/constants/data.ts` 的 `skills.delivery` 处留了同样的注释。

---

## 2. Telemetry-first logging and on-demand Calendar

Work entries are optional. The weekly report analyzes work only where the owner wrote evidence; a blank field
must not become assumed hours or a missed objective. Official COROS MCP is the live health source; no routine daily-file copy is required.
Real body measurements remain manually entered. The current contract is
[the official MCP design](design/coros-official-mcp.md). A standard week needs no Calendar record or sync;
publish a schedule change to Google Calendar only when requested. The owner → consumer map, scoring cutover,
historical compatibility, definition cleanup, and gates are in [the consolidated plan](plans/telemetry-and-definition-consolidation.md).

The previous Wave 4 per-block schedule and actuals expansion is withdrawn. It would add routine work tracking
that the owner does not want. Do not implement E1–E4 or `scripts/apply_schedule.py` without a new decision.

---

## 3. 没有时钟的 —— 想做就做，不做也不亏

- [ ] **`scripts/lib/paths.py` —— 路径常量收敛**。全仓 26 处各自计算 repo root，
      写法还有 `parents[N]` 与 `parent.parent` 两种变体，导致 grep 不到全集。
      收敛成单一 `ROOT` 常量。适合当"启动困难时的热身任务"。
- [ ] **P1 — Retrieval + eval**. Follow the LLM and evaluation phases in
      [the foundations plan](plans/ai-native-full-stack-foundations.md).
      Start with database queries or text search; add vector retrieval only when
      measured retrieval failures justify it.
- [ ] **P2 — system design 的表达**。素材已经有了（FX rate lock / per-row settlement /
      RFI state machine），缺的是讲成取舍的能力。这是**面试**丢分点，不是简历丢分点，
      所以不占 §1 的位置 —— 但它和 P0 共享同一个 deadline。

> 上一版这里还有一条 `make audit-env`（输出 commit / submodule status / `.venv` /
> remote 可见性）。**已撤掉**：动机是 DECISIONS §4 的「环境事实必须由脚本采集」，
> 但那个教训已由 `make doctor` 覆盖大半，再加一个 make target 只会分裂环境自检的入口。
> 要做就扩 `make doctor`，不要新开。

---

## 4. 其他线（详细计划在各自文档里，这里只登记状态）

| 线 | 待办 | 详细计划 |
|---|---|---|
| AI-native full-stack foundations | Planned: execution → backend/data correctness → reliable LLM features → evaluation and operations; supports the existing P0 cloud milestone | [plans/ai-native-full-stack-foundations.md](plans/ai-native-full-stack-foundations.md) |
| Wealth dashboard | Phase D（知识库浏览页）· Phase E（历史趋势展示） | [plans/wealth-dashboard.md](plans/wealth-dashboard.md) §4 |
| Duplicate definitions | Decision-reader extraction remains deferred until capture value is reassessed; wealth types, nutrition parity, finance dates, and command discovery are implemented | [consolidated plan](plans/telemetry-and-definition-consolidation.md) |
| Public mirror | 3 项发布前检查；阈值泄漏核对与 [合并计划 Phase 1](plans/telemetry-and-definition-consolidation.md#phase-1--fix-live-instructions-and-make-telemetry-records-possible) 联动，完成公开路径扫描后再勾选 | [drafts/personal-os-public-readme.md](drafts/personal-os-public-readme.md) |
| LinkedIn / JobStreet | headline · About · DTCPay bullets · skills 排序，外加 4 项数字核实 | [drafts/profile-updates-2026-08-14.md](drafts/profile-updates-2026-08-14.md) |

> These tracks maintain their detailed checklists only in the linked documents. Duplicating a checklist here creates competing owners —
> `AGENTS.md` / `CLAUDE.md` 已经因此漂移过一次。

---

## 5. 待拍板（决定了就搬去 DECISIONS.md）

| # | 问题 | 现有建议 |
|---|---|---|
| Q5 | D4 scoring 上线后要 backfill 历史周报吗？ | 生成 `*-backfill-score.md` 记新旧对比，不替换原 report |

> 2026-08-24 清理：原 Q1（HRV 绝对 vs 相对）、Q2（`awake_min_max` 太严）、Q3
> （`migrate.py --apply` 改不改 git 历史）**代码里早已按建议实现**，只是没人回头删表。
> 三条已结案并移入 [DECISIONS §2](DECISIONS.md)。
> 教训：header 那条「做完就删」的规则对本表同样适用 —— 一个已落地的决策留在待决清单
> 里，成本是每次 review 都要重新判断一遍它到底做没做。

---

## 6. 中长期（VISION 的演进方向，尚未拆解）

- Optional new device imports, after a reliable measured source exists; COROS now uses official MCP, and `body.*` remains owner-entered (DECISIONS §1)
- 历史数据查询层（SQLite 作**查询缓存**，不是 source of truth —— 见 DECISIONS §1）
- 睡眠债务预测模型（时序分析）
- 训练负荷周期化（mesocycle 自动排期）
- 支出燃烧率预警（月度 burn-rate projection）
- Mobile companion（时间表推送 + 快速 brain dump）
- 穿戴设备实时流（心率 / HRV → 自动触发 breaker）
- 多用户抽象（从 personal tool → 可复用框架）
