# Personal-OS Architecture Optimization Plan

> Generated: 2026-04-22 | Revised: 2026-04-22 (post-Wave-1 review) | Implemented: 2026-04-23
> Scope: post-COROS-integration architecture review
> Author: Claude (architecture scan + synthesis)
> Status: **Wave 1 / 2 / 2.5 / 3 ✅ done (2026-04-23 session) · Wave 4 — deferred (需 2-4 周观察期)**

---

## 0. Progress Log

| Wave | Items | Status | Evidence |
|------|-------|--------|----------|
| Wave 1 | A1 metric 改名 · A2 crash 修复 · A4 Poor Sleep derivation · A5 report_gen 迁移 | ✅ Done | commit `f4b943e` — `report_gen.py` 已用 `rolling_7d_sleep_debt` / `readiness.hrv` / Option P-d derivation |
| Wave 1 | A3 weekly_synthesis 迁移 | ✅ Done (2026-04-23) | `weekly_synthesis.py` 重写，使用 `lib.metrics` + 新 schema + rolling_7d_sleep_debt 对齐 |
| Wave 2 | B1 skill rubric · B2 daily-report 清理 · B3 thresholds · B4 聚合 | ✅ Done (2026-04-23) | SKILL.md 更新为"代码算 base + AI 做 qualitative"；thresholds 新增 readiness 块 + deep_min_range 等；lib.metrics 一次性聚合 COROS 三块 |
| Wave 2.5 | D1 pydantic library · D2 lint · D3 tests · D4 score · D5 logger · D6 migrate | ✅ Done (2026-04-23) | `scripts/lib/{schema,daily_log,metrics,breakers,score,config,logger,migrate}.py` · `make lint` · `tests/test_smoke.py` (13 tests green) · `data/logs/engine-*.jsonl` · 28 老日志批量 migrate 成功 |
| Wave 3 | C1 prompts 死引用 · C3 sync_scale · C4 `make daily DATE=` · C5 路径常量 | ✅ Done (2026-04-23) | weekly_synthesis 重写已无 PROMPTS_DIR · Makefile 新增 `daily` target · C6 留待 user 确认 eval artifacts 是否保留 |
| — | Plan 扩容 v2（"成本不限"版本）| ✅ 2026-04-23 revision | Wave 2.5 升级为 pydantic-backed library；D4 scoring 从 P3 promoted to P1；新增 D5 logger / D6 migrate；新增 Wave 4 planned-vs-actual 闭环 |
| Wave 4 | E1–E4 planned_schedule + actuals 闭环 | ⏸ Deferred | plan §5 明确要求 Wave 2.5 稳定 1 周 + 2-4 周观察期后再启动；用户可在周报质量不满意时触发 |

**剩余最大 liability**：`weekly_synthesis.py` schema 未迁移 → 周报 "Avg Deep% / Avg REM% / Avg HRV / Poor Sleep days" 全部 silently = 0；且它填 `cumulative_sleep_debt` 而非 `rolling_7d_sleep_debt`，两个 Sleep Debt 熔断器在周度 pipeline 中仍永不触发（只是 `make check` 那条路径已修好）。

**新增结构性工作**（v2 修订纳入）：
- Library Layer（`scripts/lib/` 8 个模块，pydantic-backed）替代原"抽共享函数"
- Deterministic scoring（`lib/score.py` + `thresholds.yaml` 扩展），AI 只做 qualitative
- Planned-vs-Actual 闭环（Wave 4，基础设施 + 2-4 周试用期）

---

## 1. Executive Summary

系统刚经历 COROS 集成（新增 `sleep/readiness/training/activities` 四块 frontmatter + `sync_coros.py`/`patch_coros.py`）。Wave 1 已经把 `report_gen.py` 上的两处 pre-existing 静默 bug 修掉（`KeyError` 崩溃 + 熔断器 metric 名不匹配），但下游仍有三类问题：

1. **`weekly_synthesis.py` 未迁移** —— 仍引用 `sleep.quality` / `deep_pct` / `rem_pct` / `sleep.hrv`，导致周报 prompt 里睡眠结构数据全 0；熔断器填错 metric 名，周度 pipeline 中 Sleep Debt L1/L2 + HRV Alert 仍然不会真实触发。
2. **SKILL.md 评分规则仍依赖已删字段** —— `weekly-review/SKILL.md` 三行评分、`daily-report/SKILL.md` 三行抽取规则都指向旧 schema，AI 会尝试编造或给出无来源分数。
3. **数据无用化** —— 新加的 `readiness.*` / `training.*` / `activities[]` 三块目前在两个聚合脚本里零消费，只是装饰在 daily log 里。

外加一类**结构性隐患**（Wave 1 的 drift 之所以发生的根因）：两个脚本**各自独立**实现 frontmatter 解析、`safe_float`、breaker evaluator、Poor-day derivation，schema 改动必须两处同步。目前没有任何自动化校验（lint / test / CI）能在"忘了改第二处"时报错。

**总工作量估计**：P0 剩余约 1-1.5h（weekly_synthesis 迁移 + 熔断器 fill 对齐），P1 skill + config 对齐 1.5h，P2 架构加固 2-3h（抽 lib + lint），P3 清理 0.5h。总计 5-6.5h。

**最大剩余 unlock**：A3 做完后周报数据不再是假 0；Wave 2.5 做完后下次 schema 改动不再需要"人肉检查两处脚本是否同步"。

---

## 2. System Snapshot

### 2.1 当前数据流 (Data Flow)

```
                                    ┌──────────────────────────────┐
                                    │    COROS API (unofficial)    │
                                    └──────────────┬───────────────┘
                                                   │  sync_coros.py
                                                   ▼
                                    data/fitness/YYYY-MM-DD.yaml
                                                   │  patch_coros.py
                                                   ▼
Brain dump ──[daily-report skill]──► data/daily/YYYY-MM-DD.md (frontmatter + markdown)
                                                   │
                                                   │  手动: body.* 手填（Zepp 已 revert）
                                                   │  手动: highlights / blockers / spend / energy
                                                   ▼
                                    ┌──────────────┴──────────────┐
                                    │                             │
                     scripts/report_gen.py            scripts/weekly_synthesis.py
                       (daily logic engine)          (weekly aggregation → prompt)
                                    │                             │
                            alerts (stdout)         weekly_report_prompt.md
                                                                  │
                                                                  ▼
                                                    [weekly-review skill]
                                                                  │
                                                                  ▼
                                    data/reports/YYYY-w##-weekly-report.md
                                    (含 P0/P1/P2 目标 + 熔断约束)
                                                                  │
                                                                  ▼
                                                    [coach-planner skill]
                                                                  │
                                                                  ▼
                                    data/reports/YYYY-w##-timetable.md
                                    或 append 到 daily 的 "今日计划" section
```

### 2.2 组件清单

| 组件 | 职责 | 状态 | 备注 |
|------|------|------|------|
| `config/thresholds.yaml` | 阈值 + 熔断规则 | 🟡 drifted | 5 个旧 schema 字段（`deep_pct_range`/`rem_pct_range`/`light_pct_max`/`awake_min_max:20`/`interruptions_max:1`），无 `readiness` 块；HRV 仅绝对阈值 30 |
| `templates/daily.md` | frontmatter 模板 | ✅ OK | 已更新为新 schema |
| `scripts/sync_coros.py` | COROS 拉取 + 落盘 + 调 patch | ✅ OK | 本次新增 |
| `scripts/patch_coros.py` | 把 fitness yaml merge 进 daily.md | ✅ OK | 本次新增 |
| ~~`scripts/sync_scale.py`~~ | Zepp CSV → body.* | ✅ 已删 | C3 完成；Makefile `sync-scale` target 也已移除 |
| `scripts/report_gen.py` | daily logic engine | ✅ 已迁移 | commit f4b943e — 新 schema / Option P-d / breaker metric 对齐 / `if actual is None: continue` 防 false positive |
| `scripts/weekly_synthesis.py` | 周度聚合 | 🔴 **数据失真** | L107-125 读 `deep_pct`/`rem_pct`/`sleep.quality`；L188 填 `cumulative_sleep_debt`（熔断器 key 不匹配）；新 COROS 块零消费；L245-250 仍引用不存在的 `prompts/weekly_review_agent.md`（有 fallback 不崩） |
| `.claude/skills/daily-report/SKILL.md` | brain-dump 结构化 | 🟡 drifted | L29, L31 提取已删字段（quality/bedtime/wakeup） |
| `.claude/skills/weekly-review/SKILL.md` | 评分 + P0/P1/P2 输出 | 🟡 drifted | L67/69/88 三处评分规则依赖旧字段 |
| `.claude/skills/coach-planner/SKILL.md` | 时间表生成 | ✅ OK | 使用新字段（`sleep.duration` 等），无修复需要 |
| `.claude/skills/coach-planner/references/*` | 排期格式 / 饮食库 | ✅ OK | |
| `.claude/skills/coach-planner-workspace/` | eval artifacts | ⚫ 归档候选 | 迭代过程产物，不影响运行 |
| `Makefile` | 入口 | ✅ OK | `check` target 已可跑通；缺 `daily` / `lint` / `clean` 等 QoL target |
| `user_profile.md` | 用户画像 | ✅ OK | 无旧字段引用 |
| `.venv/` + `~/tools/coros-mcp/` | Python 环境 | ✅ OK | |
| **(缺)** `scripts/lib/` | 共享 log 解析 / breaker eval | ❌ 不存在 | schema drift 根因 — 两个脚本各写各的，改 schema 需人工同步；详见 Wave 2.5 D1 |
| **(缺)** `scripts/lint_daily.py` + `tests/` | 字段校验 / smoke test | ❌ 不存在 | 无自动化检测 schema drift 的机制；详见 Wave 2.5 D2/D4 |

