# Personal-OS — Architecture

## 1. System Overview

```mermaid
graph TB
    User((👤 User))

    subgraph Input ["Input Layer"]
        BD["Brain Dump\n自然语言"]
        COROS_HW["COROS Watch\n睡眠/HRV/活动"]
    end

    subgraph Agents ["Agent Skills (Claude Code)"]
        DR["/daily-report"]
        CP["/coach-planner"]
        WR["/weekly-review"]
        WM["/wealth-manager"]
        LA["/learning-agent"]
    end

    subgraph Engine ["Logic Engine (Python)"]
        SC["sync_coros.py\nCOROS API 拉取"]
        PC["patch_coros.py\n写入日志 frontmatter"]
        RG["report_gen.py\n规则告警检查"]
        WS["weekly_synthesis.py\n周度数据聚合"]
    end

    subgraph Store ["Data Layer (data/ submodule 🔒)"]
        DL["data/daily/\nYYYY-MM-DD.md"]
        FIT["data/fitness/\nYYYY-MM-DD.yaml"]
        RPT["data/reports/\n周报存档"]
        FIN["data/finance/\nportfolio + rates"]
        UP["user_profile.md"]
        CFG["config/thresholds.yaml"]
    end

    subgraph Output ["Output"]
        ALERT["⚠️ 熔断告警"]
        SCHED["📅 时间表"]
        REPORT["📊 周报"]
    end

    User -- "碎碎念" --> BD
    BD --> DR --> DL
    COROS_HW -- "API" --> SC --> FIT
    FIT --> PC --> DL
    DL --> RG --> ALERT --> User
    DL --> WS --> WR --> REPORT --> User
    REPORT --> CP
    User --> CP --> SCHED --> User
    User --> WM --> FIN
    User --> LA --> UP
    CFG -. "阈值" .-> RG
    CFG -. "阈值" .-> WR
    UP -. "偏好" .-> DR
    UP -. "偏好" .-> CP
```

---

## 2. Daily Loop

每天的核心数据闭环：Brain Dump 结构化 + COROS 自动填充 + 逻辑引擎告警。

```mermaid
sequenceDiagram
    actor User
    participant DR as /daily-report
    participant DL as data/daily/
    participant COROS as COROS API
    participant SC as sync_coros.py
    participant PC as patch_coros.py
    participant FIT as data/fitness/
    participant RG as report_gen.py
    participant CP as /coach-planner

    User->>DR: 今天的 Brain Dump
    DR->>DL: 写入 YYYY-MM-DD.md<br/>(energy, spend, mental_load 等)

    Note over COROS,FIT: make sync-coros (每日拉取昨日数据)
    User->>SC: make sync-coros
    SC->>COROS: fetch_sleep / fetch_daily_records / fetch_activities
    COROS-->>SC: sleep + readiness + training + activities
    SC->>FIT: 写入 YYYY-MM-DD.yaml
    SC->>PC: 触发 patch
    PC->>DL: 更新 sleep/readiness/training/activities frontmatter

    User->>RG: make check
    RG->>DL: 读取近期日志
    RG-->>User: ⚠️ 告警列表 (Warning/Critical/Breaker)

    alt 有告警
        User->>CP: 今天怎么排？
        CP->>DL: 读取近3天日志
        CP-->>User: 调整后时间表
    end
```

---

## 3. Weekly Loop

每周日的回顾与下周排期双循环。

```mermaid
graph LR
    subgraph Collect ["① 数据聚合"]
        D["7× YYYY-MM-DD.md\n+ data/fitness/"] --> WS["weekly_synthesis.py"]
        WS --> PROMPT["weekly_report_prompt.md\n聚合摘要"]
    end

    subgraph Review ["② 周度回顾 (向后看)"]
        PROMPT --> WR["/weekly-review"]
        WR --> SCORE["四维评分\nOutput·Health·Mental·Habits"]
        SCORE --> DIAG["诊断报告\n+ WoW 趋势对比"]
        DIAG --> OBJ["P0/P1/P2 目标\n+ 执行约束"]
        OBJ --> RPT["data/reports/W##.md"]
    end

    subgraph Plan ["③ 下周排期 (向前看)"]
        RPT --> CP["/coach-planner"]
        CP --> TT["下周时间表\n(周一~周日时间块)"]
    end

    TT --> User((👤 User))

    style Collect fill:#EEF6FF,stroke:#4A90D9
    style Review fill:#FFF3E0,stroke:#F5A623
    style Plan fill:#F0FFF0,stroke:#50C878
```

---

## 4. Data Layer

