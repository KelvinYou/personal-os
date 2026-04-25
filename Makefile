# Personal-OS Makefile
# 一键自动化入口：降低每日/每周执行摩擦

PYTHON := .venv/bin/python3
DAILY_DIR := data/daily
SCRIPTS_DIR := scripts
TEMPLATES_DIR := templates
TODAY := $(shell date +%Y-%m-%d)

.PHONY: today daily check weekly sync-coros report lint migrate decisions-due decision-new help

## 生成今天的日志模板 (如果不存在)
today:
	@if [ -f $(DAILY_DIR)/$(TODAY).md ]; then \
		echo "[Status: OK] $(TODAY).md already exists."; \
	else \
		sed "s/{{DATE}}/$(TODAY)/g" $(TEMPLATES_DIR)/daily.md > $(DAILY_DIR)/$(TODAY).md; \
		echo "[Status: OK] Created $(DAILY_DIR)/$(TODAY).md"; \
	fi

## 生成指定日期的日志 (补写历史)
## 用法: make daily DATE=YYYY-MM-DD
daily:
	@if [ -z "$(DATE)" ]; then echo "用法: make daily DATE=YYYY-MM-DD"; exit 1; fi
	@if [ -f $(DAILY_DIR)/$(DATE).md ]; then \
		echo "[Status: OK] $(DATE).md already exists."; \
	else \
		sed "s/{{DATE}}/$(DATE)/g" $(TEMPLATES_DIR)/daily.md > $(DAILY_DIR)/$(DATE).md; \
		echo "[Status: OK] Created $(DAILY_DIR)/$(DATE).md"; \
	fi

## 校验所有日志的 frontmatter schema
lint:
	@$(PYTHON) $(SCRIPTS_DIR)/lint_daily.py

## 运行逻辑引擎检查 (Logic Engine)
check:
	@$(PYTHON) $(SCRIPTS_DIR)/report_gen.py

## 聚合周度数据，生成 Weekly Review Agent prompt
## 用法: make weekly 或 make weekly DATE=2026-03-22 (回溯指定周)
weekly:
	@$(PYTHON) $(SCRIPTS_DIR)/weekly_synthesis.py $(if $(DATE),--date $(DATE),)

## 同步 COROS 手表数据到 data/fitness/
## 用法: make sync-coros 或 make sync-coros DATE=2026-04-21
sync-coros:
	@$(PYTHON) $(SCRIPTS_DIR)/sync_coros.py $(if $(DATE),--date $(DATE),)

## 运行 schema 迁移 (dry-run 默认；APPLY=1 真写)
migrate:
	@$(PYTHON) $(SCRIPTS_DIR)/lib/migrate.py $(if $(APPLY),--apply,)

## 列出今日到期需 review 的决策
decisions-due:
	@$(PYTHON) $(SCRIPTS_DIR)/decisions_due.py

## 创建一条新决策
## 用法: make decision-new SLUG=cancel-gym
decision-new:
	@if [ -z "$(SLUG)" ]; then echo "用法: make decision-new SLUG=<slug>"; exit 1; fi
	@$(PYTHON) $(SCRIPTS_DIR)/decision_new.py --slug $(SLUG)

## 完整流程: lint + 检查 + 聚合
report: lint check weekly
	@echo ""
	@echo "[Done] Lint + logic check + weekly synthesis complete."
	@echo "[Next] Paste weekly_report_prompt.md to Claude for final analysis."

## 显示帮助
help:
	@echo "Personal-OS Commands:"
	@echo "  make today              — 生成今天的日志模板"
	@echo "  make daily DATE=...     — 生成指定日期的日志模板"
	@echo "  make lint               — 校验所有日志的 frontmatter schema"
	@echo "  make check              — 运行逻辑引擎告警检查"
	@echo "  make weekly             — 聚合本周数据 (可选: DATE=2026-03-22)"
	@echo "  make sync-coros         — 拉取昨日 COROS 数据 (可选: DATE=...)"
	@echo "  make migrate            — dry-run schema 迁移 (APPLY=1 真写)"
	@echo "  make report             — 一键完整流程 (lint + check + weekly)"
	@echo "  make decisions-due      — 列出到期待 review 的决策"
	@echo "  make decision-new SLUG= — 创建新决策条目"
	@echo "  make help               — 显示本帮助"