---

## 3. Findings

### 3.1 Schema Drift（剩余 5 处）

新 schema 删除了 `sleep.quality` / `sleep.bedtime` / `sleep.wakeup` / `sleep.interruptions` / `sleep.deep_pct` / `sleep.rem_pct` / `sleep.light_pct`；新增 `sleep.deep_min` / `light_min` / `rem_min` / `nap_min` / `avg_hr` / `min_hr` / `max_hr`，以及 `readiness:` / `training:` / `activities:` 三个顶级块。

| # | 位置 | 具体问题 | 严重度 | 状态 |
|---|------|----------|--------|------|
| D1 | `scripts/weekly_synthesis.py:107-125, 164-167, 228-229, 274-276` | 聚合 `deep_pct`/`rem_pct`/`sleep_quality` 和 `consec_poor` — 新日志全部产生 `0` / `[]`，周报里 "深睡占比 0%"、"Poor 睡眠 0 天" 均为 false-negative | 🔴 P0 | ❌ 待修（A3） |
| ~~D2~~ | ~~`scripts/report_gen.py:78-86, 131-137, 161-168`~~ | ~~`sleep_q = sleep_data.get("quality")` 永远为 None，Rule 3 睡眠质量追踪 + Rule 连续 Poor 告警彻底失效~~ | 🔴 P0 | ✅ 已修（commit f4b943e，Option P-d derivation） |
| D3 | `.claude/skills/weekly-review/SKILL.md:67` | Health 评分 "Sleep quality: 0 Poor days = 10 pts" — 新 schema 没有 quality 字段，这项评分没有输入 | 🟡 P1 | ❌ 待修（B1） |
| D4 | `.claude/skills/weekly-review/SKILL.md:69` | Health 评分 "deep% in range, HRV stable" — deep% 已删，要换成 `deep_min` 或比率计算 | 🟡 P1 | ❌ 待修（B1） |
| D5 | `.claude/skills/weekly-review/SKILL.md:88` | Habits 评分 "Bedtime/wakeup consistency (stddev of bedtime < 30min)" — 两个字段已删，这 2 分目前无法合规给出 | 🟡 P1 | ❌ 待修（B1） |
| D6 | `.claude/skills/daily-report/SKILL.md:29, 31` | Brain-dump 抽取规则要求产出 `sleep.quality` / `sleep.bedtime` / `sleep.wakeup` — AI 会尝试编造（违反模板） | 🟡 P1 | ❌ 待修（B2） |
| D7 | `config/thresholds.yaml:15-20` | `deep_pct_range` / `rem_pct_range` / `light_pct_max` / `awake_min_max=20` / `interruptions_max=1` — 前 3 个键已无字段映射；`awake_min_max` 新 schema 仍有但阈值 20 min 偏严（用户 04-21 即 70min）；`interruptions_max` 字段已删 | 🟢 P2 | ❌ 待修（B3） |

### 3.2 Pre-existing Bugs（**不是这次引入的**，但一并修掉）

#### ~~B1. `report_gen.py:47` 读取不存在的键 → `make check` 崩溃~~ ✅ 已修（commit f4b943e）

原问题：`report_gen.py:47` 用 `critical_debt = config["sleep"]["critical_debt_hours"]` 会 `KeyError`。解决方案：采用 Option (b) — 删除 flat-threshold 告警路径，交由 Sleep Debt L1/L2 熔断器覆盖。`make check` 现在能跑通。

#### B2. 熔断器 metric 名字全线对不上 🟡 部分已修

| 熔断器 | 条件 metric | `report_gen.py` | `weekly_synthesis.py` |
|---|---|---|---|
| Sleep Debt L1 | `rolling_7d_sleep_debt >= 5.0` | ✅ 已填（`:147`） | ❌ 仍填 `cumulative_sleep_debt`（`:188`） |
| Sleep Debt L2 | `rolling_7d_sleep_debt > 8.0` | ✅ 已填 | ❌ 同上 |
| HRV Recovery Alert | `hrv < 30` | ✅ 已填 `readiness.hrv`（`:148-149`），且 `if actual is None: continue` 防 false positive | ❌ 未填 + 无 None-guard |

**结论**：daily `make check` 路径正确；周度 pipeline (`make weekly`/`make report`) 仍会报错或假 OK。A3 完成时一并处理。

#### B3. `prompts/` 目录不存在但被引用 🟢 P2

`weekly_synthesis.py:15` 定义 `PROMPTS_DIR = PROJECT_ROOT / "prompts"`，L245-250 试图读 `weekly_review_agent.md`。目录本身不存在，但 fallback 逻辑（L248-250）写了"你现在是系统配置的 Weekly Review Agent"的一行 stub prompt，不会崩溃。

此代码路径为**历史遗留** —— weekly-review skill 已经把完整 system prompt 写进 SKILL.md 了，`weekly_synthesis.py` 产出的 `weekly_report_prompt.md` 只需包含数据部分，不需要再拼系统 prompt。

### 3.3 Dead Data（新 COROS 块零消费）

`sync_coros.py` 落盘的 3 个新块**目前没有任何 downstream 读取**：

| 块 | 关键字段 | 潜在消费者 | 当前状态 |
|---|---|---|---|
| `readiness.hrv` | 夜间 HRV | `report_gen.py` HRV Recovery Alert | ❌ 未读（熔断器 metric 名字对不上） |
| `readiness.hrv_baseline` | 7 日 baseline | 相对 HRV 偏差告警（更合理） | ❌ 未读 |
| `readiness.rhr` | 静息心率 | 可做 RHR 升高预警 | ❌ 未读 |
| `readiness.tired_rate` | 疲劳指数 | 直接进 daily scoring | ❌ 未读 |
| `readiness.load_ratio` | ATI/CTI 比 | **过训预警**（>1.5 触发） | ❌ 未读 |
| `readiness.stamina_level` | 体能储备 | 跑步后参考 | ❌ 未读 |
| `training.today_load` | 当日训练负荷 | 周度累计负荷 | ❌ 未读 |
| `training.vo2max` | 长期心肺 | 周报趋势 | ❌ 未读 |
| `activities[]` | 结构化训练记录 | **自动统计 "本周训练 N 次"**（目前靠 AI 从 narrative 推断） | ❌ 未读 |

**Impact**: 用户花力气接入了 COROS，但除了 `sleep.duration` 和 `activities` 的视觉呈现外，**系统的决策循环仍靠旧数据运行**。

### 3.4 Null-handling 现状

之前 W16 报告标注的 "null energy/HRV 触发 false positive" —— 源码里 `safe_float(None, default=0.0)` 的 `default=0.0` 设计在**平均值计算**（L164-168）时是对的（跳过 null 计 0），但在**熔断判定**（L208）时是错的（不存在的 metric 返回 0，自动满足 `< 30` 条件）。

