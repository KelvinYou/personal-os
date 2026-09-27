# Personal-OS

个人管理系统 Repo：通过结构化日志、逻辑引擎与 AI Agent 实现数据驱动的自我管理。

> 架构细节见 [ARCHITECTURE.md](ARCHITECTURE.md) | 产品方向见 [docs/VISION.md](docs/VISION.md) | 协作规范 + 完整目录树见 [AGENTS.md](AGENTS.md)

## 核心闭环

```
Brain Dump → /daily-report → 逻辑引擎告警 → /coach-planner → 每日排期
                ↑                                      ↑
         COROS 手表自动同步                      /weekly-review
```

## 目录速览

完整目录树的唯一 owner 是 [AGENTS.md](AGENTS.md)（`make doctor` 逐条校验）；这里只给入口地图。

| 位置 | 用途 |
|------|------|
| `.agents/skills/` | Agent skills，见下方 [Claude Code Skills](#claude-code-skills) |
| `config/` | 公开的法规与流水线设置；个人阈值在 `data/config/` |
| `market/` | 外部可观测市场事实（利率/汇率/JD）；public |
| `data/` | 🔒 你自己的独立私有仓库（主仓库忽略此目录）—— 日志、配置、决策、财务、profile |
| `scripts/` | Python 自动化（逻辑引擎、COROS 同步、周度聚合、doctor…） |
| `web/` | 本地理财仪表盘（Next.js，localhost only） |
| `repos/` | 外部项目 submodules |
| `docs/` | INDEX 路由 + VISION（方向）/ ROADMAP（待办）/ DECISIONS（已决定不重提）/ knowledge notes |
| `templates/` · `tests/` | 空白模板 / 单元测试 |

## 快速开始

> 第一次进这个仓库、或想让 agent 带着配：读 [SETUP.md](SETUP.md)（顶部注释块是给 agent 的交互式 bootstrap 脚本）。

```bash
git clone https://github.com/KelvinYou/personal-os.git
cd personal-os
git submodule update --init repos/ai-stock-analysis repos/notes # 按需
make setup      # 建 .venv + 装依赖
make doctor     # 环境自检
```

创建你自己的**私有** Git 仓库（空仓库也可以）后，运行 `make setup-private DATA_REPO=<你的私仓 URL>`。
这会把私仓 clone 到 `data/`，并复制待个性化的配置示例。逐项检查
`data/config/thresholds.yaml`、`data/config/settings.yaml`，确认后将各文件的
`owner_configured` 改为 `true`，填写 `data/user_profile.md`，再运行 `make doctor`。
如果 `data/` 已有文件，初始化命令会拒绝覆盖；先把它们安全迁入自己的私仓。
主仓库不会记录你的私仓 URL 或 commit。

常用命令一览（用途，不重复参数细节 —— 完整清单见 [AGENTS.md](AGENTS.md#common-commands)）：

| 命令 | 用途 |
|------|------|
| `make today` | 生成今天的日志模板 |
| `make sync-coros` | 同步 COROS 昨日数据（睡眠/HRV/活动）写入日志 |
| `make sync-calendar` | 同步 Google Calendar 日程 |
| `make check` | 跑逻辑引擎告警检查 |
| `make weekly` / `make report` | 生成周报 prompt / 一键完整周报 |
| `make wealth` | 净资产：现金/到期/利率 + 股票估值 |
| `make web` | 本地理财仪表盘 |
| `make test` / `make lint` | 单元测试 + web typecheck / 日志 lint |
| `make kb-check` / `make kb-index` / `make kb-eval` / `make kb-graph` | Knowledge-note contract / catalog / retrieval eval / Mermaid view |
| `make archive` | 折叠 90 天热窗口外的日志 |
| `make decisions-due` / `make decision-new` | 决策待review列表 / 创建新决策条目 |
| `make calibration` | 决策校准分析 |
| `make quarterly` | 季度身份审计 |

COROS 同步需要项目根目录 `.env`（`COROS_EMAIL` / `COROS_PASSWORD` / `COROS_REGION`）。

逻辑引擎阈值规则见私仓的 `data/config/thresholds.yaml`；公开示例在 `templates/thresholds.example.yaml`。
四维评分框架（Output/Health/Mental/Habits）见 weekly-review skill。理财模块目前面向马来西亚、MYR/USD 场景；COROS、Calendar 和股票流水线按需启用。

## Claude Code Skills

| 命令 | 功能 |
|------|------|
| `/daily-report` | Brain Dump 转结构化日志 |
| `/weekly-review` | 周度综合分析与下周目标 |
| `/coach-planner` | 教练式排期 + 实时决策支持 |
| `/wealth-manager` | 投资组合分析、买入时机、净资产汇总 |
| `/learning-agent` | AI 时代技能雷达与学习规划 |
| `/decision-log` | 决策日志捕获 |
| `/decision-review` | 决策回顾与校准 |
| `/meta-coach` | 月度 agent 建议质量审计 |
| `/identity-audit` | 季度行为 vs 声称身份审计 |
| `/profile-optimizer` | 用 JD 数据改写 LinkedIn / portfolio 文案与排序 |
| `/contract-guardian` | 跨层改动（schema / 脚本 / 文档）的语义契约审查 |
| `/quant-backtest-review` | ai-stock-analysis 回测与信号代码的对抗式复核 |
| `/repo-orchestrator` | 多仓库协作：submodule 同步、集成检查、提交前把关 |
| `/skill-creator` | 技能创建、优化与 eval（上游开源技能，非本仓库维护） |

`/git-commit` 与 `/diagram-flow` 已迁至 [agent-toolkit](https://github.com/KelvinYou/agent-toolkit)，通过 plugin 安装：

```
/plugin marketplace add KelvinYou/agent-toolkit
/plugin install agent-toolkit@agent-toolkit
```

## 依赖

依赖清单唯一 owner 是 `requirements.txt`。`make setup` 安装；`make doctor` 验证 venv/私有数据/股价 pipeline/web 依赖。COROS 同步另需 `coros_api`（内部包），仪表盘另需 `cd web && npm i`。
