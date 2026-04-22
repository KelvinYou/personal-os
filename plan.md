# Personal-OS Architecture Optimization Plan

> Generated: 2026-04-22 | Scope: post-COROS-integration architecture review
> Author: Claude (architecture scan + synthesis)
> Status: **Proposal — awaiting user sign-off before implementation**

---

## 1. Executive Summary

系统刚经历 COROS 集成（新增 `sleep/readiness/training/activities` 四块 frontmatter + `sync_coros.py`/`patch_coros.py`），但 downstream 的 **logic engine、weekly aggregator、scoring skill、daily-report extraction rules 全部还在引用旧 schema**。更严重的是，审查过程中发现**两处 pre-existing 的静默 bug**（不是这次引入的）：

1. **`sleep.critical_debt_hours` 键在 `config/thresholds.yaml` 不存在** —— `scripts/report_gen.py:47` 会 `KeyError` 崩溃，`make check` **根本跑不通**。用户可能没注意是因为这个 target 很少直接跑（通常走 `make report` 时才触发）。
2. **熔断器 metric 名字对不上** —— `thresholds.yaml` 定义 `rolling_7d_sleep_debt` 和 `hrv`，但两个脚本只填充 `cumulative_sleep_debt` / `consecutive_poor_sleep` / `sleep_duration` / `energy_level` / `mental_load`。**Sleep Debt Level 1/2、HRV Recovery Alert 这三个熔断器永远不会被脚本触发** —— 目前能看到它们 "active" 完全是 weekly-review AI skill **绕过脚本、手算**的结果。

Plus 一个**数据无用化**问题：新加的 `readiness.*` / `training.*` / `activities[]` 三块，在 `weekly_synthesis.py` 和 `report_gen.py` 里**零消费**，它们目前只是装饰在 daily log 里。

**总工作量估计**：P0 修复约 2-3h（schema 对齐 + 两个静默 bug），P1 数据消费约 2-4h（真正用上 COROS 新数据），P2 整理 1-2h（配置清理、死文件删除）。总计 5-9h，可分 3 轮逐步推进。

**最大 unlock**：P0 做完后，circuit breakers 真正 work，`make check` 不再崩，weekly report 的睡眠数据不再全 0。

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
| `config/thresholds.yaml` | 阈值 + 熔断规则 | 🟡 drifted | 5 个旧 schema 字段 + 缺失 `critical_debt_hours` |
| `templates/daily.md` | frontmatter 模板 | ✅ OK | 已更新为新 schema |
| `scripts/sync_coros.py` | COROS 拉取 + 落盘 + 调 patch | ✅ OK | 本次新增 |
| `scripts/patch_coros.py` | 把 fitness yaml merge 进 daily.md | ✅ OK | 本次新增 |
| `scripts/sync_scale.py` | Zepp CSV → body.* | ⚫ 归档候选 | 用户已 revert 为手填，脚本变成 dead code |
| `scripts/report_gen.py` | daily logic engine | 🔴 **崩溃** | L47 读取不存在的键；L80 读取已删字段 |
| `scripts/weekly_synthesis.py` | 周度聚合 | 🔴 **数据失真** | L109/110/119/124 读取已删字段，新 COROS 块零消费 |
| `.claude/skills/daily-report/SKILL.md` | brain-dump 结构化 | 🟡 drifted | L29-31 提取已删字段 |
| `.claude/skills/weekly-review/SKILL.md` | 评分 + P0/P1/P2 输出 | 🟡 drifted | L67/69/88 三处评分规则依赖旧字段 |
| `.claude/skills/coach-planner/SKILL.md` | 时间表生成 | ✅ OK | 使用新字段（`sleep.duration` 等），无修复需要 |
| `.claude/skills/coach-planner/references/schedule-rules.md` | 排期格式 | ✅ OK | |
| `.claude/skills/coach-planner/references/meal-library.md` | 饮食库 | ✅ OK | |
| `.claude/skills/coach-planner-workspace/` | eval artifacts | ⚫ 归档候选 | 迭代过程产物，不影响运行 |
| `prompts/weekly_review_agent.md` | 旧版 weekly prompt | ⚫ **文件不存在** | 被 skill 取代，但 `weekly_synthesis.py:245-250` 还在尝试读取（有 fallback，不崩） |
| `Makefile` | 入口 | 🟡 `check` target 崩溃 | 其他 target OK |
| `user_profile.md` | 用户画像 | ✅ OK | 无旧字段引用 |
| `.venv/` + `~/tools/coros-mcp/` | Python 环境 | ✅ OK | |

---