**`report_gen.py` 现状**：已加 `if actual is None: continue`（:171-172），缺数据跳过判定。
**`weekly_synthesis.py` 现状**：`:208` 仍用 `actual = latest_metrics.get(metric_name, 0.0)`，保留 false positive 风险。A3 里同步修掉。

### 3.5 结构性根因（Wave 1 drift 的 root cause） 🟡 架构债

Wave 1 能出现 "schema 改了但两个脚本各自独立不同步" 的 drift，根因是两个脚本**各写各的**以下逻辑：

| 职责 | `report_gen.py` 实现位置 | `weekly_synthesis.py` 实现位置 |
|------|---|---|
| `parse_frontmatter` / `parse_log` | `:21-28` | `:34-43` |
| `safe_float(default=0.0)` | `:31-38` | `:24-31` |
| Poor Sleep Day derivation | `:82-91` (Option P-d) | ❌ 不存在（用已删的 `sleep.quality`） |
| Breaker evaluator 循环 | `:160-180` | `:199-217` |
| `latest_metrics` 收集 | `:127-149` | `:175-197` |

只要 schema 再变（比如加 `body.hydration_ml`），上面 10 处需要**人工同步**。当前唯一的"catch"机制是 user 肉眼审查。**建议把这 5 件事抽出到 `scripts/lib/daily_log.py`**，详见 Wave 2.5 D1。

### 3.6 Skill 边界 / 责任归属

读了所有 SKILL.md，边界总体清楚（coach-planner 排期、weekly-review 评分、daily-report 提取），但有**两处模糊**：

- **`daily-report.SKILL.md` 没说 COROS 数据从哪来** —— 现在的流程是：用户 brain-dump → daily-report 生成 .md（含空 sleep 块）→ 单独跑 `make sync-coros` 填充。如果顺序反了（先 sync-coros 再 daily-report），后者会不会覆盖？需查 SKILL.md 的 "如果该日期文件已存在，先读取现有内容，合并而非覆盖" 是否真的按块级合并。
- **`weekly-review.SKILL.md` 里的 "bedtime 一致性" 评分 (L88)** 只能 fallback 为"睡眠时长一致性"；但谁来决定替换？这种 skill 内部规则调整属于本 plan 的 D5 fix，不需再讨论 ownership。

### 3.7 Makefile 覆盖盘点

现有 target：`today` / `check` / `weekly` / `sync-coros` / `report` / `help`（`sync-scale` 已删）。

潜在缺口：
- **`make today` 不会自动跑 sync-coros** — 用户得手动连续跑两条。可考虑让 `today` depend on `sync-coros` with `DATE=$(yesterday)`，但副作用是每次 `make today` 都打 COROS API。**权衡后建议保持独立**（避免偷跑 API；网络慢时 make today 会卡）。
- **缺 `make daily DATE=...`** —— 当前想补写历史日期得手动 `cp` template。加一个 parametric target 1 行搞定。
- **缺 `make clean`** — `weekly_report_prompt.md` 是 gitignored 的中间产物，偶尔手动删一下；非急需。

---

## 4. Prioritized Action Items

每项格式：**ID · 标题 · 优先级 · 文件 · 工作量 · 依赖 · 验证**。

### Wave 1 — P0 correctness fixes

---

#### ~~A1. 对齐熔断器 metric 名字~~ ✅ Done (commit f4b943e, `report_gen.py` only)

`report_gen.py` 已改用 `rolling_7d_sleep_debt`（`:147`），从 `readiness.hrv` 填 `latest_metrics["hrv"]`（`:148-149`），熔断判定已加 `if actual is None: continue`（`:171-172`）防 false positive。
**⚠️ `weekly_synthesis.py:188` 仍填 `cumulative_sleep_debt`，A3 中一并处理。**

---

#### ~~A2. 修复 `make check` 崩溃~~ ✅ Done (commit f4b943e)

采用 Option (b) — 删除 `critical_debt_hours` 相关的 flat-threshold 告警（`report_gen.py:47, 171-172`），由 Sleep Debt L1/L2 熔断器完全取代。`make check` 现在能跑通。

---

#### A3. 迁移 `weekly_synthesis.py` 到新 sleep schema 🔴 **P0 — 剩余最后一件 Wave 1 工作**

- **Priority**: 🔴 P0
- **Problem**: L107-125 读 `deep_pct` / `rem_pct` / `sleep_quality`，新日志全部 null（见 D1）；同时 L188 填错 breaker metric 名（B2 剩余部分）
- **Approach**:
  1. 读 `deep_min` / `light_min` / `rem_min` / `awake_min` 代替三个 `*_pct`；从 `readiness.hrv` 代替旧 `sleep.hrv`
  2. 砍掉 `sq` / `sleep_quality` / `consecutive_poor_sleep` 旧路径，改用 **Option P-d derivation**（与 `report_gen.py:88-91` 完全一致；理想情况下 Wave 2.5 D1 之后直接 `from lib.daily_log import derive_poor_sleep`）
  3. 把 L226-229 的输出改成 "Avg Deep minutes / Avg REM minutes / Avg HRV"；L274-276 prompt 区块同上
  4. **熔断器 fill 对齐**：把 L188 的 `cumulative_sleep_debt` 改为 `rolling_7d_sleep_debt`（单独计算"最近 7 天 vs baseline"），与 `report_gen.py` 对齐；同时加 `if actual is None: continue` 防 false positive（L208）
  5. **保留 `total_sleep_debt` 作为 display-only 变量**（周报里展示"本周累计负债"），和 breaker 用的 rolling 7d 区分开 — 解决 §6 Q2
- **Files**: `scripts/weekly_synthesis.py:82-125, 164-197, 208, 220-232, 267-281` (~45 行 net)
- **Effort**: M (~45min)（Wave 2.5 D1 若先做可降到 15min）
- **Depends**: 无外部；Wave 2.5 D1 可选前置
- **Verify**: 对 W17 (2026-04-20 起) 跑 `python3 scripts/weekly_synthesis.py --date 2026-04-20`，检查 `Avg Deep minutes` / `Avg HRV` 非 0；04-17 短睡那周的 Sleep Debt L1 应 tripped。

---

#### ~~A4. 定义 "Poor Sleep Day" 的新 derivation~~ ✅ Decided — Option P-d

采用 **Option P-d**：`duration < 6.5h OR (awake_min > 40 AND HRV < baseline × 0.9)`。已在 `report_gen.py:88-91` 实现。其余脚本 / skill 统一对齐此定义。

---

#### ~~A5. 迁移 `report_gen.py` 到新 sleep schema~~ ✅ Done (commit f4b943e)

新 schema 字段全部到位，Option P-d derivation 生效，Rule 3 + 连续 Poor 告警可正常触发。

---

### Wave 2 — P1 skill rubric alignment（本周）

---

#### B1. 修正 `weekly-review` skill 的 3 处评分规则

- **Priority**: 🟡 P1
- **Problem**: D3/D4/D5 — Health + Habits 各有 2 行评分项依赖已删字段
- **Approach**:
  - L67 → `| Poor Sleep days derivation (per A4): 0=10 pts, 1=7, 2=4, 3+=1 | Up to 10 pts |`
  - L69 → `| COROS sleep structure (deep_min 60-150, avg_hr stable), HRV relative to baseline (>0.9×) | Up to 3 pts |`
  - L88 → `| 睡眠时长一致性 (stddev of sleep.duration across 7 days < 45min) | Up to 2 pts |`
- **Files**: `.claude/skills/weekly-review/SKILL.md:67, 69, 88` (3 处行替换)
- **Effort**: S (~10min)
- **Depends**: A4
- **Verify**: 下次跑周报 skill，评分自洽，没有 "undefined field" 提示

---

#### B2. 清理 `daily-report` skill 的抽取规则

- **Priority**: 🟡 P1
- **Problem**: D6 — L29-31 让 AI 尝试从 brain dump 抽 quality/bedtime/wakeup
- **Approach**: 删掉 L29 (quality) + L31 (bedtime/wakeup)；保留 L30 (duration)；补一行 `sleep` 其余字段: 来自 `make sync-coros` 自动填充，Brain Dump 中无需关心（让 AI 不要尝试编造）
- **Files**: `.claude/skills/daily-report/SKILL.md:29-31` (-2 行 +1 行)
- **Effort**: S (~5min)
- **Depends**: none
- **Verify**: 下次跑 daily-report，输出的 YAML 不再出现 quality/bedtime/wakeup

---

