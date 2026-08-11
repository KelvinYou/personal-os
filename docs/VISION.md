# Personal-OS — 产品方向与架构愿景

## 核心定位

**一套以工程师思维构建的个人控制系统**——不是简单的习惯追踪器，而是具备状态感知、梯度降级、闭环反馈的自我管理操作系统。

## 设计哲学

1. **Config-Driven** — 所有阈值外部化，零硬编码魔法数字
2. **Graceful Degradation** — 4 级运行模式（OK → Warning → Critical → Breaker），不是 on/off
3. **Closed-Loop Feedback** — 每日记录 → 逻辑引擎告警 → 周度综合分析 → 下周排期
4. **AI-Native** — 系统从第一天就为 Agent 协作设计，不是事后加 AI
5. **Honesty Over Vanity** — 记录真实数据，接受低分，做根因分析

## 系统控制流

```mermaid
---
title: Personal-OS Control Tower
---
stateDiagram-v2
    direction TB

    state "📥 Daily Input Layer" as input {
        [*] --> BrainDump: 自然语言碎碎念
        BrainDump --> DailyReport: daily-report skill
        DailyReport --> YAML: 28-field frontmatter
        DailyReport --> Narrative: 工程师日志
    }

    state "⚙️ Logic Engine (report_gen.py)" as engine {
        state eval <<choice>>
        YAML --> eval
        eval --> OK: all metrics green
        eval --> Warning: threshold breach
        eval --> Critical: multi-metric failure
        eval --> BREAKER: cascade detected

        state "🟢 OK" as OK {
            state "Deep Work ≥ 4h" as dw_ok
            state "Energy ≥ 6" as en_ok
            state "Sleep Debt < 5h" as sd_ok
            state "Spend < RM200/wk" as sp_ok
        }

        state "🟡 Warning" as Warning {
            state "Deep Work < 4h" as dw_w
            state "Energy = 5" as en_w
            state "Caffeine > 14:00" as cf_w
            state "Poor Sleep ×1" as sl_w
        }

        state "🔴 Critical" as Critical {
            state "Energy < 4" as en_c
            state "Sleep < 6.5h" as sl_c
            state "Sleep Debt ≥ 10h" as sd_c
            state "Mental Load ≥ 7" as ml_c
        }

        state "⛔ BREAKER (5 types)" as BREAKER {
            state "Sleep Critical\n< 6.5h → Deload" as B1
            state "Sleep Debt ≥ 5h\n→ Restrict Training" as B2
            state "Energy Collapse < 4\n→ DW Cap 2h" as B3
            state "Mental Overload ≥ 7\n→ Single-task" as B4
            state "Poor Sleep ×2+\n→ System Offline" as B5
        }
    }

    state "📊 Weekly Review (Report Agent)" as weekly {
        state "4D Scoring" as scoring {
            state "Output 40pt\nDeep Work hours + quality" as S1
            state "Health 30pt\nSleep + Energy + Exercise" as S2
            state "Mental 20pt\nResilience + Breaker wisdom" as S3
            state "Habits 10pt\nSpend + Micro-habits" as S4
        }
        state "Trend Compare\nWoW delta" as trend
        state "P0/P1/P2 Objectives\n+ Constraints" as objectives
        scoring --> trend
        trend --> objectives
    }

    state "🎯 Coach-Planner (Schedule Agent)" as coach {
        state "Read Objectives\nfrom Report" as read_obj
        state "Assess Current State\nLogs + Breakers" as assess
        state "Next-day Schedule" as sched
        state "Next-week Timetable" as timetable
        state "Decision Support" as decision
        read_obj --> assess
        assess --> sched: 日度排期
        assess --> timetable: 周度排期
        assess --> decision: 实时教练
    }

    input --> engine
    OK --> weekly: 正常积累
    Warning --> coach: 当日调整
    Critical --> coach: 紧急降级
    BREAKER --> coach: 强制干预
    weekly --> coach: P0/P1/P2 + 约束
```

## 四级运行模式

| 模式 | 触发条件 | 系统响应 |
|------|----------|----------|
| **🟢 OK** | 所有指标绿灯 | 正常积累，数据汇入周度分析 |
| **🟡 Warning** | 单指标越线 | coach-planner 当日微调排期 |
| **🔴 Critical** | 多指标同时恶化 | 紧急降级：削减 Deep Work、强制休息 |
| **⛔ Breaker** | 级联故障检测 | 强制干预：Deload / Single-task / System Offline |

## Agent 职责分离

| Agent | 方向 | 输入 | 输出 |
|-------|------|------|------|
| **weekly-review** | 向后看 | 7天日志 + 上周报告 | 诊断报告 + 4D评分 + P0/P1/P2目标 + 执行约束 |
| **coach-planner** | 向前看 | 日志 + 报告目标 + 熔断状态 | 当日/当周/下周时间表 + 决策支持 |

**数据流**：weekly-review 只产出诊断，coach-planner 只产出行动。两者通过 P0/P1/P2 目标接口解耦。

## 双时间轴决策

- **日度（实时）**：brain dump → logic engine → coach-planner → 当天时间表
- **周度（回顾+规划）**：7天聚合 → weekly-review(评分+目标) → coach-planner(下周排期)

## 未来演进方向

### Near-term
- [ ] Logic engine 单元测试覆盖（pytest）
- [ ] COROS / Zepp 数据自动导入（CSV / API）
- [ ] 历史数据查询层（SQLite 替换 flat YAML）

### Mid-term
- [ ] 睡眠债务预测模型（时序分析）
- [ ] 训练负荷周期化（mesocycle 自动排期）
- [ ] 支出燃烧率预警（月度 burn-rate projection）

### Long-term
- [ ] Mobile companion（时间表推送 + 快速 brain dump）
- [ ] 穿戴设备实时流（心率 / HRV → 自动触发 breaker）
- [ ] 多用户抽象（从 personal tool → 可复用框架）
