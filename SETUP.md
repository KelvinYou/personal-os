<!--
┌─────────────────────────────────────────────────────────────────────────────┐
│ AGENT INSTRUCTIONS — read this block before doing anything else             │
│                                                                             │
│ If you are an AI agent (Claude Code / Codex / …) and the user asked to      │
│ set up, bootstrap, onboard, or "get started with" this repo:                │
│                                                                             │
│ Do NOT paste the command list from README.md and stop. Walk the user        │
│ through the phases below interactively, using AskUserQuestion (or plain     │
│ questions if you have no such tool). Run the commands yourself; report      │
│ each result before moving on.                                               │
│                                                                             │
│ Hard rules:                                                                 │
│  1. `make doctor` is the gate. Run it after Phase 1 and again at the end.   │
│     Its `expected` rows are NOT failures — a missing private `data/` is     │
│     access control working, not a broken setup. Never "fix" an expected     │
│     row by creating files under data/.                                      │
│  2. Never invent values for config/thresholds.yaml or data/user_profile.md. │
│     Every number in there is a claim about a specific human. Ask, or leave  │
│     the shipped default and say out loud that it is still Kelvin's.         │
│  3. Phase 3 (personalisation) is where a wrong answer does lasting damage:  │
│     thresholds feed circuit breakers, which gate every coach-planner        │
│     schedule. Confirm each answer back before writing.                      │
│  4. If the user has no `data/` access, stop after Phase 2 and tell them     │
│     which commands are unavailable (`make wealth`, `make web`, anything     │
│     reading data/daily/). Do not fabricate a substitute data layer.         │
│                                                                             │
│ Questions to ask in Phase 3, in this order — one at a time, not batched:    │
│   Q1 Do you have write access to the private `personal-os-data` repo?       │
│      (no → public-only mode; skip Q3–Q6)                                    │
│   Q2 Timezone and daily wake/sleep window? (clock.py assumes Asia/KL)       │
│   Q3 Target deep-work hours per weekday?        → thresholds.deep_work      │
│   Q4 Minimum acceptable sleep, and your HRV baseline if you know it?        │
│                                                 → thresholds.sleep/readiness│
│   Q5 Do you wear a COROS watch? (no → skip make sync-coros entirely)        │
│   Q6 Which currency and country for the finance rules?                      │
│                                    → config/wealth_rules.yaml, market/      │
│                                                                             │
│ When every phase is done, run `make doctor` and `make test`, then print the │
│ "First week" list at the bottom of this file. Stop there. Do not start      │
│ generating logs, schedules, or reports unless the user asks.                │
└─────────────────────────────────────────────────────────────────────────────┘
-->

# Setup