#### B3. `thresholds.yaml` 清理 + 补齐

- **Priority**: 🟡 P1
- **Problem**: D7 + B1 后续
- **Approach**:
  1. 删 L16-20 的 5 个旧键
  2. 加新键（给 weekly-review 和未来 logic engine 使用）：
     ```yaml
     sleep:
       ...
       deep_min_range: [60, 150]      # 7-9h 睡眠下 16-30% 深睡的换算
       rem_min_range: [50, 140]       # 同上 REM
       awake_min_warning: 40          # 本周 04-21 即 70min，20min 太严
       nap_compensation_min: 45       # 白天 nap 达此值可部分抵消 debt
     readiness:
       hrv_rel_baseline_min: 0.85     # HRV < 0.85 × baseline 判为低恢复
       load_ratio_overtraining: 1.5   # ATI/CTI > 1.5 过训预警
       tired_rate_warning: -30        # tired_rate < -30 预警
     ```
  3. 新增一个熔断器 (见 C2)
- **Files**: `config/thresholds.yaml:15-20, +new block after L21` (-5 行 +12 行)
- **Effort**: S (~10min)
- **Depends**: user confirms阈值数字
- **Verify**: `python3 -c "import yaml; yaml.safe_load(open('config/thresholds.yaml'))"` 不报错

---

#### B4. 让 `weekly_synthesis.py` 聚合新 COROS 块

- **Priority**: 🟡 P1
- **Problem**: §3.3 dead data
- **Approach**: 在现有聚合循环中新增：
  ```python
  readiness = meta.get("readiness") or {}
  hrv_values.append(safe_float(readiness.get("hrv")))
  tired_rates.append(safe_float(readiness.get("tired_rate")))
  load_ratios.append(safe_float(readiness.get("load_ratio")))

  training = meta.get("training") or {}
  weekly_total_load += safe_float(training.get("today_load"))

  activities = meta.get("activities") or []
  training_sessions += len(activities)  # 自动统计本周训练次数
  ```
  prompt 输出段新增 "本周训练次数 {training_sessions}、总训练负荷 {weekly_total_load}、平均 tired_rate、平均 load_ratio"。
- **Files**: `scripts/weekly_synthesis.py` (+40 行 在现有循环内)
- **Effort**: M (~45min)
- **Depends**: A3
- **Verify**: W17 跑一次，输出的 `weekly_report_prompt.md` 含训练次数字段且非 0

---

### Wave 2.5 — Architecture Hardening（防止下一次 drift）

> **动机**：Wave 1 的 drift 之所以发生，根因是两个聚合脚本独立各写一遍解析/评估逻辑，且无任何自动化校验（见 §3.5）。以下 4 项是"结构性保险"，不做系统也能跑，但下一次 schema 改动仍会重演人工同步地狱。

---

#### D1. 抽出 `scripts/lib/` 完整 library layer（pydantic 化）🟡 **P1（最高 ROI，升级版）**

- **Priority**: 🟡 P1
- **Problem**: §3.5 所列 5 类重复逻辑散落在两脚本；更深层问题是**无 schema 类型边界** —— frontmatter 以裸 dict 流通，`meta.get("sleep", {}).get("duration")` 这种链式 None 处理随处可见，拼写错误只有运行时才能发现
- **Approach**: 建立架构 doc §9 所述的 Library Layer，引入 **pydantic** 作为 schema 硬边界（用户已明确接受 pydantic 作为新依赖，见 §7 修订）：

  ```
  scripts/lib/
  ├── __init__.py
  ├── schema.py      # pydantic: DailyLog, Sleep, Readiness, Training, Activity, Body, DailySpend, Thresholds, Breaker
  ├── daily_log.py   # load(path) → DailyLog, iter_week(monday) → Iterator, save(log), derive_poor_sleep(log)
  ├── metrics.py     # rolling_7d_debt, avg_hrv, consecutive_poor, weekly_aggregates
  ├── breakers.py    # evaluate(metrics, cfg) → list[TrippedBreaker]（唯一 breaker 入口）
  └── config.py      # load_thresholds() → Thresholds；启动期 fail-fast
  ```

  两个脚本全面重写为 lib consumer：
  - `report_gen.py`：约 50 行，纯 glue（load config → iter logs → evaluate → print alerts）
  - `weekly_synthesis.py`：约 80 行，纯 glue（load config → aggregate week → format prompt）
- **Key pydantic models**：
  ```python
  class Sleep(BaseModel):
      duration: float | None = None
      deep_min: int | None = None
      light_min: int | None = None
      rem_min: int | None = None
      awake_min: int | None = None
      nap_min: int | None = None
      avg_hr: int | None = None
      min_hr: int | None = None
      max_hr: int | None = None

  class Readiness(BaseModel):
      hrv: float | None = None
      hrv_baseline: float | None = None
      rhr: int | None = None
      tired_rate: float | None = None
      ati: float | None = None
      cti: float | None = None
      load_ratio: float | None = None
      stamina_level: int | None = None
      performance: int | None = None

  class DailyLog(BaseModel):
      date: date
      energy_level: int | None = None
      deep_work_hours: float | None = None
      sleep: Sleep = Field(default_factory=Sleep)
      readiness: Readiness = Field(default_factory=Readiness)
      # ... 其余字段
      model_config = ConfigDict(extra='forbid')  # 未知字段 fail-fast
  ```
- **Files**: 新增 `scripts/lib/*` (~250-300 行 含 pydantic models)；`scripts/report_gen.py` 重写 -100 行；`scripts/weekly_synthesis.py` 重写 -150 行
- **Effort**: L (~3h — 比原 45min 估计大幅上调，因引入 pydantic schema 化)
- **Depends**: A3 可合并做（**推荐合并**）；`.venv` 需 `pip install pydantic`（新增唯一运行时依赖）
- **Verify**:
  - `python3 -m py_compile scripts/lib/*.py`
  - 对 Personal-OS 数据 submodule 现有所有日志跑 `load()` 应全部通过 pydantic 校验（老日志有旧字段的需要先跑 D6 migrate）
  - `make check && make weekly` 输出与 pre-refactor baseline 一致（事前 snapshot）
  - 故意 typo 一个 field（`energ_level: 7`）→ pydantic `ValidationError` 立即报错

---

#### D2. `scripts/lint_daily.py` + `make lint` — schema 校验 🟡 P1

- **Priority**: 🟡 P1
- **Problem**: 模板里新增/删除字段后，没有机制检测 `data/daily/*.md` frontmatter 与 `templates/daily.md` 对不上的情况。Wave 1 drift 全靠用户肉眼发现。
- **Approach**:
  1. 写 `scripts/lint_daily.py`：读 `templates/daily.md` frontmatter 作为 schema，对 `data/daily/*.md` 每个文件做字段集 & 类型校验（允许 None，但不允许出现模板外的未知顶级 key）
  2. `Makefile` 加 `lint` target；`make report` 改为 `lint check weekly`，让 drift 在 `make report` 时就抛出 warning
  3. 初版**不用 pydantic**，PyYAML + 手写字段白名单即可（避免新增依赖）
- **Files**: 新增 `scripts/lint_daily.py` (~60 行)；`Makefile` +5 行
- **Effort**: M (~45min)
- **Depends**: D1（能复用 `parse_frontmatter`）
- **Verify**: 故意改一个日志加 `bogus_field: 1`，`make lint` 应 `[ERROR] data/daily/2026-04-22.md: unexpected top-level key "bogus_field"`，exit code != 0

---

#### D3. E2E smoke test — `tests/test_smoke.py` 🟢 P2

- **Priority**: 🟢 P2（可选但推荐）
- **Problem**: 目前改代码的唯一 regression 检测方式是用户手动跑 `make report` 看输出。任何 silent 数据丢失（例如 A3 不做时"Avg Deep% 0%"）都不会报错。
- **Approach**: 用 `tests/fixtures/daily/` 放 3-5 份典型日志（1 份 Poor sleep, 1 份高 load_ratio, 1 份 caffeine 违规），`tests/test_smoke.py` 断言：
  - `run_checks(fixtures_dir)` 不崩
  - Sleep Debt L1 breaker 按预期 trip/不 trip
  - Poor Sleep derivation 对短睡日返回 True
  - `generate_weekly_synthesis` 产出的 prompt 含 "Avg HRV" 字段且值 > 0
