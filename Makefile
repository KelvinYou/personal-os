# Personal-OS Makefile
# 一键自动化入口：降低每日/每周执行摩擦

PYTHON := .venv/bin/python3
DAILY_DIR := data/daily
SCRIPTS_DIR := scripts
TEMPLATES_DIR := templates
TODAY := $(shell date +%Y-%m-%d)

.PHONY: archive sync-protocol setup setup-private doctor doctor-web test today daily check weekly sync-coros report lint migrate decisions-due decision-new calibration quarterly wealth web help

## 建立 .venv 并安装依赖 (public repo 即可跑)
setup:
	@python3 -m venv .venv
	@.venv/bin/pip install --quiet --upgrade pip
	@.venv/bin/pip install --quiet -r requirements.txt
	@echo "[Status: OK] .venv 就位。下一步: make doctor"

## checkout private data submodule (需 personal-os-data 权限)
## 注意: 本机 .git/config 有 submodule.data.update=none（.gitmodules 里没有），
## 直接 git submodule update --init data 只会输出 Skipping。这里显式覆盖，
## 且只作用于本次命令，不写回 .git/config。
setup-private:
	@git -c submodule.data.update=checkout submodule update --init data
	@echo "[Status: OK] data submodule 已 checkout。"

## 环境自检 (区分 error / expected / warning)
doctor:
	@python3 $(SCRIPTS_DIR)/doctor.py

## 同上，但把 web 依赖缺失视为 error (给 make web 用)
doctor-web:
	@python3 $(SCRIPTS_DIR)/doctor.py --web

## 跑 Python 测试 + web typecheck
test:
	@$(PYTHON) -m unittest discover -s tests -t . -v
	@if [ -d web/node_modules ]; then \
		cd web && npm run --silent typecheck && echo "[Status: OK] web typecheck 通过"; \
	else \
		echo "[Status: Warning] 跳过 web typecheck — web/node_modules 缺失 (cd web && npm i)"; \
	fi

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

## 把某周 delta 的 calendar.yaml sidecar 推到 Google Calendar (一次性事件)
## 用法: make sync-calendar 或 make sync-calendar WEEK=2026-w31
sync-calendar:
	@$(PYTHON) $(SCRIPTS_DIR)/sync_calendar.py $(if $(WEEK),--week $(WEEK),)

## 把 standard_week.yaml 的常驻锚点推成周期性事件 (建一次就一直重复)
## 无提醒 + 标记 Free；推到独立日历 Personal-OS，可在侧边栏单独开关
## 用法: make sync-protocol DRY=1 (预览) 或 make sync-protocol (真推)
sync-protocol:
	@$(PYTHON) $(SCRIPTS_DIR)/sync_calendar.py --protocol $(if $(DRY),--dry-run,)

## 归档冷日志 + 清理 COROS 暂存 (dry-run 默认；APPLY=1 真写)
## 90 天外的 daily 折叠成周行，30 天外已 patch 的 fitness 直接删
## 用法: make archive 或 make archive APPLY=1 HOT=120
archive:
	@$(PYTHON) $(SCRIPTS_DIR)/archive.py $(if $(APPLY),--apply,) \
		$(if $(HOT),--hot-days $(HOT),) $(if $(FITNESS),--fitness-days $(FITNESS),)

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

## Tracked Assets 监控: 现金/到期/利率 + 股票估值 (NAV 计价产品仍不含)
## 用法: make wealth 或 make wealth DATE=2026-09-01 (预演到期)
wealth:
	@if [ ! -x $(PYTHON) ] || [ ! -f data/finance/savings.yaml ]; then \
		echo "[Status: Critical] wealth 前置条件不满足，跑 make doctor 看具体是哪一项："; \
		$(MAKE) --no-print-directory doctor; exit 1; \
	fi
	@$(PYTHON) $(SCRIPTS_DIR)/wealth_check.py $(if $(DATE),--date $(DATE),) $(if $(JSON),--json,)

## 启动本地理财仪表盘 (localhost only，不部署)
web:
	@$(MAKE) --no-print-directory doctor-web || exit 1
	@cd web && npm run dev

## 决策校准分析 (Brier score + 分布)
calibration:
	@$(PYTHON) $(SCRIPTS_DIR)/calibration.py

## 季度身份审计 (需 ≥ 12 周日志)
## 用法: make quarterly 或 make quarterly QUARTER=2026-Q1
quarterly:
	@echo "[Identity Audit] Run: /identity-audit $(if $(QUARTER),$(QUARTER),)"

## 完整流程: lint + 检查 + 聚合
report: lint check weekly
	@echo ""
	@echo "[Done] Lint + logic check + weekly synthesis complete."
	@echo "[Next] Paste weekly_report_prompt.md to Claude for final analysis."

## 显示帮助
help:
	@echo "Personal-OS Commands:"
	@echo "  make setup              — 建立 .venv 并安装 requirements.txt"
	@echo "  make setup-private      — checkout private data submodule (需权限)"
	@echo "  make doctor             — 环境自检 (error / expected / warning)"
	@echo "  make test               — Python 测试 + web typecheck"
	@echo "  make today              — 生成今天的日志模板"
	@echo "  make daily DATE=...     — 生成指定日期的日志模板"
	@echo "  make lint               — 校验所有日志的 frontmatter schema"
	@echo "  make check              — 运行逻辑引擎告警检查"
	@echo "  make weekly             — 聚合本周数据 (可选: DATE=2026-03-22)"
	@echo "  make sync-coros         — 拉取昨日 COROS 数据 (可选: DATE=...)"
	@echo "  make sync-calendar      — 推送 timetable calendar.yaml 到 Google Calendar (可选: WEEK=...)"
	@echo "  make sync-protocol      — 推常驻周锚点到 Calendar (DRY=1 预览)"
	@echo "  make archive            — 归档冷日志 + 清理 COROS 暂存 (APPLY=1 真写)"
	@echo "  make migrate            — dry-run schema 迁移 (APPLY=1 真写)"
	@echo "  make report             — 一键完整流程 (lint + check + weekly)"
	@echo "  make decisions-due      — 列出到期待 review 的决策"
	@echo "  make decision-new SLUG= — 创建新决策条目"
	@echo "  make calibration        — 决策校准分析 (Brier score)"
	@echo "  make wealth             — Tracked Assets: 现金/到期/股票估值 (可选: DATE=... / JSON=1)"
	@echo "  make web                — 启动本地理财仪表盘 (localhost)"
	@echo "  make quarterly          — 季度身份审计 (可选: QUARTER=2026-Q1)"
	@echo "  make help               — 显示本帮助"