## 3. Findings

### 3.1 Schema Drift（已知 5 处，需优先对齐）

新 schema 删除了 `sleep.quality` / `sleep.bedtime` / `sleep.wakeup` / `sleep.interruptions` / `sleep.deep_pct` / `sleep.rem_pct` / `sleep.light_pct`；新增 `sleep.deep_min` / `light_min` / `rem_min` / `nap_min` / `avg_hr` / `min_hr` / `max_hr`，以及 `readiness:` / `training:` / `activities:` 三个顶级块。

| # | 位置 | 具体问题 | 严重度 |
|---|------|----------|--------|
| D1 | `scripts/weekly_synthesis.py:107-125, 164-167, 228-229, 274-276` | 聚合 `deep_pct`/`rem_pct`/`sleep_quality` 和 `consec_poor` — 新日志全部产生 `0` / `[]`，周报里 "深睡占比 0%"、"Poor 睡眠 0 天" 均为 false-negative | 🔴 P0 |
| D2 | `scripts/report_gen.py:78-86, 131-137, 161-168` | `sleep_q = sleep_data.get("quality")` 永远为 None，Rule 3 睡眠质量追踪 + Rule 连续 Poor 告警彻底失效 | 🔴 P0 |
| D3 | `.claude/skills/weekly-review/SKILL.md:67` | Health 评分 "Sleep quality: 0 Poor days = 10 pts" — 新 schema 没有 quality 字段，这项评分没有输入 | 🟡 P1 |
| D4 | `.claude/skills/weekly-review/SKILL.md:69` | Health 评分 "deep% in range, HRV stable" — deep% 已删，要换成 `deep_min` 或比率计算 | 🟡 P1 |
| D5 | `.claude/skills/weekly-review/SKILL.md:88` | Habits 评分 "Bedtime/wakeup consistency (stddev of bedtime < 30min)" — 两个字段已删，这 2 分目前无法合规给出 | 🟡 P1 |
| D6 | `.claude/skills/daily-report/SKILL.md:29-31` | Brain-dump 抽取规则要求产出 `sleep.quality` / `sleep.bedtime` / `sleep.wakeup` — AI 会尝试编造（违反模板） | 🟡 P1 |
| D7 | `config/thresholds.yaml:15-20` | `deep_pct_range` / `rem_pct_range` / `light_pct_max` / `awake_min_max=20` / `interruptions_max=1` — 前 3 个键已无字段映射；`awake_min_max` 新 schema 仍有但阈值 20 min 偏严（用户 04-21 即 70min）；`interruptions_max` 字段已删 | 🟢 P2 |

### 3.2 Pre-existing Bugs（**不是这次引入的**，但一并修掉）

#### B1. `report_gen.py:47` 读取不存在的键 → `make check` 崩溃 🔴 P0

```python
critical_debt = config["sleep"]["critical_debt_hours"]  # KeyError
```

`thresholds.yaml` 里 `sleep:` 块**完全没有** `critical_debt_hours` 这个键。该值后来用于 L171-172 的累计负债告警（`if total_sleep_debt >= critical_debt`）。此脚本跑不起来，说明用户长期没单独执行 `make check`。

**Verification 命令**（不要跑，避免打乱）: `make check 2>&1 | head -5`

#### B2. 熔断器 metric 名字全线对不上 🔴 P0

`thresholds.yaml` 中定义的 3 个关键熔断器：

| 熔断器 | 条件 metric | 脚本填充值 | 是否能触发 |
|---|---|---|---|
| Sleep Debt Level 1 | `rolling_7d_sleep_debt >= 5.0` | 脚本无此键 → default 0.0 | ❌ 永不触发 |
| Sleep Debt Level 2 | `rolling_7d_sleep_debt > 8.0` | 同上 | ❌ 永不触发 |
| HRV Recovery Alert | `hrv < 30` | 脚本无此键 → default 0.0 | ⚠️ **永远触发**（0 < 30） |

脚本侧 (`report_gen.py:111-137`, `weekly_synthesis.py:174-197`) 实际填充的只有：
- `sleep_duration`
- `energy_level`
- `mental_load`
- `cumulative_sleep_debt`（键名与 thresholds 的 `rolling_7d_sleep_debt` 不匹配）
- `consecutive_poor_sleep`（依赖已坏的 quality 字段）

这就是 W16 weekly report 开头那段警告的原因（"脚本误报说明：将 null energy/HRV 计算为 0.0 触发了 Energy Collapse 和 HRV Recovery Alert"）—— 用户以为是 null 问题，**根因其实是 metric 名字不匹配 + 缺值默认为 0**。

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