- **Files**: 新增 `tests/test_smoke.py` + `tests/fixtures/daily/*.md` (~100 行)
- **Effort**: S-M (~30min)
- **Depends**: D1 强烈推荐（测 lib 层比测脚本入口更稳）
- **Verify**: `python3 -m pytest tests/` 全绿；故意把 `derive_poor_sleep` 改坏，至少 1 个 case 红
- **Scope note**: 不引入 pytest-as-dep（不写 `requirements.txt`），直接 `python3 -m unittest` 也行；测试本身是 personal 项目，用最轻量的就好

---

#### D4. Scoring base 计算迁到 `lib/score.py`（deterministic scoring）🟡 **P1（升级版，原 P3）**

- **Priority**: 🟡 P1（从原 P3 promoted —— 用户决定成本不限时做）
- **Problem**:
  - `weekly-review/SKILL.md:52-96` 的 4 维 rubric 是 markdown 表格，每周 AI 手算。**不可复现**（同一周重跑分数可能漂移）、**不可回放**（想用新 rubric 对 W13 重算需要让 AI 再跑一遍）、**不可测试**（无 ground truth）
  - AI 手算 "deep work 17.3 / 30 × 25 = 14.4 pts" 这种确定性公式是资源浪费 + 误差源
- **Approach**:
  1. `config/thresholds.yaml` 扩展 `scoring:` 块 —— 将 SKILL.md 里的所有"确定性部分"（`actual/target × max`、threshold lookup、proportional 映射）翻译为 YAML 可配置公式：
     ```yaml
     scoring:
       output:
         deep_work:
           target_hours: 30
           max_points: 25
           formula: proportional  # actual / target * max_points, capped
       health:
         energy:
           target: 7
           max_points: 8
           formula: proportional
         sleep_debt:
           thresholds: [[3, 7], [5, 5], [10, 3]]  # (debt < X) → Y pts，小于即中
           max_points: 7
         poor_sleep_days:
           thresholds: [[0, 10], [1, 7], [2, 4]]  # count ≤ X → Y pts
           else_points: 1                          # 其余 (3+ days) = 1 pt
           max_points: 10
       # ... mental, habits 同理
     ```
  2. `scripts/lib/score.py::compute_base_score(metrics, rubric) -> ScoreBreakdown`，输出 4 维 base score + per-criterion 明细
  3. `weekly_synthesis.py` 在产出 `weekly_report_prompt.md` 时附带 "Base Score (deterministic): Output 24.3 / Health 22.5 / Mental 14 / Habits 8.5 = 69.3"
  4. `weekly-review/SKILL.md` 大幅精简：删除评分表格；职责改为"读 base score + 做 qualitative bonus/penalty + narrative + WoW 对比 + P0/P1/P2 目标"
- **Files**:
  - `config/thresholds.yaml` +30 行（`scoring:` 扩展）
  - `scripts/lib/score.py` +150 行（新增）
  - `scripts/weekly_synthesis.py` +20 行（append base score 到 prompt）
  - `.claude/skills/weekly-review/SKILL.md` -40 行（删评分表）+10 行（新 qualitative 流程）
- **Effort**: L (~3h)
- **Depends**: D1（pydantic ScoreBreakdown 和 Rubric 模型）；A3/B4 完成后 metrics 稳定
- **Verify**:
  - 对 W13-W16 历史日志 backfill 跑 `compute_base_score`，输出与存档周报 AI 评分相差 ≤ 3 分（若超过 5 分，说明 rubric 翻译有偏差，需迭代）
  - 写 `tests/test_score.py` 覆盖每个 criterion 的 edge case（deep_work = 0 / target / 2×target / None）
- **Architectural unlock**: Score 从"每次 AI run 不同的模糊值"变成"git-trackable 的确定性值"。周报历史可回放，rubric 变更可 A/B 比较，bonus/penalty 讨论回到 qualitative 本位

---

#### D5. Observability — `lib/logger.py` + `data/logs/*.jsonl` 🟢 P2

- **Priority**: 🟢 P2
- **Problem**: `make check` / `make weekly` 输出仅 stdout，终端一关即失。调 breaker false positive、回溯"为什么上周 HRV Alert 触发"完全没有历史据点
- **Approach**:
  1. `scripts/lib/logger.py`：`emit_event(event_type: str, payload: dict)` → append 一行 JSON 到 `data/logs/engine-YYYY-MM-DD.jsonl`
  2. `report_gen.py` / `weekly_synthesis.py` 在关键点 emit：
     ```python
     emit_event("check_run", {"days_scanned": 7, "alerts": [...], "tripped_breakers": ["HRV Recovery Alert"], "latest_metrics": {...}})
     emit_event("weekly_synthesis", {"week_id": "2026-W17", "days_logged": 6, "base_score": {...}, "tripped": [...]})
     ```
  3. `data/logs/` 加到 `.gitignore` 或 data submodule（不 polluting 主 repo）
  4. 可选：`scripts/inspect_logs.py` CLI 查询工具（`python3 scripts/inspect_logs.py --breaker "HRV Recovery Alert" --last 30d`）
- **Files**: 新增 `scripts/lib/logger.py` (~40 行)；两个脚本各 +5 行 emit 调用；`.gitignore` +1 行
- **Effort**: S-M (~45min)
- **Depends**: D1
- **Verify**: 连续跑 3 天 `make check` 后，`cat data/logs/engine-*.jsonl | jq` 能看到三条结构化 event

---

#### D6. `lib/migrate.py` — schema 迁移基础设施 🟡 P1

- **Priority**: 🟡 P1（D1 的前置 —— 引入 pydantic `extra='forbid'` 会让老日志 validation 失败，必须有迁移路径）
- **Problem**: pydantic 严格 schema + 老日志（可能含已删字段如 `sleep.quality`）不兼容。若不写 migrate，D1 首次跑就 fail-fast 不能读任何老日志
- **Approach**:
  1. `scripts/lib/migrate.py` 定义 Migration 接口 + 有序 migration list：
     ```python
     @dataclass
     class Migration:
         id: str                                    # "2026-04-drop-sleep-quality"
         applies_to: Callable[[dict], bool]         # 判定 frontmatter 是否需迁移
         transform: Callable[[dict], dict]          # 就地转换
     ```
  2. 初版包含这些 migration：
     - `drop-deprecated-sleep-fields`：删除老 `sleep.quality` / `sleep.bedtime` / `sleep.wakeup` / `sleep.interruptions` / `sleep.deep_pct` / `sleep.rem_pct` / `sleep.light_pct` / `sleep.hrv`
     - `derive-poor-flag`（可选）：给每个老日志预计算 `sleep.is_poor` 字段（Option P-d 结果）以加速 breaker 评估
  3. `Makefile` 新增 `migrate` target：`.venv/bin/python3 scripts/lib/migrate.py --apply`（默认 dry-run，`--apply` 才真写）
  4. 成功迁移后 commit 一次 `data/` submodule（"chore(data): migrate pre-W17 daily logs to new schema"）
- **Files**: 新增 `scripts/lib/migrate.py` (~80 行)；`Makefile` +5 行
- **Effort**: M (~1h — 包含在数据 submodule 上 dry-run + review + apply 的时间)
- **Depends**: D1 schema 模型已定（但 migrate 可在 D1 完成 schema 后、两脚本切换前运行）
- **Verify**:
  - Dry-run 输出应显示"N 个 daily log 需迁移"，apply 后重跑 `lib.daily_log.load()` 对所有日志成功
  - 随机抽 3 份老日志，`git diff` 确认只删了 deprecated 字段，未改其他
- **Risk**: 对 `data/` submodule 的批量改动。建议操作前 `git -C data log --oneline | head -5` 备份 HEAD；`migrate --apply` 在单独分支跑，人 review 后再 merge

---

### Wave 3 — P2 cleanup & polish（有空再搞）

---

#### C1. 删除 `prompts/` 死引用

- **Priority**: 🟢 P2
- **Problem**: B3 — `weekly_synthesis.py:244-250` 读取不存在的 prompts 文件
- **Approach**: 删掉这 7 行；`prompt_context` 直接以数据段开头即可（skill 自己有完整 system prompt）
- **Files**: `scripts/weekly_synthesis.py:244-250, 259` (-7 行)
- **Effort**: S (~5min)
- **Depends**: none
- **Verify**: weekly synthesis 照常产出，prompt 文件不含 "你现在是系统配置的..." stub 行

---