两条路。人类想自己跑命令 → 直接看 [README.md 的快速开始](README.md#快速开始)。
想让 agent 带着走一遍（推荐首次） → 对 agent 说：

```
读 SETUP.md，带我把这个仓库配起来
```

Agent 会照本文件顶部那段注释里的流程逐阶段问你、跑命令、报结果。那段注释是给
agent 看的，人类可以忽略。

> 为什么单独一个文件：README 是给人看的命令清单，AGENTS.md 是常驻规范。两者都
> 没有「第一次进这个仓库该按什么顺序问什么」。以前这段知识只存在于我脑子里，
> 换一台机器或换一个 agent 就得重新解释一遍。

---

## Phase 0 — 前提

| 需要 | 检查 | 缺了怎么办 |
| :--- | :--- | :--- |
| Python ≥ 3.11 | `python3 --version` | 装它；`zoneinfo` 和 `X \| None` 语法都依赖 |
| git | `git --version` | — |
| Node（仅 dashboard） | `node --version` | 跳过，CLI 全部不依赖 |
| `personal-os-data` 权限 | 见 Phase 2 | 无权限也能用大部分功能，见下 |

## Phase 1 — 骨架

```bash
git clone --recurse-submodules https://github.com/KelvinYou/personal-os.git
cd personal-os
make setup     # 建 .venv + 装 requirements.txt
make doctor    # 第一次 gate
```

`make doctor` 分三类结论，语义不同，**不要混着看**：

- `error` — 仓库/环境坏了，照它给的修复命令处理。
- `expected` — 按设计就不该有。典型：无 private repo 权限时 `data/` 未 checkout。
  **这不是故障。** 把权限边界报成失败会训练人忽略这个命令。
- `warning` — 能跑，但结果缺一块（如 `repos/ai-stock-analysis/data/` 为空 →
  股票全部 unpriced，合计被低估）。

退出码只有 `error` 是 1。

## Phase 2 — 私有数据层（可选）

```bash
make setup-private   # 需要 personal-os-data 的读权限
```

有权限 → `data/` 里出现 daily/ decisions/ finance/ protocol/ user_profile.md。
无权限 → 到此为止，以下命令不可用：

- `make wealth` / `make web`（读 `data/finance/*.yaml`）
- `make check` / `make weekly` / `make report`（读 `data/daily/`）
- 依赖日志的 skills：`/weekly-review`、`/coach-planner`、`/identity-audit`、
  `/meta-coach`

仍然可用：`make doctor`、`make test`、`make check-mermaid`、`make eval*`
（session eval 读的是 `~/.claude/projects/`，与 data submodule 无关）、
`/learning-agent`、`/profile-optimizer`、`/quant-backtest-review`。

**fork 这个仓库自己用**：`data` 指向我的私仓，你 clone 不到。建一个自己的
private repo，改 `.gitmodules` 里 `submodule.data.url` 指过去，按
`templates/daily.md` 的 frontmatter 建第一份日志。schema 由
`scripts/lib/schema.py` 校验，`make lint` 会告诉你缺哪个字段。

## Phase 3 — 个性化（agent 在这里逐条问你）

仓库里所有数字都是**对某个具体的人的断言**，不是通用默认值。fork 之后不改这些，
逻辑引擎会拿我的身体参数评判你的一周。

| 文件 | 里面是什么 | 不改的后果 |
| :--- | :--- | :--- |
| `config/thresholds.yaml` | deep_work / sleep / readiness / energy / caffeine / circuit_breakers / scoring | 熔断按我的 HRV 基线开火 |
| `config/wealth_rules.yaml` | `us_estate`、`prs` —— 马来西亚税务与美国遗产税常量 | 非 MY 税务居民会算错 |
| `data/user_profile.md` | 作息、饮食、锻炼偏好 | `/coach-planner` 排出你不会执行的表 |
| `data/protocol/standard_week.md` | 唯一的人类时间表，每周不重排 | 排期没有锚点 |
| `market/interest_rates.yaml`、`market/fx.yaml` | 外部可观测市场事实 | 现金收益率算错 |

改完必须跑一次 `make test` —— thresholds 走 pydantic 校验，写错字段会 fail-fast，
不会静默变成 0。

## Phase 4 — 验收

```bash
make doctor        # 期望：无 error
make test          # Python 单测 + mermaid 渲染检查 + web typecheck
make today         # 生成今天的日志模板
make check         # 逻辑引擎（有日志才有意义）
```

---

## First week

配完之后，按这个顺序建立习惯 —— 一次只加一个循环，别一天全开：

1. **Day 1–7 每天**：`make today`，然后跟 agent 说今天干了什么，让 `/daily-report`
   把碎碎念写成结构化日志。这一步不做，后面全部无数据可读。
2. **第一个周末**：`make report` → 把 `weekly_report_prompt.md` 交给
   `/weekly-review`，拿到四维评分 + 下周 P0/P1/P2。
3. **紧接着**：`/coach-planner` 排下周时间表。它读 P0/P1/P2 + `user_profile.md` +
   熔断状态。
4. **做了任何非琐碎取舍时**：`/decision-log` 记一条，写下预期结果和 review 日期。
   `make decisions-due` 到期会提醒。
5. **月度**：`make eval-rollup` 看 agent 自己这个月的 signal 分布，
   `/meta-coach` 审计建议质量。审计对象是 agent，不是你。

前四周不要碰 `/identity-audit`（需 ≥ 12 周日志）和 `make calibration`
（需要已 reviewed 的决策）—— 数据不够时它们只会输出噪音。
