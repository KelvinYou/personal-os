# Personal-OS — AI Agent 协作规范

> 本文件是所有 harness（Claude Code / Codex / …）协作规范的**唯一 owner**。
> `CLAUDE.md` 只是 import 本文件，不要在那边另写内容。

## 项目概述
个人管理系统，通过结构化日志 + AI Agent 实现数据驱动的自我管理。核心闭环：每日记录 → 逻辑引擎告警 → 周度综合分析 → 下周排期。

## 目录结构
> 本块由 `make doctor` 逐条 `test -e` 校验（data/ 未 checkout 时豁免其下条目）。
> 改布局请同步改这里 —— 本文件每次会话强制注入，路径写错会让 agent 直接读错文件。
```
/config/                  — 我的阈值设定 + 法规常量 (thresholds / wealth_rules.yaml)
/market/                  — 外部可观测市场事实 (interest_rates / fx.yaml, jobs/)；public，无个人信息
/data/                    — private submodule (personal-os-data)；无权限时不 checkout
/data/daily/              — 每日工程师日志 (YYYY-MM-DD.md)；热窗口 90 天，更旧的由 make archive 折叠
/data/archive/            — 冷数据归档 (YYYY-Qn.md 周摘要 + body.csv 体成分全序列)
/data/protocol/           — 常驻 protocol；standard_week.md 是唯一的人类时间表，每周不重排；standard_week.yaml 仅为 Calendar anchors projection
/data/finance/            — 财务持仓 (savings / portfolio / policy.yaml)
/data/reports/            — 周报存档 + 周度 delta (仅在有例外时生成)
/data/reports/evals/      — session eval 记录 (make eval 产出；审计 agent 自己，不是审计我)
/data/user_profile.md     — 全局用户画像 (作息/饮食/锻炼偏好)
/docs/                    — 长文档；三个 owner：VISION(方向) / ROADMAP(待办) / DECISIONS(已决定不重提)
/docs/voice-guide.md      — 我的写作声音 (从 34 篇已发布 blog 反推)；写任何对外文字前先读
/ARCHITECTURE.md          — 系统架构 + 不变量；改数据流/契约前先读它
/SETUP.md                 — 首次 bootstrap 流程；顶部注释块是给 agent 的交互式脚本
/templates/               — 空白模板文件
/scripts/                 — 自动化脚本 (Python 3)
/tests/                   — 单元测试 + fixtures (不读真实私有数据)
/web/                     — 本地理财仪表盘 (Next.js, localhost only)
/.agents/skills/          — AI Agent skills (weekly-review / wealth-manager / ...)
/repos/                   — 外部项目 submodules，统一管理 + 供 skills 读取
/repos/portfolio-website  — 个人网站 (career 相关统一入口)
/repos/ai-stock-analysis  — 股票分析工具；亦是股价的唯一 owner
/repos/kelvinyou-notes    — 公共笔记 submodule；nutrition 数据集的唯一 owner
/scripts/nutrition.py     — nutrition 查询 adapter（读 repos/kelvinyou-notes，见 docs/plan-public-knowledge-integration.md）
/scripts/lib/nutrition/   — nutrition adapter 的共享实现（basis 换算、macro/成本推导）
```

## 关键约定
- 每日日志文件名格式: `YYYY-MM-DD.md`
- YAML frontmatter 必须通过 `scripts/lib/schema.py` 校验；字段清单与模板保持 parity（可选字段允许留空）
- 所有阈值从 `config/thresholds.yaml` 读取，脚本中禁止硬编码魔法数字
- 脚本使用 Python 3，依赖见 `requirements.txt`（`make setup` 安装到 `.venv/`）
- 输出全量符合 CommonMark 标准

## 常用命令
- `make setup` — 建立 `.venv` 并安装依赖
- `make setup-private` — checkout private `data` submodule（需仓库权限）
- `make doctor` — 环境自检；区分 error / expected（如无权限时 data 未 checkout）/ warning
- `make test` — Python 测试 + web typecheck
- `make today` — 生成今天的日志模板
- `make check` — 运行逻辑引擎检查所有日志
- `make weekly` — 聚合本周数据，生成周报 prompt
- `make report` — 一键生成完整周报 (聚合 + 调用 AI)
- `make wealth` — Tracked Assets: 现金/到期/利率 + 股票估值（NAV 计价产品仍不含）
- `make eval` — 把最近一次 Claude Code session 转成 eval 记录（`SESSION=recent-3` 指定）
- `make eval-rollup` — 月度 agent signal 汇总；`/meta-coach` 读这份，不读单条 eval

## AI Agent 协作须知
- 生成排期时必须参考 `data/user_profile.md` 中的作息/饮食偏好
- 评分框架使用四维度权重 (产出40/健康30/心智20/习惯10)
- 日志风格: 工程师视角，使用 `[Status: OK/Warning/Critical]` 标记
- 中文为主，技术术语保留英文原文
- 写任何**对外文字**（blog / LinkedIn / README 散文 / commit body）前先读
  `docs/voice-guide.md`。仓库内部报告不受它管，继续用 `[Status: ...]` 那套。

## 收尾时给三个下一步
答完一个请求后，主动给 3 个可选的下一步，不要问「还需要什么吗」：
- **第 1 个必须是我想不到但会觉得有用的** —— 从这次上下文里看出来的机会，
  不是把我刚说的话重述一遍。
- 第 2、3 个是自然的后续（跑什么命令、改哪个文件）。
- 每个一行，带上具体命令或路径。看不懂就别猜。

例外，此时跳过：我在连续快速下指令（说明我心里有序列，插建议是打断）；
或者这一轮本身就是我在回答你的问题。

## 会话结束后审计 agent 自己
`make eval` 把 transcript 转成 `data/reports/evals/` 里一条记录：事实 + 机械
signal（write-before-read / unverified-mutation / tool-error-loop / user-correction …），
每条 signal 都写了「什么证据能推翻它」。

- `judgement` / `agents_md_change` / `notes` 三个字段**生成时一律为 null**。
  自己给自己打分的 auditor 等于对被审计对象有写权限 —— 那是 `/decision-log`
  里同一个坑。人或 `/meta-coach` 事后填。
- 重新生成不会覆盖已填的 review 字段（除非 `--force`）。
- 单条 eval 证明不了什么；`make eval-rollup` 的分布才是证据。同一个 signal 在
  一个月里命中过半 → 那是 AGENTS.md 的 bug，不是那次会话的 bug。