#### C2. 新增 Overtraining 熔断器（利用 load_ratio）

- **Priority**: 🟢 P2（功能增强，不是修复）
- **Proposal**:
  ```yaml
  - name: "Overtraining Warning"
    description: "ATI/CTI 过训比值警示"
    condition:
      metric: load_ratio
      operator: ">"
      value: 1.5
    actions:
      - "当日禁止安排额外训练，改为主动恢复"
      - "训练降重 30% 至 ratio < 1.3"
      - "强制 8h 睡眠机会窗口"
  ```
- **Files**: `config/thresholds.yaml` (+10 行)；`report_gen.py`/`weekly_synthesis.py` 填充 `latest_metrics["load_ratio"]`（B4 已做）
- **Effort**: S (~10min)
- **Depends**: B4
- **Verify**: 伪造一条 `readiness.load_ratio: 1.6` 的日志，`make check` 应触发此熔断器

---

#### ~~C3. `sync_scale.py` 归档 + `Makefile` 的 `sync-scale` target 处理~~ ✅ Done

脚本已删除（未保留 archive 版本），Makefile 的 `sync-scale` target 已移除。`make help` 不再出现此 target。

---

#### C4. 加 `make daily DATE=YYYY-MM-DD` target

- **Priority**: 🟢 P2
- **Problem**: 补写历史日期目前要 `cp template`
- **Approach**: Makefile 里加
  ```make
  daily:
      @if [ -z "$(DATE)" ]; then echo "用法: make daily DATE=YYYY-MM-DD"; exit 1; fi
      @sed "s/{{DATE}}/$(DATE)/g" $(TEMPLATES_DIR)/daily.md > $(DAILY_DIR)/$(DATE).md
      @echo "[Status: OK] Created $(DAILY_DIR)/$(DATE).md"
  ```
- **Files**: `Makefile` (+7 行)
- **Effort**: S (~5min)
- **Verify**: `make daily DATE=2026-04-22` 生成文件

---

#### C5. 统一 PROMPTS_DIR / REPORTS_DIR 路径常量

- **Priority**: 🟢 P2（code hygiene）
- **Problem**: `weekly_synthesis.py:15` 定义 `REPORTS_DIR` 但从未使用（脚本输出到根目录的 `weekly_report_prompt.md` 而不是 `data/reports/`）
- **Approach**: 删掉未用的 PROMPTS_DIR + REPORTS_DIR，或真正用起来（weekly-review skill 已经把 final report 写到 `data/reports/YYYY-w##-weekly-report.md`，那脚本这个变量就是历史遗留，建议删）
- **Files**: `scripts/weekly_synthesis.py:15-16` (-2 行)
- **Effort**: S (~2min)

---

#### C6. `coach-planner-workspace/` eval artifact 归档

- **Priority**: 🟢 P2
- **Problem**: 目录里有 `iteration-1/eval-*/without_skill/outputs/response.md` 之类的迭代产物，不影响运行但占目录
- **Approach**: 询问用户 —— 是否还需要 eval artifacts？不需要则整目录归档至 `.claude/skills/archive/` 或删除
- **Effort**: S
- **Depends**: user 确认

---

### Wave 4 — Planned-vs-Actual Feedback Loop（闭环测量）🟠 大改动

> **动机**：现系统有 measure → diagnose → plan 三段，但**缺 plan → measure 闭环**。coach-planner 排了周一 09:00-12:00 DW Project X，周一晚 /daily-report 记 `deep_work_hours: 6`，但无结构化字段记录 "6h 里多少是 Project X"。周报 AI 只能靠叙事推断"好像按计划走了 70%"，完全凭感觉。Wave 4 把"计划执行率"变成硬指标。

---

#### E1. daily.md schema 新增 `planned_schedule` + `actuals` 块 🟠 P2

- **Priority**: 🟠 P2（基础设施）
- **Problem**: 当前 daily.md 无计划字段，coach-planner 的输出或落在 `data/reports/*-timetable.md` 单独文件，或追加到 daily.md 正文"今日计划"section —— 两种都是非结构化，无法让下游聚合
- **Approach**:
  1. `templates/daily.md` frontmatter 新增两块：
     ```yaml
     planned_schedule:                 # coach-planner 生成排期时写入 (block 级)
       - time: "09:00-12:00"
         type: deep_work                # deep_work / training / meeting / break / meal / other
         target: "Personal-OS Wave 2"
         planned_hours: 3.0
       - time: "19:00-20:00"
         type: training
         target: "上肢哑铃"
         planned_hours: 1.0
     actuals: []                       # /daily-report 填；每条 block 一条 actual
       # - block_ref: 0                 # 对应 planned_schedule[0] 的 index
       #   actual_hours: 2.5
       #   completed: partial           # done / partial / missed / replaced
       #   notes: "被 30min 临时会议打断"
     ```
  2. `scripts/lib/schema.py` 相应 pydantic 模型：`PlannedBlock`, `Actual`, `DailyLog.planned_schedule`, `DailyLog.actuals`
  3. `scripts/lib/migrate.py` 加 migration：老日志这两字段默认 `[]`
- **Files**: `templates/daily.md` (+20 行)；`scripts/lib/schema.py` (+30 行)；`scripts/lib/migrate.py` (+10 行)
- **Effort**: S-M (~45min)
- **Depends**: D1, D6
- **Verify**: 老日志 load 后这两字段自动为 `[]`；新日志能保存结构化排期

---

#### E2. `/coach-planner` 输出写入 `planned_schedule` 🟠 P2

- **Priority**: 🟠 P2
- **Problem**: 当前 coach-planner skill 输出 markdown 时间表，非结构化
- **Approach**:
  1. 修改 `.claude/skills/coach-planner/SKILL.md`：排期输出模式改为"既写 markdown 给人看，又更新目标日 daily.md 的 `planned_schedule` frontmatter"
  2. 新增 helper：`scripts/apply_schedule.py`（或集成进 coach-planner 的 shell step）—— 接收 JSON 排期，更新指定 `data/daily/YYYY-MM-DD.md` 的 `planned_schedule` 块
  3. 当排期涉及多天（如"下周时间表"），逐日更新；若目标日 daily.md 不存在，`make daily DATE=...` 先创建
- **Files**: `.claude/skills/coach-planner/SKILL.md` +30 行；`scripts/apply_schedule.py` +60 行
- **Effort**: M (~1.5h)
- **Depends**: E1, C4 (`make daily DATE=` target)
- **Verify**: 对 coach-planner 说"排明天时间表"，完成后 `cat data/daily/2026-04-24.md` 应见到 4-6 条结构化 `planned_schedule` entry

---

#### E3. `/daily-report` 对账 actuals 🟠 P2

- **Priority**: 🟠 P2
- **Problem**: Brain Dump 里自然语言描述"上午做了 Personal-OS 2h 然后被 meeting 打断去搞 Project Y" —— 需要把这些对应到 planned block
- **Approach**:
  1. 修改 `.claude/skills/daily-report/SKILL.md`：生成日志时**先读现有 `planned_schedule`**，然后从 Brain Dump 抽取每个 block 的实际完成情况，填 `actuals[]`
  2. 对"计划外"活动（planned 里没但实际做了）：追加 `actuals` 条目 `block_ref: null, type: "unplanned", ...`
  3. "完全跳过" 的 block：填 `completed: missed` 且 `actual_hours: 0`，`notes` 记原因
- **Files**: `.claude/skills/daily-report/SKILL.md` +40 行
- **Effort**: M (~1h 迭代 prompt)
- **Depends**: E1, E2
- **Verify**: Brain Dump 里写"计划 3h DW 只做了 1.5h 因为 meeting"，输出的 daily.md 应有 `actuals[0].actual_hours: 1.5, completed: partial`

---

#### E4. `lib/metrics.py` 新增 adherence 聚合 + weekly-review 纳入评分 🟠 P2

