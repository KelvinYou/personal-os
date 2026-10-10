#!/usr/bin/env python3
# flow: weekly-report
"""Weekly Synthesis — 周度数据聚合管道.

Thin glue over scripts/lib/: aggregates a target week, runs the deterministic
base-score computation, fills the prompt file consumed by the weekly-review
skill.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from lib.breakers import evaluate  # noqa: E402
from lib.config import load_thresholds  # noqa: E402
from lib.coros_mcp import CorosSnapshot, load_snapshot  # noqa: E402
from lib.daily_log import DAILY_DIR, iter_all, iter_week, week_bounds  # noqa: E402
from lib.logger import emit_event  # noqa: E402
from lib.metrics import compute_weekly_aggregate, latest_metrics  # noqa: E402
from lib.score import compute_base_score, format_breakdown_md  # noqa: E402


def _read_body(path: Path) -> str:
    content = path.read_text(encoding="utf-8")
    parts = content.split("---", 2)
    if len(parts) < 3:
        return ""
    return parts[2].strip()


def _fmt(value: float | None, digits: int = 1, suffix: str = "") -> str:
    return f"{value:.{digits}f}{suffix}" if value is not None else "unavailable"


def _has_coros_source(day: date, fitness_dir: Path) -> bool:
    path = fitness_dir / f"{day.isoformat()}.yaml"
    if not path.is_file():
        return False
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return any(data.get(k) for k in ("sleep", "readiness", "training", "activities"))


def generate_weekly_synthesis(target_date: date | None = None,
                              coros_snapshot: CorosSnapshot | None = None) -> None:
    cfg = load_thresholds()
    sleep_baseline = cfg.sleep.baseline_hours
    monday = week_bounds(target_date)

    all_logs = list(iter_all())
    manual_days = sum(monday <= log.date <= monday + timedelta(days=6) for log in all_logs)
    if coros_snapshot is not None:
        end = min(monday + timedelta(days=6), coros_snapshot.period_end)
        if not coros_snapshot.period_start <= monday <= end:
            raise ValueError("MCP query must cover the requested week's start")
        all_logs = coros_snapshot.merge(all_logs)
        week_logs = [log for log in all_logs if monday <= log.date <= end]
    else:
        week_logs = list(iter_week(monday))
    if not week_logs:
        print("[Status: Warning] No daily logs found for this week.")
        return

    week_last = end if coros_snapshot is not None else max(l.date for l in week_logs)

    agg = compute_weekly_aggregate(
        week_logs,
        all_logs,
        sleep_baseline,
        cfg.sleep.debt_window_days,
        today=week_last,
        sleep_cfg=cfg.sleep,
    )
    # MCP evidence is authoritative in MCP mode; legacy provenance is offline-only.
    fitness_dir = PROJECT_ROOT / "data" / "fitness"
    logged_sources = {log.date for log in week_logs if log.coros_synced}
    agg.coros_days = sum(
        (monday + timedelta(days=i)) in logged_sources
        or (coros_snapshot is None
            and _has_coros_source(monday + timedelta(days=i), fitness_dir))
        for i in range(7)
    )
    # Breaker eval uses logs up to the week's last day, so historic weeks
    # get the breaker state that was relevant then. Raw logs on purpose:
    # an alarm must fire on evidence, never on a baseline fill.
    logs_up_to_week = [l for l in all_logs if l.date <= week_last]
    metrics = latest_metrics(
        logs_up_to_week,
        sleep_baseline,
        cfg.sleep.debt_window_days,
        sleep_cfg=cfg.sleep,
    )
    if coros_snapshot is not None:
        metrics = coros_snapshot.metrics(logs_up_to_week, cfg, week_last)
    tripped = evaluate(metrics, cfg.circuit_breakers)
    base_score = compute_base_score(agg, week_logs, cfg.scoring,
                                    caffeine_cutoff=cfg.caffeine.cutoff_time)

    # --- Summary ---
    print("=" * 50)
    print("[Status: OK] Weekly Synthesis Complete")
    source_note = (coros_snapshot.summary() if coros_snapshot else
                   "Local recorded evidence only; official COROS MCP was not queried. "
                   "Historical health values do not establish current readiness.")
    print(f"  Evidence       : {source_note}")
    print("=" * 50)
    print(f"  Week of          : {monday.isoformat()}")
    print(f"  Evidence days    : {agg.days_logged}; local daily files: {manual_days}")
    print(f"  Deep Work        : {agg.total_deep_work:.1f}h across {agg.work_days} recorded days" if agg.work_days else "  Deep Work        : unavailable")
    print(f"  Avg Energy       : {_fmt(agg.avg_energy, 1, '/10')}")
    print(f"  Avg Sleep        : {_fmt(agg.avg_sleep, 2, 'h')}")
    print(f"  Avg Deep min     : {_fmt(agg.avg_deep_min, 0)}")
    print(f"  Avg REM min      : {_fmt(agg.avg_rem_min, 0)}")
    print(f"  Avg Awake min    : {_fmt(agg.avg_awake_min, 0)}")
    print(f"  Avg HRV          : {_fmt(agg.avg_hrv, 0, 'ms')}")
    print(f"  Avg tired_rate   : {_fmt(agg.avg_tired_rate)}")
    print(f"  Avg load_ratio   : {_fmt(agg.avg_load_ratio, 2)}")
    print(f"  Poor Sleep days  : {agg.poor_sleep_days} / {agg.sleep_days} observed sleep days" if agg.sleep_days else "  Poor Sleep days  : unavailable")
    print(f"  Rolling 7d debt  : {agg.rolling_7d_sleep_debt:.1f}h observed" if agg.sleep_days else "  Rolling 7d debt  : unavailable")
    print(f"  Weekly debt (display): {agg.total_sleep_debt:.1f}h observed" if agg.sleep_days else "  Weekly debt (display): unavailable")
    print(f"  Training sessions: {agg.training_sessions}")
    print(f"  Weekly load      : {agg.weekly_total_load:.0f}")
    if agg.latest_body:
        print(f"  Body ({agg.latest_body_date}): {agg.latest_body}")
    print(f"  Total Spend      : RM{agg.total_spend:.2f} recorded" if agg.spend_days else "  Total Spend      : unavailable")
    print(f"  Breakers Trip    : {len(tripped)}")
    for tb in tripped:
        print(f"    [TRIPPED] {tb.name}: {tb.metric}={tb.actual}")
    print("-" * 50)
    print(f"  Sources          : COROS {agg.coros_days}d, body {agg.body_days}d, work {agg.work_days}d")
    print("-" * 50)
    print(base_score.summary_line())
    print("=" * 50)

    # --- Prompt assembly ---
    profile_file = PROJECT_ROOT / "data" / "user_profile.md"
    profile_content = profile_file.read_text(encoding="utf-8") if profile_file.exists() else "未找到 data/user_profile.md。"

    # Per-day slices preserve unknown values; no baseline is synthesized.
    logs_compiled: list[str] = []
    for log in week_logs:
        fp = DAILY_DIR / f"{log.date.isoformat()}.md"
        body = _read_body(fp) if fp.exists() else ""
        snippet = body[:500] if body else "(空)"
        meta_dump = yaml.dump(
            log.model_dump(exclude={"date"}, exclude_none=False),
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        ).strip()
        logs_compiled.append(
            f"### {log.date.isoformat()}\n"
            + (f"**MCP tools:** {', '.join(next((r.tools for r in coros_snapshot.records if r.date == log.date), []))}\n"
               if coros_snapshot else "")
            + f"```yaml\n{meta_dump}\n```\n"
            f"**核心摘录：**\n{snippet}...\n"
        )

    sunday = monday + timedelta(days=6)
    lines: list[str] = []
    lines.append("# Weekly Report Input — 本周注入数据")
    lines.append("")
    lines.append("> 本文件由 `scripts/weekly_synthesis.py` 自动生成，供 weekly-review skill 消费。")
    lines.append("> System prompt 由 skill 本身提供；本文件仅含数据。")
    lines.append(f"> Health evidence: {source_note}")
    lines.append("> Scoring policy: telemetry-observed-v1 (2026-09-29 cutover); do not compare historical full scores directly.")
    lines.append("")
    lines.append("## 0. 全局用户画像与偏好 (User Profile)")
    lines.append(profile_content.strip())
    lines.append("")
    lines.append("## 1. 过去 7 天的宏观聚合数据 (Aggregated Metrics)")
    lines.append(f"- 统计周期：{monday.isoformat()} ~ {sunday.isoformat()}")
    lines.append(f"- Evidence days: {agg.days_logged}; local daily files: {manual_days}")
    lines.append(f"- 已记录专注工作：{agg.total_deep_work:.1f} 小时 / {agg.work_days} 个记录日" if agg.work_days else "- 专注工作：未记录")
    lines.append(f"- Source coverage: evidence {agg.days_logged}/7; local daily files {manual_days}; COROS {agg.coros_days}d; body {agg.body_days}d; work {agg.work_days}d")
    lines.append(f"- 平均精力值：{_fmt(agg.avg_energy, 1, '/10')}")
    lines.append(f"- 平均心智负荷：{_fmt(agg.avg_mental_load, 1, '/7')}")
    lines.append("- **睡眠结构 (COROS)**:")
    lines.append(f"  - 平均睡眠时长：{_fmt(agg.avg_sleep, 2, 'h')}")
    lines.append(f"  - 平均深睡：{_fmt(agg.avg_deep_min, 0, ' min')}")
    lines.append(f"  - 平均 REM：{_fmt(agg.avg_rem_min, 0, ' min')}")
    lines.append(f"  - 平均 Awake：{_fmt(agg.avg_awake_min, 0, ' min')}")
    lines.append(f"  - 平均夜间 HRV：{_fmt(agg.avg_hrv, 0, 'ms')}")
    lines.append("- **就绪度 (Readiness)**:")
    lines.append(f"  - 平均 tired_rate：{_fmt(agg.avg_tired_rate)}")
    lines.append(f"  - 平均 load_ratio：{_fmt(agg.avg_load_ratio, 2)}")
    lines.append("- **训练 (Training)**:")
    activity_days = (sum(monday <= r.date <= week_last and "activities" in r.model_fields_set
                         for r in coros_snapshot.records) if coros_snapshot else None)
    load_days = sum(log.training.today_load is not None for log in week_logs)
    lines.append(f"  - Recorded training sessions: {agg.training_sessions}" +
                 (f" across {activity_days} queried activity days; unqueried days unknown"
                  if activity_days is not None else " (local records only)"))
    lines.append(f"  - Recorded training load: {agg.weekly_total_load:.0f} across {load_days} observed days"
                 if load_days else "  - Training load: unavailable")
    lines.append(f"- Poor Sleep：{agg.poor_sleep_days} / {agg.sleep_days} 个已观测睡眠日" if agg.sleep_days else "- Poor Sleep：未记录睡眠")
    lines.append(f"- 已观测睡眠负债 (display): {agg.total_sleep_debt:.1f} 小时" if agg.sleep_days else "- 睡眠负债：不可用")
    lines.append(f"- 7 日滚动睡眠负债 (breaker input, observed): {agg.rolling_7d_sleep_debt:.1f} 小时" if agg.sleep_days else "- 7 日滚动睡眠负债：不可用")
    lines.append(f"- 连续 Poor 睡眠天数：{agg.consecutive_poor} 天")
    lines.append(f"- 咖啡因截断时间记录：{', '.join(agg.caffeine_cutoffs) if agg.caffeine_cutoffs else '暂无数据'}")
    lines.append("- 本周主要效率阻碍 (Primary Blockers):")
    if agg.primary_blockers:
        for b in agg.primary_blockers:
            lines.append(f"  - {b}")
    else:
        lines.append("  - 暂无明显数据")
    lines.append(f"- 已记录支出：RM{agg.total_spend:.2f}（{agg.spend_days} 个记录日）" if agg.spend_days else "- 支出：未记录")
    lines.append("")

    lines.append("## 2. 🚨 Circuit Breaker 熔断状态 (System Alerts)")
    if tripped:
        for tb in tripped:
            auto = tb.enforcement == "auto"
            tag = "TRIPPED" if auto else "ADVISORY"
            lines.append(
                f"- **[{tag}] {tb.name}**: `{tb.metric}` = {tb.actual} (阈值: {tb.operator} {tb.threshold})"
            )
            lines.append(
                "  - 强制行为限制:" if auto
                else "  - 建议（engine 无法验证/执行，由 agent 判断）:"
            )
            for a in tb.actions:
                lines.append(f"    - {a}")
    else:
        lines.append("- No breaker triggered on observed evidence. Missing measurements are unknown; this is not proof of recovery or a live all-clear.")
    lines.append("")

    lines.append("## 2.5 身体测量快照（手动记录）")
    lb = agg.latest_body or {}
    if lb:
        lines.append(f"- 测量日期：{agg.latest_body_date}")
        for key, value in lb.items():
            lines.append(f"- {key}: {value}")
    else:
        lines.append("- 本周无体成分数据。")
    lines.append("")

    lines.append("## 3. Deterministic Base Score (代码自动计算，AI 只做 bonus/penalty 调整)")
    lines.append("")
    lines.append(format_breakdown_md(base_score))
    lines.append("")
    lines.append("> Blank optional fields are unknown. Only observed criteria receive points; a full /100 requires all criteria.")
    lines.append("")

    # --- Decision Journal summary ---
    from decisions_due import DECISIONS_DIR, _parse_frontmatter, iter_due  # noqa: E402
    total_decisions = 0
    week_decisions = 0
    due_decisions = iter_due()
    if DECISIONS_DIR.is_dir():
        for p in DECISIONS_DIR.glob("*.md"):
            if p.name.startswith("."):
                continue
            total_decisions += 1
            meta = _parse_frontmatter(p)
            if meta:
                dd = meta.get("date_decided")
                if dd:
                    d = dd if isinstance(dd, date) else date.fromisoformat(str(dd))
                    if monday <= d <= sunday:
                        week_decisions += 1
    if total_decisions > 0 or due_decisions:
        lines.append("## 4.5 决策日志快照 (Decision Journal)")
        lines.append(f"- 本周新增决策：{week_decisions} 条")
        lines.append(f"- 决策总数：{total_decisions} 条")
        lines.append(f"- 待 review：{len(due_decisions)} 条")
        if due_decisions:
            nearest = due_decisions[0][1].get("id", "?")
            lines.append(f"- 最近到期：{nearest}")
        lines.append("")

    lines.append("## 5. 每日日志切片采样 (Daily Slices)")
    lines.append("")
    lines.extend(logs_compiled)

    prompt_path = PROJECT_ROOT / "weekly_report_prompt.md"
    prompt_path.write_text("\n".join(lines), encoding="utf-8")

    iso_year, iso_week, _ = monday.isocalendar()
    print(f"\n[Output] Prompt written to {prompt_path}")
    print(f"[Tip] 生成的周报建议存档至 data/reports/{iso_year}-w{iso_week:02d}-weekly-report.md")

    emit_event("weekly_synthesis", {
        "health_source": "coros-official-mcp" if coros_snapshot else "local-records",
        "monday": monday.isoformat(),
        "iso_week": f"{iso_year}-W{iso_week:02d}",
        "days_logged": agg.days_logged,
        "coros_days": agg.coros_days,
        "body_days": agg.body_days,
        "work_days": agg.work_days,
        "tripped_breakers": [tb.name for tb in tripped],
        "observed_score_points": round(base_score.total, 2),
        "full_score_available": base_score.complete,
        "base_score": {
            "output": round(base_score.output.points, 2),
            "health": round(base_score.health.points, 2),
            "mental": round(base_score.mental.points, 2),
            "habits": round(base_score.habits.points, 2),
        },
        "avg_sleep": round(agg.avg_sleep, 2) if agg.avg_sleep is not None else None,
        "avg_hrv": round(agg.avg_hrv, 1) if agg.avg_hrv is not None else None,
        "rolling_7d_sleep_debt": round(agg.rolling_7d_sleep_debt, 2),
        "training_sessions": agg.training_sessions,
    })


def main() -> int:
    parser = argparse.ArgumentParser(description="Weekly Synthesis")
    parser.add_argument("--date", help="Target date (YYYY-MM-DD), defaults to today", default=None)
    parser.add_argument("--coros-input", help="Normalized official MCP JSON, or - for stdin")
    args = parser.parse_args()
    target = date.fromisoformat(args.date) if args.date else None
    snapshot = load_snapshot(args.coros_input) if args.coros_input else None
    generate_weekly_synthesis(target_date=target, coros_snapshot=snapshot)
    return 0


if __name__ == "__main__":
    sys.exit(main())