**Proposed fix**: 把熔断器的 metric lookup 改为 `None`-aware —— 缺数据时跳过判定，而不是用 0 判定。

### 3.5 Skill 边界 / 责任归属

读了所有 SKILL.md，边界总体清楚（coach-planner 排期、weekly-review 评分、daily-report 提取），但有**两处模糊**：

- **`daily-report.SKILL.md` 没说 COROS 数据从哪来** —— 现在的流程是：用户 brain-dump → daily-report 生成 .md（含空 sleep 块）→ 单独跑 `make sync-coros` 填充。如果顺序反了（先 sync-coros 再 daily-report），后者会不会覆盖？需查 SKILL.md 的 "如果该日期文件已存在，先读取现有内容，合并而非覆盖" 是否真的按块级合并。
- **`weekly-review.SKILL.md` 里的 "bedtime 一致性" 评分 (L88)** 只能 fallback 为"睡眠时长一致性"；但谁来决定替换？这种 skill 内部规则调整属于本 plan 的 D5 fix，不需再讨论 ownership。

### 3.6 Makefile 覆盖盘点

现有 target：`today` / `check` / `weekly` / `sync-coros` / `sync-scale` / `report` / `help`。

潜在缺口：
- **`make today` 不会自动跑 sync-coros** — 用户得手动连续跑两条。可考虑让 `today` depend on `sync-coros` with `DATE=$(yesterday)`，但副作用是每次 `make today` 都打 COROS API。**权衡后建议保持独立**（避免偷跑 API；网络慢时 make today 会卡）。
- **缺 `make daily DATE=...`** —— 当前想补写历史日期得手动 `cp` template。加一个 parametric target 1 行搞定。
- **缺 `make clean`** — `weekly_report_prompt.md` 是 gitignored 的中间产物，偶尔手动删一下；非急需。

---

## 4. Prioritized Action Items

每项格式：**ID · 标题 · 优先级 · 文件 · 工作量 · 依赖 · 验证**。

### Wave 1 — P0 correctness fixes（今晚或明早）

---

#### A1. 对齐熔断器 metric 名字

- **Priority**: 🔴 P0
- **Problem**: thresholds 用 `rolling_7d_sleep_debt`，脚本填 `cumulative_sleep_debt`；thresholds 用 `hrv`，脚本根本不填。导致所有 "sleep debt" 和 "HRV" 熔断器 broken（见 B2）。
- **Files**:
  - `scripts/report_gen.py:129-137` (+10 行)
  - `scripts/weekly_synthesis.py:188-197` (+10 行)
- **Approach**:
  1. 把 `cumulative_sleep_debt` 改名为 `rolling_7d_sleep_debt`，语义改为"仅近 7 天 vs baseline 的差"（目前是"全量累计"，范围越大越失真）
  2. 从 fitness yaml 或 daily.md 的 `readiness.hrv` 读取，填入 `latest_metrics["hrv"]`
  3. 熔断判定逻辑：`actual = latest_metrics.get(metric_name)` 若为 None，**skip 此熔断器**（加 `if actual is None: continue`），而不是 default 0
- **Effort**: M (~30min)
- **Depends**: none
- **Verify**: 在 04-17 (sleep 4.77h) 的周，手动跑 `python3 scripts/weekly_synthesis.py --date 2026-04-17`，应看到 `Sleep Debt Level 1` tripped 但 `HRV Recovery Alert` NOT tripped (因 HRV 52 > 30)。

---

#### A2. 修复 `make check` 崩溃：补 `critical_debt_hours` 键 或 删该告警

- **Priority**: 🔴 P0
- **Problem**: `report_gen.py:47` KeyError（见 B1）
- **Options**:
  - (a) `thresholds.yaml` 补 `critical_debt_hours: 10.0`（与熔断 Sleep Debt L2 的 8.0 保持梯度）
  - (b) 删除 L47 + L171-172 的告警逻辑，让 Sleep Debt L1/L2 熔断器完全取代（更清爽）
- **Recommendation**: **(b)**，因为 sleep debt 信号已由两个熔断器覆盖，再搞一个 flat threshold 只是重复。
- **Files**: `scripts/report_gen.py:47, 171-172` (-5 行)
- **Effort**: S (~5min)
- **Depends**: A1（改完 A1 后再做 A2，否则 Sleep Debt 熔断器还是不 work）
- **Verify**: `make check` 能跑通并输出 alerts。

---

#### A3. 迁移 `weekly_synthesis.py` 到新 sleep schema

