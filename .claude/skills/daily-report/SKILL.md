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
2. **读取用户画像**: 读取 `user_profile.md` 了解用户的作息/饮食偏好，辅助判断。
3. **读取食材单价**: 读取记忆中的食材单价信息，用于估算自炊成本。
4. **提取元数据**: 从 Brain Dump 中提取所有 YAML 字段。
5. **生成日志**: 输出符合规范的完整日志文件。

## Brain Dump 输入

$ARGUMENTS

## 提取规则

### YAML Metadata
- `energy_level`: (1-10) 根据描述的情绪和精力打分
- `deep_work_hours`: (float) 提取专注工作的小时数
- `sleep.quality`: (Good/Fair/Poor) 根据描述判断
- `sleep.duration`: (float) 睡眠时长（小时）
- `sleep.bedtime` / `sleep.wakeup`: 入睡和醒来时间
- `sleep` 其余字段: 如用户提供了 COROS/手环数据则填入，否则留空
- `caffeine_cutoff`: (HH:MM) 下午最晚一次咖啡因摄入时间
- `primary_blocker`: 一句话概括今日最大效率阻碍
- `daily_spend`: 提取所有消费记录，结构化为 `amount` (RM), `category`, `note`
  - **重要**: 自炊也必须按食材实际单价估算成本，不能写 amount: 0
- `mental_load`: (1-10) 心智负担和压力水平
- `body.*`: 如用户提供体重/体脂等数据则填入，否则留空

### Markdown Body
- **今日核心产出 (Highlights)**: 分类提炼工作内容，涵盖公司+个人项目
- **干扰与阻碍 (Interruptions & Blockers)**: 打断心流或令人不爽的事件
- **明日规划 (Next Steps)**: 未完成或计划中的任务

## 缺省处理

如果 Brain Dump 中缺失重要数据（消费/睡眠时长等），在 YAML 中留空，并在日志末尾附加：

```
[Status: Warning] 提示：今日相关数据（消费/睡眠时长等）未检测到，建议手工补充完善数据库。
```

## 输出要求

- 严格遵守 `templates/daily.md` 的字段结构，严禁编造数据
- 日期使用今天的日期
- 将完整日志写入 `daily/{YYYY-MM-DD}.md`
- 如果该日期文件已存在，先读取现有内容，合并而非覆盖
- 中文为主，技术术语保留英文