```mermaid
erDiagram
    DAILY_LOG {
        string date PK "YYYY-MM-DD"
        float energy_level
        float deep_work_hours
        float caffeine_cutoff
        int mental_load
        array daily_spend
        object sleep "COROS auto"
        object readiness "COROS auto"
        object training "COROS auto"
        array activities "COROS auto"
        object body "manual"
    }

    FITNESS_YAML {
        string date PK "YYYY-MM-DD"
        object sleep "duration/phases/HR"
        object readiness "HRV/RHR/load_ratio"
        object training "today_load/VO2max/LTHR"
        array activities "sport/duration/HR/load"
    }

    WEEKLY_REPORT {
        string week_id PK "W## YYYY"
        int output_score "max 40"
        int health_score "max 30"
        int mental_score "max 20"
        int habits_score "max 10"
        int total_score "max 100"
        array p0_objectives
        array p1_objectives
        array p2_objectives
        object wow_delta "week-over-week"
    }

    PORTFOLIO {
        string ticker PK
        string market "Bursa/US"
        float shares
        float avg_cost
        string category
    }

    THRESHOLDS {
        float sleep_baseline "7.5h"
        float sleep_debt_l1 "5h"
        float sleep_debt_l2 "8h"
        float energy_warning "5"
        float energy_critical "4"
        float weekly_spend_alert "120 MYR"
        float caffeine_cutoff "14:00"
    }

    DAILY_LOG ||--|| FITNESS_YAML : "patched by sync_coros"
    DAILY_LOG }|--|| THRESHOLDS : "evaluated against"
    DAILY_LOG }o--o{ WEEKLY_REPORT : "aggregated into"
    PORTFOLIO }|--|| THRESHOLDS : "spend rules"
```

---

## 5. COROS Sync Pipeline

```mermaid
flowchart LR
    subgraph External ["外部"]
        API["COROS API\nteamapi.coros.com\n(us region)"]
    end

    subgraph Auth ["认证"]
        ENV[".env\nCOROS_EMAIL\nCOROS_PASSWORD\nCOROS_REGION=us"]
        LOGIN["coros_api.try_auto_login()"]
        ENV --> LOGIN
    end

    subgraph Fetch ["并发拉取"]
        direction TB
        F1["fetch_sleep(auth, day)"]
        F2["fetch_daily_records(auth, day)"]
        F3["fetch_activities(auth, day)"]
    end

    subgraph Write ["写入"]
        YAML["data/fitness/YYYY-MM-DD.yaml\n(sleep + readiness + training + activities)"]
        PATCH["patch_coros.py\n更新日志 frontmatter"]
        MD["data/daily/YYYY-MM-DD.md\nsleep/readiness/training/activities 块"]
    end

    LOGIN --> API
    API --> F1 & F2 & F3
    F1 & F2 & F3 --> YAML
    YAML --> PATCH --> MD
```

---

## 6. Circuit Breaker State Machine

```mermaid
stateDiagram-v2
    direction LR

    [*] --> OK

    OK --> Warning: 单指标越线
    Warning --> OK: 指标恢复

    Warning --> Critical: 多指标恶化
    Critical --> Warning: 部分恢复

    Critical --> Breaker: 级联触发
    Breaker --> Critical: 主指标改善

    state OK {
        note: energy≥6, sleep_debt<5h\nspend正常, 无连续 Poor
    }

    state Warning {
        note: deep_work<4h\nenergy=5\ncaffeine>14:00\nPoor Sleep ×1
    }

    state Critical {
        note: energy<4\nsleep<6.5h\nsleep_debt≥10h\nmental_load≥7
    }

    state Breaker {
        SleepCritical: Sleep Critical\nsleep<6.5h → Deload 全禁训
        DebtL1: Sleep Debt L1\n≥5h → Zone2 限速
        DebtL2: Sleep Debt L2\n>8h → 步行 only
        EnergyCollapse: Energy Collapse\n<4 → DW cap 2h
        MentalOverload: Mental Overload\n≥7 → 单任务模式
        PoorStreak: Poor Sleep ×2\n→ System Offline
        HRVAlert: HRV<30\n→ 禁高强度
    }
```

---

## 7. Agent Skill Responsibilities

```mermaid
graph TD
    subgraph Backward ["← 向后看 (Diagnostic)"]
        WR["/weekly-review\n4D评分 + WoW趋势\n+ P0/P1/P2目标"]
    end

    subgraph Forward ["向前看 (Action) →"]
        CP["/coach-planner\n当日/当周/下周时间表\n+ 实时决策支持"]
    end

    subgraph Specialists ["专项 Agents"]
        DR["/daily-report\nBrain Dump → 结构化日志"]
        WM["/wealth-manager\n投资组合 + 净资产分析"]
        LA["/learning-agent\n技能雷达 + 学习规划"]
        GC["/git-commit\nConventional Commits"]
        SC["/skill-creator\n技能创建 + 评测"]
    end

    LOGS["7× daily logs\n+ fitness yamls"] --> WR
    WR -- "P0/P1/P2 + 约束" --> CP
    WR -- "诊断报告" --> REPORT["data/reports/"]

    CP -- "时间块排期" --> SCHED["明日/本周计划"]
    CP -. "读取近期日志" .-> LOGS
    CP -. "读取上周目标" .-> REPORT

    style Backward fill:#FFF3E0,stroke:#F5A623
    style Forward fill:#F0FFF0,stroke:#50C878
    style Specialists fill:#EEF6FF,stroke:#4A90D9
```