- **Priority**: 🔴 P0
- **Problem**: L107-125 读 `deep_pct` / `rem_pct` / `sleep_quality`，新日志全部 null（见 D1）
- **Approach**:
  1. 读 `deep_min` / `light_min` / `rem_min` / `awake_min` 代替三个 `*_pct`
  2. 从 `readiness.hrv` 代替旧 `sleep.hrv`
  3. 砍掉 `sq` / `sleep_quality` / `consecutive_poor_sleep` 所有逻辑（新 schema 没有 quality 字段），改用复合判定："本日 sleep.duration < 6.5 或 awake_min > 40 或 hrv 跌破 baseline 15% 即记为 Poor 日"（详见 A4 的 sleep quality derivation）
  4. 把 L226-229 的输出改成 "Avg Deep minutes / Avg REM minutes / Avg HRV"
  5. L274-276 prompt 区块同上
- **Files**: `scripts/weekly_synthesis.py:82-125, 164-197, 220-232, 267-281` (~40 行 net)
- **Effort**: M (~45min)
- **Depends**: A4 的定义（sleep quality 如何 derive）
- **Verify**: 对 W17 (2026-04-20 起) 跑一次，检查 `Avg Deep minutes` 有值非 0，`Avg HRV` 非 0。

---

#### A4. 定义 "Poor Sleep Day" 的新 derivation（替代 sleep.quality）

- **Priority**: 🔴 P0（是 A3 的前置决策，效率合并做）
- **Problem**: 新 schema 没有 Good/Fair/Poor 字段，多个 skill 评分依赖
- **Proposed derivation**（三选一或复合，需用户拍板，见 §6）:
  | 方案 | 判定 | 优点 | 缺点 |
  |---|---|---|---|
  | Option P-a | duration < 6.5h | 简单 | 忽略 HRV/结构 |
  | Option P-b | HRV < baseline × 0.85 | 反映恢复 | 波动大 |
  | Option P-c | duration < 6.5h **或** awake_min > 40 **或** HRV < baseline × 0.85 | 覆盖全 | 判定太宽，易 false positive |
  | Option P-d（**推荐**） | **duration < 6.5h OR (awake_min > 40 AND HRV < baseline × 0.9)** | 时长短是刚性，碎片化+低 HRV 组合才算差 | 需同时两指标 |
- **Effort**: S（单纯决策，编码在 A3 里）
- **Depends**: user sign-off（见 §6 Q1）

---

#### A5. 迁移 `report_gen.py` 到新 sleep schema

- **Priority**: 🔴 P0
- **Problem**: L78-86 / L131-137 / L161-168 读 sleep.quality，Rule 3 + 连续 Poor 告警 broken（见 D2）
- **Approach**:
  1. 用 A4 决策的 derivation 计算 per-day poor 标记
  2. `latest_metrics["consecutive_poor_sleep"]` 改为基于此 derivation
  3. 同 A1，填入 `latest_metrics["hrv"]` 从 readiness
- **Files**: `scripts/report_gen.py:77-86, 119-137, 161-168` (~30 行 net)
- **Effort**: M (~30min)
- **Depends**: A1, A4
- **Verify**: 跑 `make check`，对 04-17（短睡）标 Poor、04-21（7.65h）不标 Poor。

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

#### C3. `sync_scale.py` 归档 + `Makefile` 的 `sync-scale` target 处理

- **Priority**: 🟢 P2
- **Problem**: 用户已 revert 为手填 body.*，脚本 + make target 成 dead surface
- **Options**:
  - (a) 保留 sync-scale target 但注释标 "deprecated, manual entry preferred"
  - (b) 移除 make target，把脚本移到 `scripts/archive/`
- **Recommendation**: **(b)** — 清爽。用户记忆里有 feedback-body-data-manual，以后不太可能回头。
- **Files**: `Makefile` (-15 行); `scripts/sync_scale.py` → `scripts/archive/`
- **Effort**: S (~5min)
- **Depends**: user 确认不后悔
- **Verify**: `make help` 不再出现 `sync-scale`

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

## 5. Recommended Sequencing

### Wave 1 (今晚 21:45 断电前 或 明早 — **P0 critical**)

**目标**：让系统"说实话" —— 熔断器真的能触发、`make check` 不崩、周报数据不 silently 归零。

**顺序**：A4 决策 → A1 metric 改名 → A2 删 critical_debt 分支 → A5 report_gen 新 schema → A3 weekly_synthesis 新 schema