- **Priority**: 🟠 P2
- **Problem**: 有了 `planned_schedule` + `actuals` 后需把"执行率"变成周度 metric
- **Approach**:
  1. `scripts/lib/metrics.py::compute_adherence(logs) -> AdherenceReport`：
     ```python
     class AdherenceReport(BaseModel):
         total_planned_blocks: int
         done: int
         partial: int
         missed: int
         replaced: int
         planned_hours: float
         actual_hours: float
         adherence_pct: float          # done + 0.5 × partial / total
         hours_pct: float              # actual / planned
         breakdown_by_type: dict[str, float]  # 按 type 分组 (deep_work/training/...)
     ```
  2. `weekly_synthesis.py` 把 AdherenceReport 写入 `weekly_report_prompt.md`
  3. `weekly-review/SKILL.md` 评分新增"执行率"维度 **或**把 adherence 作为现有 Habits 分的子项（建议后者，避免分数膨胀）
  4. coach-planner 读上周 AdherenceReport 作为排期依据（"上周 DW adherence 45%，下周目标压缩为 4 blocks × 2h 而非 6 blocks × 2h"）
- **Files**: `scripts/lib/metrics.py` +80 行；`scripts/weekly_synthesis.py` +15 行；`.claude/skills/weekly-review/SKILL.md` +10 行；`.claude/skills/coach-planner/SKILL.md` +10 行
- **Effort**: M (~1.5h)
- **Depends**: E3 落地 2+ 周产生数据后才有意义
- **Verify**: 对 W18 末跑周报，应能看到"本周执行率 68%（DW 55% / Training 90% / Meal 100%）"这种硬数字

---

**Wave 4 总成本**：~5h + **2-4 周试用观察期**。建议：
- 在 Wave 2.5 全部落地稳定 1 周后启动
- E1 + E2 先做（基础设施 + 写入路径），跑 1 周让用户观察 coach-planner 输出是否还顺手
- E3 + E4 在 E2 数据沉淀后做
- **回滚计划**：任何阶段发现 AI 对账质量差或用户抗拒，回滚到 Wave 2.5 终态（schema 字段保留默认 `[]`，不 break 已有流程）

---

## 5. Recommended Sequencing

### ~~Wave 1~~ ✅ Mostly Done (commit f4b943e)

A1 / A2 / A4 / A5 已完成。剩余 **A3**（`weekly_synthesis.py` 迁移 + breaker fill 对齐），建议与 Wave 2.5 D1 合并做，见下。

### Wave 2 + 2.5 合并 session — **推荐作为下次 coding block（~6-7h，可拆 2 session）**

**目标**：一次性把所有 schema drift 清完，把"不再 drift"的结构保险做上，并把 scoring 确定性化。

> ⚠️ 成本升级提示：采纳"成本不限"版本后，D1 从"抽共享函数"升级为"pydantic-backed library layer"；D4 从"P3 defer"升级为"P1 deterministic scoring"；新增 D5（logger）、D6（migrate）。总成本从原 ~3h 翻到 ~6-7h。建议拆 **Session A**（~3.5h）+ **Session B**（~3h）。

---

#### Session A — Schema + Library 层落地（~3.5h）

1. **D6.a** — 写 `scripts/lib/migrate.py` 框架 + drop-deprecated-sleep-fields migration，dry-run 对 `data/` 跑一遍，review diff（30min）
2. **D1.a** — `scripts/lib/schema.py` 所有 pydantic models（含 Thresholds、Breaker、DailyLog 全套）（1h）
3. **D1.b** — `scripts/lib/{daily_log, metrics, breakers, config}.py` 实现（1.5h）
4. **D6.b** — `migrate.py --apply` 对 data submodule 跑真写；commit 到 data submodule（10min）
5. **A3 + B2 breaker fill** — 用新 lib 重写 `weekly_synthesis.py`（15min，因为 lib 已就绪）；同步重写 `report_gen.py` 使用新 lib（15min）
6. **B3** — `thresholds.yaml` 清理旧字段 + 加 `readiness` 块（10min）
7. **回归**：`make check && make weekly DATE=2026-04-20`，对比 pre-refactor snapshot（10min）

**Session A commit 粒度**：
- `chore(lib): add pydantic schema module (D1.a)`
- `feat(lib): add daily_log/metrics/breakers/config modules (D1.b)`
- `chore(data): migrate pre-W17 daily logs to new schema (D6)` — 在 data submodule 内
- `refactor: rewrite report_gen.py + weekly_synthesis.py using lib (A3 + D1)`
- `chore(config): remove deprecated sleep schema, add readiness block (B3)`

---

#### Session B — Skills + Scoring + Observability（~3h）

8. **B1** — `weekly-review/SKILL.md` 三处评分字段更新（过渡版本，保留手算 rubric）（10min）
9. **B2** — `daily-report/SKILL.md` 删 quality/bedtime/wakeup（5min）
10. **B4** — `weekly_synthesis.py` 聚合 readiness/training/activities（已在 lib/metrics.py 里的话，只需 glue）（15min）
11. **D4** — `lib/score.py` + `thresholds.yaml` scoring 块扩展 + weekly_synthesis 写 base score 到 prompt + weekly-review/SKILL.md 大改为 qualitative-only（2h）
12. **D5** — `lib/logger.py` + 两脚本 emit hooks + `.gitignore`（45min）
13. **D2** — `scripts/lint_daily.py`（复用 lib.schema）+ `make lint` + `make report` 挂载（30min）
14. **D3** — `tests/test_{smoke,score,breakers,migrate}.py`（45min — 覆盖更多因为有了 lib + score）

**Session B commit 粒度**：
- `docs(skills): drop deprecated brain-dump extraction rules (B2)`
- `feat(weekly): aggregate readiness/training/activities (B4)`
- `feat(lib): add deterministic score computation (D4)`
- `refactor(skills): weekly-review uses pre-computed base score (D4)`
- `feat(lib): add JSON lines logger + emit hooks (D5)`
- `feat(lint): add scripts/lint_daily.py + make lint target (D2)`
- `test: add E2E/unit tests for lib layer (D3)`

**为什么这个顺序**：
- D6 在 D1 之前跑一次 dry-run，确保迁移方案可行（避免 pydantic fail-fast 时再返工）
- D1 先定 schema 再写 lib 模块，pydantic 模型是所有模块的基础
- A3 + breaker fill 利用 lib 重写，自然把 Wave 1 残余做掉
- D4 依赖 lib + A3/B4 后的稳定 metrics，放 Session B 中段
- D5 / D2 / D3 放最后做"护栏"，能对前面所有改动做回归

---

### Wave 3 (W18 或之后 — **P2 cleanup**)

**目标**：清理 dead surface、加 QoL 功能。

**顺序**：C1 prompts 死引用删除 → C2 新熔断器 → ~~C3~~ → C4 make daily → C5 常量清理 → C6 eval artifacts

**估时**：合计 ~45min（C3 已完成）

**时机**：Wave 2.5 落地后，单独抽一个 coding 时段。C2 需 B3/B4 完成（`load_ratio` 已进聚合）后才能生效。

---

### Wave 4 (W19 或之后 — **Planned-vs-Actual 闭环**)

**目标**：建立 measure → diagnose → plan → measure 的完整闭环。

**顺序**：E1 schema 扩展 → E2 coach-planner 写入 → （运行 1-2 周积累数据）→ E3 daily-report 对账 → （再 1-2 周）→ E4 weekly-review 纳入 adherence

**估时**：~5h 工程 + 2-4 周观察期

**时机**：
- **前置**：Wave 2.5 全部完成且稳定 1 周（避免在不稳定基础上再加功能）
- **触发条件**：用户对"周报执行率评估靠 AI 瞎猜"产生明显不满时启动；若觉得当前叙事性对账够用，Wave 4 可无限期推迟

---

## 6. Risks & Open Questions

**~~Q1. "Poor Sleep Day" derivation~~** ✅ Resolved — 采用 Option P-d（commit f4b943e 已落地）

**~~Q2. `total_sleep_debt` 语义冲突~~** ✅ Resolved by A3 设计
- **display 用本周累计**（周报 UI 里显示"Sleep Debt 12.3h"给用户看）
- **breaker fill 用 rolling 7d**（从今天往回 7 天，与熔断器 threshold 对齐）
- A3 步骤 4-5 已明确此双变量设计，`weekly_synthesis.py` 中两者并存、分别计算

**Q3. HRV threshold 要用绝对值 30 还是相对 baseline？** — 仍待决策
- 现在 `hrv_warning_low: 30` 是绝对阈值，适合"机器警告"
- 但用户 baseline 54 → HRV 45 (−17%) 就已经值得注意，远早于到 30
- **建议**：保留绝对 30 作为"红线"（触发 HRV Recovery Alert 强制恢复日），另加一个 `hrv_rel_baseline_warning: 0.85` 作为黄线（仅 log warning，不触发 breaker）
- 决策归入 B3（`thresholds.yaml` 扩展）

