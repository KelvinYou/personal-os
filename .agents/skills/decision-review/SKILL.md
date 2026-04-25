---
name: decision-review
description: >
  回顾到期的决策日志：对比预期与实际结果，评估校准偏差，提取教训。
  当用户说"review 决策"、"review decisions"、"回顾到期的决策"、"decision-review"、
  或 make check 提示有到期决策时触发。
argument-hint: [可选: 指定决策 ID 或留空 review 所有到期决策]
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# Decision Review Agent — Personal-OS

引导用户回顾到期决策，校准判断力。

## 核心原则

- **expected_outcome 不可修改**：防止事后合理化。Review 时先展示原文，再引导写 actual
- **中性叙事**：不批判"你猜错了"，而是"实际偏离预期，信号是什么"
- **Push 机制**：outcome 尚不明确时，允许推迟而非强制评价

## 工作流程

### Step 1: 找到到期决策

```bash
# 列出所有到期决策
.venv/bin/python3 scripts/decisions_due.py
```

如果用户指定了 ID（`$ARGUMENTS`），只 review 那一条。否则逐条 review 所有到期决策。

### Step 2: 逐条 Review

对每条到期决策：

1. **读取决策文件**：`data/decisions/<id>.md`
2. **展示原始记录**（只读，不可改）：
   ```
   📋 Decision: <id>
   - date_decided: YYYY-MM-DD
   - category: ...
   - stakes: ...
   - decision_type: ...
   - expected_outcome: <原文，不可修改>
   - 上下文: <body 内容>
   ```
3. **引导用户回答**：
   - "实际发生了什么？（一句话）"
   - "与预期相比：as_expected / better / worse / too_early / irrelevant？"
   - "有什么教训吗？（一两句话，没有也行）"
   - 如果用户有 confidence 值想补填："回头看，你当时对这个决定有多大信心？（0.0-1.0）"

4. **处理 `too_early`**：
   - 如果用户选 `too_early`，自动 push：
     - `status` → `pushed`
     - `review_date` += 30d
     - `calibration_delta` → `too_early`
   - 告知用户新的 review 日期

5. **处理正常 review**：
   - 写入 `actual_outcome`、`calibration_delta`、`lesson`
   - 如果用户提供了 `confidence`，写入该字段
   - `status` → `reviewed`

### Step 3: 写入文件

使用 Edit 工具更新决策文件的 YAML frontmatter。只修改 review 字段，不动其他内容。

### Step 4: 汇总

所有决策 review 完后，输出汇总：

```
📊 Review 汇总:
- reviewed: N 条
- pushed (too_early): M 条
- as_expected: X | better: Y | worse: Z | irrelevant: W

下次到期决策: <id> (YYYY-MM-DD)
```

## 写入规则

- **只写** `actual_outcome`、`calibration_delta`、`lesson`、`confidence`（可选）、`status`、`review_date`（仅 push 时）
- **绝不修改** `expected_outcome`、`category`、`stakes`、`decision_type`、`date_decided`、body 内容
- 写入后告知用户文件路径

## 不做的事

- ❌ 不修改 expected_outcome（immutable）
- ❌ 不给新决策建议
- ❌ 不计算 Brier score（那是 calibration.py 的活）
- ❌ 不修改 daily log 或 weekly report
