---
name: daily-report
description: 将用户的 Brain Dump（自然语言碎碎念）转化为符合 Personal-OS 规范的结构化每日复盘报告。在用户描述今天做了什么、花了多少钱、睡眠情况等时使用。
argument-hint: [brain-dump text]
allowed-tools: Read, Write, Grep, Glob
---

## Role: Daily Report Agent

将用户输入的自然语言 Brain Dump 转化为 Personal-OS 规范的结构化日志。

## 工作流程

1. **读取模板**: 先读取 `templates/daily.md` 获取最新的 YAML 字段结构。
2. **读取用户画像**: 读取 `data/user_profile.md` 了解用户的作息/饮食偏好，辅助判断。
3. **读取食材单价**: 读取记忆中的食材单价信息，用于估算自炊成本。
4. **提取元数据**: 从 Brain Dump 中提取所有 YAML 字段。
5. **生成日志**: 输出符合规范的完整日志文件。

## Brain Dump 输入

$ARGUMENTS

## 提取规则

### 核心原则：只记例外 (Exception-based)

**Brain Dump 没提到的字段就留空，不要推断、不要回填、不要为了「填满」而编。**

留空 = 按 `config/thresholds.yaml` 的 `logging_defaults` 基线执行，评分时自动兜底，不扣分。
这是设计好的行为，不是数据缺失。真正的失败模式是反过来的：2026-08-09 那份日志被回填成
`deep_work_hours: 0` + `adherence: ✅`，是 agent 猜的，既污染了数据集又和基线规则自相矛盾。
**猜出来的值比空值有害得多** —— 空值系统知道该兜底，猜值系统会当成实测。

### YAML Metadata

只在 Brain Dump 里**实际提到**时才填：

- `energy_level`: (1-10) 用户描述了精力/情绪才打分。没提 → 留空（基线 7）
- `deep_work_hours`: (float) 用户明确说了时长才填。没提 → 留空（基线：工作日 8 / 周末 0）
- `mental_load`: (1-7) 用户描述了压力才填。没提 → 留空（基线 3）
- `caffeine_cutoff`: (HH:MM) **只在超过 14:00 时填**。正常/没提 → 留空（基线 14:00 合规）
- `adherence.timetable`: **只在偏离 `data/protocol/standard_week.md` 时填** ⚠️ 或 🔴，并补一行
  `deviation_note` 根因。按计划执行或没提 → 留空（基线 ✅）
- `primary_blocker`: **只在当天真有 incident 时写一行**。日常牢骚（累、没睡好）不算 —— 那些
  COROS 数据已经记录了。写进来会让归档脚本误判为需要保留原文的事件日
- `daily_spend`: **只在有外食/额外消费时逐项写**。全自炊日留空（基线 RM25.9/天，来源见
  `data/protocol/standard_week.md` §7 采购清单）。有外食就连自炊部分一起按单价估全
- `body.*`: 用户提供了测量数据才填，否则留空。**不参与基线兜底** —— 没测就是没测
- `sleep.*` / `readiness.*` / `training.*` / `activities[]`: **COROS 自动填充**（`make sync-coros`），
  Brain Dump 无需处理；现有文件中已有值不要覆盖。同样不参与兜底

### Markdown Body

**默认整个 body 留空。** 只有下列内容值得写：

- **今日核心产出 (Highlights)**: 当天确实交付了东西才写，分类涵盖公司+个人项目
- **干扰与阻碍**: 只写真 incident，不写日常疲劳
- 计划偏离的根因（`adherence` 是 ⚠️/🔴 时）

平淡的一天就是空 body —— COROS + frontmatter 已经包含 weekly-review 需要的全部数据。

## 缺省处理

**不要因为字段留空就发告警。** 留空是预期状态，`logging_defaults` 会兜底。

旧版会在日志末尾追加 `[Status: Warning] 今日相关数据未检测到，建议手工补充` —— 这句话
已经删除。它把「按基线执行的一天」显示成一个待办事项，正是这套系统要拆掉的那种噪音。

只有真正无法兜底的缺口才提示，且只提示一次：

- COROS 数据缺失（`sleep.duration` 为空）→ `[Status: Warning] COROS 未同步，跑 make sync-coros`
- 用户明确提到了某个数值但你没能解析出来 → 直接问用户，不要猜

## 输出要求

- 严格遵守 `templates/daily.md` 的字段结构，严禁编造数据
- 日期使用今天的日期
- 将完整日志写入 `data/daily/{YYYY-MM-DD}.md`
- 如果该日期文件已存在，先读取现有内容，合并而非覆盖
- 中文为主，技术术语保留英文

## 决策检测钩子

处理完 Brain Dump 后，扫描内容是否包含非琐碎决定的信号（"决定…"、"I decided…"、明确的取舍/选择、放弃了 A 选了 B）。如果检测到，在日志输出末尾追加提示：

```
💡 检测到可能的决策：`<一句话摘要>`。要记到决策日志吗？→ `/decision-log <摘要>`
```

只提示，不自动写决策文件。用户复制粘贴即可触发 `/decision-log`。
