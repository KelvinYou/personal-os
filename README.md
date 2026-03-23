# Personal-OS

个人管理系统 Repo，通过结构化指令与逻辑引擎实现数据驱动的自我管理。

## 目录骨架 (Scaffold)
- `/daily/` - 每日复盘与日志记录，采用标准 Markdown 模板并包含 YAML 元数据。
- `/scripts/` - 自动化脚本当文件夹，含用于报告生成和逻辑引擎分析的工具。
- `/prompts/` - 存放与 AI 交互的系统提示词，如 `weekly_review_agent.md`。

## 逻辑引擎 (Logic Engine)
本系统遵循以下规则处理数据输入：

1. **关联性检查 (Correlation Check)**
   - 规则：如果 `deep_work_hours` 低于 4 小时，分析引擎向下检索 `daily_log` 中的 `Interruption` (干扰) 或评估是否由于 `Energy` (精力) 过低导致。
   
2. **财务对账 (Financial Reconciliation)**
   - 规则：自动从每日日志提取 `daily_spend`，计算本周消费累计，并与 20% 储蓄目标进行对比告警。
   
3. **健康预警 (Health Warning)**
   - 规则：如果连续三天 `sleep_quality` 为 `Poor`，系统在复盘时强制触发弹回“休息建议”。

## 输出规范
- 全量符合 CommonMark 标准。
- 分析结果采用标准工程师日志风格：`[Status: OK/Warning/Critical]`。
