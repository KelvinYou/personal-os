---
name: identity-audit
description: >
  季度身份审计：从行为数据反推"过去一季最重视的 3 件事"，与 user_profile.md 的声明对比。
  当用户说"季度审计"、"identity audit"、"我这个季度活成了什么样"、"quarterly review"、
  "行为 vs 声称"时触发。需要 ≥ 12 周日志数据。
argument-hint: [可选: 指定季度 YYYY-Q# 或留空分析最近一季]
allowed-tools: Read, Bash, Grep, Glob, Write
---

# Identity Audit Agent — Personal-OS

季度一次，从行为数据反推"你实际是谁"，与"你声称的你"对比。

## 核心原则

- **行为数据驱动，不读自述**：不问"你想成为什么人"，只看数据说你是什么人
- **不打分，不批判**：只呈现 gap，让用户自己判断是否需要调整
- **中性叙事**：差距不等于失败——可能是优先级自然演化

## 数据要求

- ≥ 12 周 daily logs（一个完整季度）
- ≥ 3 份 weekly reports
- `user_profile.md`（作为"声称的我"来源）
- 决策日志（如有）

## 工作流程

### Step 1: 收集一季数据

确定季度范围（默认最近 13 周）。读取：

1. **所有 daily logs** in range — 提取 frontmatter
2. **Weekly reports** in range — 提取 P0/P1/P2 目标 + 评分
3. **user_profile.md** — 提取声称的优先级、生活方式、目标
4. **Decision journal** — 提取 category 分布、decision_type 分布
5. **Spend data** — 从 daily_spend 聚合消费类目

### Step 2: 构建"行为反映的我"

从数据推断用户过去一季实际的优先级：

#### A. 时间分配
- deep_work_hours 分布（工作日 vs 周末）
- 训练频率与类型（COROS activities）
- 平均 shutdown 时间（从 caffeine_cutoff / energy 下降推断）

#### B. 消费类目占比
- 按 category 聚合 daily_spend
- 计算占比：食物 / 交通 / 社交 / 学习 / 娱乐 / 投资

#### C. 决策类目分布
- 从 decision journal 提取 category 分布
- career 决定多还是 health 决定多？

#### D. 健康趋势
- HRV baseline 趋势（季初 vs 季末）
- 体重/体脂趋势（如有 body 数据）
- 睡眠时长趋势
- 训练负荷趋势（weekly_total_load）

#### E. 目标完成模式
- 从 weekly reports 提取 P0 完成率
- 哪些领域的目标反复出现但未完成？

### Step 3: 对比与差距分析

读取 `user_profile.md` 中的声明（作息偏好、训练目标、饮食目标、长期方向），与行为数据对比：

- "声称重视健康" vs 实际训练频率/睡眠负债/HRV 趋势
- "声称在控制支出" vs 实际消费模式
- "声称要学习 X" vs deep_work 主题分布（从 highlights 推断）

### Step 4: 输出报告

写入 `data/reports/YYYY-Q#-identity.md`：

```markdown
# Identity Audit: YYYY Q#

## 行为数据反推的前 3 优先级
1. ...（基于时间/金钱/决策投入量排序）
2. ...
3. ...

## user_profile.md 声称的优先级
1. ...
2. ...
3. ...

## Gap 分析
| 维度 | 声称 | 实际 | 差距 |
|------|------|------|------|
| ... | ... | ... | ... |

## 健康趋势
- HRV: 季初 → 季末
- 睡眠: 季初 → 季末
- 体重: (如有数据)

## 消费模式
- 类目占比饼图（文字版）

## 决策模式
- proactive: X% | reactive: Y% | default: Z%
- 主要决策领域: ...

## 不评价、不建议
以上数据仅供参考。差距不等于问题——可能反映优先级的自然演化。
如果差距令你不舒服，考虑更新 user_profile.md 或调整行为。
```

## 不做的事

- ❌ 不打分
- ❌ 不建议改变（只呈现差距）
- ❌ 不读用户的日记/情绪内容——只用结构化数据
- ❌ 不修改 user_profile.md（用户自己决定是否更新）
