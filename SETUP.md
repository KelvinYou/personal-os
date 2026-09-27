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
│  2. Never invent values for data/config/thresholds.yaml or data/user_profile.md. │
│     Examples are not personal settings. Keep owner_configured: false until   │
│     the owner has reviewed every value.                                       │
│  3. Phase 3 (personalisation) is where a wrong answer does lasting damage:  │
│     thresholds feed circuit breakers, which gate every coach-planner        │
│     schedule. Confirm each answer back before writing.                      │
│  4. If the user has no private data repo yet, stop after Phase 2 and help   │
│     them create one. Do not write personal data into the public repository. │
│                                                                             │
│ Questions to ask in Phase 3, in this order — one at a time, not batched:    │
│   Q1 What is the URL of your own private data repo?                         │
│   Q2 Timezone and daily wake/sleep window? → data/config/settings.yaml      │
│   Q3 Target deep-work hours per weekday? → private thresholds.deep_work     │
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
| 自己的 private Git repo | 见 Phase 2 | 可先只运行 public 测试；个人功能需要配置 |

## Phase 1 — 骨架

```bash
git clone https://github.com/KelvinYou/personal-os.git
cd personal-os
git submodule update --init repos/ai-stock-analysis repos/notes # 可选
make setup     # 建 .venv + 装 requirements.txt
make doctor    # 第一次 gate
```

`make doctor` 分三类结论，语义不同，**不要混着看**：

- `error` — 仓库/环境坏了，照它给的修复命令处理。
- `expected` — 尚未接入自己的 `data/` 私仓，个人功能暂不可用。
  **这不是故障。** 把权限边界报成失败会训练人忽略这个命令。
- `warning` — 能跑，但结果缺一块（如 `repos/ai-stock-analysis/data/` 为空 →
  股票全部 unpriced，合计被低估）。

退出码只有 `error` 是 1。

## Phase 2 — 接入自己的私有数据仓库

```bash
make setup-private DATA_REPO=git@github.com:you/my-personal-os-data.git
```

命令会把你的私仓 clone 到 `data/`；主仓库忽略这个目录，不记录它的 URL 和 commit。
如果 `data/` 已有文件，命令会拒绝覆盖。先把文件安全迁入你的私仓，再重新运行。
没有私仓时，以下命令不可用：

- `make wealth` / `make web`（读 `data/finance/*.yaml`）
- `make check` / `make weekly` / `make report`（读 `data/daily/`）
- 依赖日志的 skills：`/weekly-review`、`/coach-planner`、`/identity-audit`、
  `/meta-coach`

仍然可用：`make doctor`、`make test`、`make check-mermaid`、`make eval*`
（session eval 读的是 `~/.claude/projects/`，与私仓无关）、
`/learning-agent`、`/profile-optimizer`、`/quant-backtest-review`。

私仓内应保留 `config/settings.yaml`、`config/thresholds.yaml`、
`user_profile.md` 和 `daily/`。首次 clone 后会复制两个配置示例；它们的
`owner_configured: false` 会阻止个人命令运行。逐项核对后改为 `true`。
`templates/daily.md` 是日志模板，`scripts/lib/schema.py` 是 frontmatter schema。

## Phase 3 — 个性化（agent 在这里逐条问你）

公开示例里的数字不是通用默认值。必须根据自己的情况配置私仓，
否则逻辑引擎不能生成个人结论。

| 文件 | 里面是什么 | 不改的后果 |
| :--- | :--- | :--- |
| `data/config/thresholds.yaml` | deep_work / sleep / readiness / energy / caffeine / circuit_breakers / scoring | 无效时拒绝运行 |
| `data/config/settings.yaml` | 本地时区 | 日期可能跨日 |
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