**为什么这个顺序**：
- A4 是所有 "quality derivation" 的设计前置
- A1 先改 metric 名，是 A5/A3 里填新 metric 的基础
- A2 紧跟 A1 (同一文件相近行)
- A5、A3 最后合并（一次性把 schema drift 清掉）

**估时**：合计 ~2h，可一次性做完

### Wave 2 (本周周末前 — **P1 rubric alignment**)

**目标**：skill 评分能实打实给出分数，不再有 "undefined field" 尴尬。顺带把 COROS 新数据接入周报。

**顺序**：B3 thresholds 扩展 → B1 weekly-review 三处评分 → B2 daily-report 删旧字段 → B4 聚合新 COROS 块

**估时**：合计 ~1.5h

**时机建议**：周六 10:00-11:30（System Offline 原则上禁止编程，但这属于"为下周系统健壮性做准备" —— 界线模糊，建议用户自己决定是否放在周日 meal prep 前做）

### Wave 3 (W18 或之后 — **P2 cleanup**)

**目标**：清理 dead surface、加 QoL 功能。

**顺序**：C1 prompts 死引用删除 → C2 新熔断器 → C3 sync_scale 归档 → C4 make daily → C5 常量清理 → C6 eval artifacts

**估时**：合计 ~1h

**时机**：单独抽一个 coding 时段，或拆成 3-4 次每次 15-20min 搞一两个。

---

## 6. Risks & Open Questions

**Q1. "Poor Sleep Day" 的 derivation（A4 抉择）**
- 选 Option P-d（duration < 6.5 OR (awake > 40 AND HRV < baseline × 0.9)）？
- 还是更保守的 P-a（仅 duration < 6.5）？
- 前者更全面但可能让 Poor 日变多；后者保留与旧系统一致的 signal 但忽略碎片化

**Q2. `total_sleep_debt` 语义**
- 目前脚本 L131 (`weekly_synthesis.py`) 计算的是**本周全量累计**（比如周一累计到周日）
- 熔断器 `rolling_7d_sleep_debt` 用的是**滚动 7 日**
- 周聚合 vs 滚动窗口在周初/周末会有显著差异
- 建议：改为"从 **今天往回** 7 天"的 rolling window，与熔断器语义一致

**Q3. HRV threshold 要用绝对值 30 还是相对 baseline？**
- 现在 `hrv_warning_low: 30` 是绝对阈值，适合"机器警告"
- 但用户 baseline 54 → HRV 45 (−17%) 就已经值得注意，远早于到 30
- 建议：保留绝对 30 作为"红线"（触发 HRV Recovery Alert 强制恢复日），另加一个"相对 < 0.85 × baseline" 作为黄线（仅提示，不强制）

**Q4. `awake_min_max: 20` 太严格？**
- 用户 04-21 即录得 70min，但那晚 7.65h 睡眠且 HRV 50 并不算差
- 建议调到 40（B3 提议值）

**Q5. `make check` 语义**
- 修好 A1/A2 后，这个 target 输出的 alerts 目标是谁看？
  - 用户每天手动看？（当前没这习惯）
  - weekly-review skill 读？（目前 skill 不调用 `make check`，只调用 weekly_synthesis）
- 如果没人真的消费，修它的 ROI 不高；但不修又留崩溃代码。
- 建议：**修到能跑**（A1+A2）但不追求"让每天的告警被看见"这个功能

**Q6. COROS 数据的"信任边界"**
- `readiness.tired_rate = -24` 算不算"身体反馈"？
- 如果 AI 在周报里说"本周疲劳指数均值 -22，偏疲劳"，用户会买账吗？还是认为是黑盒数字？
- 如果不买账，B4 的聚合价值打折扣
- 建议：**先做 B4**，观察两周周报里 AI 怎么使用这些数字，再决定要不要深挖

**Q7. 是否让 `make sync-coros` 自动 + sync-scale 统一为 `make sync`？**
- 现在 sync-scale 即将 archive（C3），所以这个问题会自动消失

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

---

## 8. Meta Notes

- 本 plan.md 会随实施进度被**更新**（Wave 1 完成后 strike-through 掉 A1-A5）而不是删除，作为 W17 系统健康度的书面记录
- 用户确认方案后，建议在一次会话内完成整个 Wave 1（避免跨会话上下文丢失，也便于原子化 commit）
- 每个 Wave 做完后建议 commit 一次，commit message 格式：`refactor(schema): migrate <component> to new COROS sleep schema (Wave N / A#)`（遵循用户的 split-commits 偏好，memory: `feedback-split-commits`）
- 所有修改应 run `python3 -m py_compile scripts/*.py` 做语法检查，以及手动跑一次 `make check && make weekly` 回归
