# Personal-OS Makefile
# 一键自动化入口：降低每日/每周执行摩擦

PYTHON := python3
DAILY_DIR := data/daily
SCRIPTS_DIR := scripts
TEMPLATES_DIR := templates
TODAY := $(shell date +%Y-%m-%d)

.PHONY: today check weekly help

## 生成今天的日志模板 (如果不存在)
today:
	@if [ -f $(DAILY_DIR)/$(TODAY).md ]; then \
		echo "[Status: OK] $(TODAY).md already exists."; \
	else \
		sed "s/{{DATE}}/$(TODAY)/g" $(TEMPLATES_DIR)/daily.md > $(DAILY_DIR)/$(TODAY).md; \
		echo "[Status: OK] Created $(DAILY_DIR)/$(TODAY).md"; \
	fi

## 运行逻辑引擎检查 (Logic Engine)
check:
	@$(PYTHON) $(SCRIPTS_DIR)/report_gen.py

## 聚合周度数据，生成 Weekly Review Agent prompt
## 用法: make weekly 或 make weekly DATE=2026-03-22 (回溯指定周)
weekly:
	@$(PYTHON) $(SCRIPTS_DIR)/weekly_synthesis.py $(if $(DATE),--date $(DATE),)

## 完整流程: 检查 + 聚合
report: check weekly
	@echo ""
	@echo "[Done] Logic check + weekly synthesis complete."
	@echo "[Next] Paste weekly_report_prompt.md to Claude for final analysis."

## 显示帮助
help:
	@echo "Personal-OS Commands:"
	@echo "  make today   — 生成今天的日志模板"
	@echo "  make check   — 运行逻辑引擎告警检查"
	@echo "  make weekly  — 聚合本周数据 (可选: make weekly DATE=2026-03-22)"
	@echo "  make report  — 一键完整流程 (check + weekly)"
	@echo "  make help    — 显示本帮助"
