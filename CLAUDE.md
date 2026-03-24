# Personal-OS — Claude 协作规范

## 项目概述
个人管理系统，通过结构化日志 + AI Agent 实现数据驱动的自我管理。核心闭环：每日记录 → 逻辑引擎告警 → 周度综合分析 → 下周排期。

## 目录结构
```
/config/          — 系统阈值与配置 (thresholds.yaml)
/daily/           — 每日工程师日志 (YYYY-MM-DD.md)
/templates/       — 空白模板文件
/scripts/         — 自动化脚本 (Python 3)
/prompts/         — AI Agent 系统提示词
/reports/         — 生成的周报存档
/user_profile.md  — 全局用户画像 (作息/饮食/锻炼偏好)
```

## 关键约定
- 每日日志文件名格式: `YYYY-MM-DD.md`
- YAML frontmatter 必须包含完整字段集 (见 templates/daily.md)
- 所有阈值从 `config/thresholds.yaml` 读取，脚本中禁止硬编码魔法数字
- 脚本使用 Python 3，依赖: PyYAML
- 输出全量符合 CommonMark 标准

## 常用命令
- `make today` — 生成今天的日志模板
- `make check` — 运行逻辑引擎检查所有日志
- `make weekly` — 聚合本周数据，生成周报 prompt
- `make report` — 一键生成完整周报 (聚合 + 调用 AI)

## AI Agent 协作须知
- 生成排期时必须参考 `user_profile.md` 中的作息/饮食偏好
- 评分框架使用四维度权重 (产出40/健康30/心智20/习惯10)
- 日志风格: 工程师视角，使用 `[Status: OK/Warning/Critical]` 标记
- 中文为主，技术术语保留英文原文