**Q4. `awake_min_max: 20` 太严格？** — 仍待决策
- 用户 04-21 即录得 70min，但那晚 7.65h 睡眠且 HRV 50 并不算差
- **建议**：调到 40（B3 提议值）。用户确认即可

**Q5. `make check` 语义** — 可后置
- A1/A2 已修好，脚本能跑；但目前 weekly-review skill 只调 `weekly_synthesis.py`，没人真的每天看 `make check` 输出
- **建议**：维持现状，不追求"让每天的告警被看见"；若未来某天用户想要每日 nag，再加 `make today` 自动链 `make check`

**Q6. COROS 数据的"信任边界"** — 先做观察
- `readiness.tired_rate = -24` 算不算"身体反馈"？AI 在周报里说"本周疲劳指数均值 -22，偏疲劳" 会不会被当黑盒数字？
- **建议**：B4 先把数字放进 prompt，**不强制**评分公式用它；观察两周后看周报解读质量，再决定是否进 scoring

**~~Q7. Wave 2.5 D1 (共享 lib) 的命名空间~~** ✅ Resolved — `scripts/lib/`
- 最终采用 `scripts/lib/<module>.py` + `scripts/lib/__init__.py`；两个脚本用 `from lib.xxx import yyy`（配合 `sys.path` 或包装 package）

**~~Q8. Wave 2.5 D4（scoring 进 config）做不做？~~** ✅ Resolved — 做，升级为 P1
- 用户成本不限决策。D4 已 promoted 为 P1，纳入 Session B 中段
- Rubric 进 `thresholds.yaml` 的 `scoring:` 块，AI 只做 qualitative 判断；见 §4 Wave 2.5 D4 全文

**Q9. D6 migrate 到底改不改 `data/` submodule 的 git 历史？** — 待拍板
- 纯 dry-run 不改；`--apply` 会对 `data/daily/*.md` 批量 rewrite frontmatter
- **建议**：单独分支 `migrate/drop-deprecated-sleep-fields` 跑，人 review diff 确认只删 deprecated key，再 merge
- 不做 git filter-branch / rebase，保留一次 "chore(data): migrate to new schema" commit 即可

**Q10. Wave 4 planned_schedule 的 `time` 字段格式** — 待拍板
- `"09:00-12:00"` 字符串 vs `start: "09:00", end: "12:00"` 两字段 vs ISO duration?
- **建议**：保留人类友好 `"09:00-12:00"` string；在 lib.schema 里 parse 成 `(time, time)` tuple 供聚合使用
- 不用 ISO duration / datetime —— 过度工程化

**Q11. D4 scoring backfill —— 历史周报要重算吗？**
- 做完 D4 后，对 W13-W16 历史 report 跑新 rubric 会产出不同分数
- **建议**：一次性在 `data/reports/` 旁边生成 `*-backfill-score.md`，记录新旧分数对比，不替换原 report
- 后续周报从 W18/W19 开始用新 deterministic 分数

---

## 7. Out of Scope（避免未来重提）

这些明确**不做**，记录下来防止下次会话里旧话重提：

1. **Zepp Life body 数据自动同步** —— 用户已选手填（memory: `feedback-body-data-manual`），不重启 `sync_scale.py` 自动化
2. **GitHub Actions / cron 自动拉取 COROS** —— 用户拒绝（23 Apr 对话），手动 `make sync-coros` 即可
3. **COROS API 官方 key 申请** —— 不值得；非官方 client 覆盖够用
4. **bedtime / wakeup 字段重新加回** —— COROS API 不暴露，硬加只会制造更多空字段。如果未来真需要，应从 activity 时间戳反推，不需要模板字段
5. **sleep.quality 字段回归** —— 用户明确换成了计算型 derivation，不重建 Good/Fair/Poor 三级分类
6. **Public dashboard / 数据可视化 web** —— Personal-OS 是本地工具，不做 hosted UI
7. **多人/团队化** —— 系统设计为 single-user，不做 multi-tenant
8. **`make today` 自动触发 `sync-coros`** —— 副作用风险（网络慢、API 改动），用户手动双步更安全
9. **LLM 直接改 daily.md frontmatter（绕过 daily-report skill）** —— 保持单一入口，避免字段漂移
10. **把 `patch_coros.py` 改为"读取时合并"架构（single source: data/fitness/*.yaml）** —— 评估过，优点是消除双写，但牺牲 daily.md 自包含（grep/人读价值下降）。当前 sync+patch 模型已经够用，不 refactor（此决策已纳入 `architecture.md §5` 作为显式 tradeoff）
11. ~~**pydantic / pytest 作为新依赖**~~ → **已接受 pydantic 作为 D1/D4/D6 必要依赖**；pytest 仍不用（D3 继续用 `unittest`）
12. ~~**scoring rubric 进 config（D4）**~~ → **已接受，D4 promoted 为 P1**
13. **SQLite / 任何 DB 做 source of truth** —— 破坏 "人类可读优先 + 手改 md 立即生效" 的核心体验；架构 doc §1 设计原则明确拒绝
14. **cron / launchd / GitHub Actions 自动化** —— 单用户本地系统的偏好选择，非能力限制
15. **事件驱动 pipeline**（如 /daily-report 完成自动触发 `make check`） —— 复杂度 tax 无收益，`make` 显式触发已足够
16. **schema versioning（`schema_version: 2` 字段）** —— schema 每年大改 1 次，D6 一次性 migration 模式足够；不做 schema 版本号
17. **把 `coach-planner` 排期写入 `data/reports/timetable.md` 的格式保留** —— Wave 4 E2 改为写入 daily.md frontmatter 结构化字段；老 timetable.md 可留作 human-readable 补充，但聚合以 frontmatter 为准

---

## 8. Meta Notes

- 本 plan.md 会随实施进度被**更新**（完成项 strike-through + 加 ✅ 标记）而不是删除，作为系统健康度的书面记录
- **已入档**：Wave 1 A1/A2/A4/A5（commit f4b943e）、C3 sync_scale 归档、plan v2 修订（2026-04-23）
- **已关联**：本 plan 的 Wave 2.5 D1/D4/D5/D6 均在 `architecture.md §9 Library Layer` 有对应章节；Wave 4 在 `architecture.md §9` 的"与 Agent Layer 分工"段提及。plan 与 architecture 共同演进，不分离维护
- 用户确认本次修订后，按 §5 新 sequencing 执行：**Session A**（~3.5h，schema + library）+ **Session B**（~3h，skills + scoring + observability）；Wave 3 / Wave 4 另开 session。总工程量 ~10h + Wave 4 观察期 2-4 周
- Commit 粒度见 §5（Session A 5 个 commit + Session B 7 个 commit）；遵循 `feedback-split-commits` 偏好
- Pre-commit check 演进路径：
  - **当前**：`python3 -m py_compile scripts/*.py`
  - **Session A 后**：`python3 -m py_compile scripts/*.py scripts/lib/*.py && python3 -c "from lib.daily_log import load; [load(p) for p in Path('data/daily').glob('*.md')]"`（pydantic fail-fast 会在这步暴露迁移遗漏）
  - **Session B 后**：`make lint && python3 -m unittest discover tests/`
- 完整回归（Session A 后）：`make check && make weekly DATE=2026-04-20`，对比 pre-refactor snapshot 的 `Avg Deep minutes / Avg HRV / Avg tired_rate` / tripped breakers 一致
- **Risk register**（v2 新增）：
  - **R1** pydantic 严格 schema 可能暴露 data submodule 中"以前能 load 但不符合新 model"的老日志 → D6 migrate dry-run 会先列出，apply 前人审
  - **R2** D4 scoring 公式与 AI 手算分数出现 > 5 分偏差 → 跑 W13-W16 backfill 对比（见 Q11），若偏差大则迭代公式，不阻断 Session B 其他项
  - **R3** Wave 4 E3 对账质量取决于 Brain Dump 的自然语言质量；若用户描述过简导致 actuals 缺失多 → 回滚 E3，保留 E1/E2 结构化排期（coach-planner 受益），仅牺牲 adherence 自动化
  - **R4** 引入 lib 后 import path 问题（`from lib.xxx` vs `from scripts.lib.xxx`）→ Session A 开始时先定好 `sys.path` 注入方式，所有脚本统一
