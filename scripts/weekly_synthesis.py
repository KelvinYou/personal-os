#!/usr/bin/env python3
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


def generate_weekly_synthesis(target_date: date | None = None) -> None:
    cfg = load_thresholds()
    sleep_baseline = cfg.sleep.baseline_hours
    monday = week_bounds(target_date)

    week_logs = list(iter_week(monday))
    if not week_logs:
        print("[Status: Warning] No daily logs found for this week.")
        return

    all_logs = list(iter_all())
    week_last = max(l.date for l in week_logs)
    agg = compute_weekly_aggregate(week_logs, all_logs, sleep_baseline, cfg.sleep.debt_window_days, today=week_last)
    # Breaker eval uses logs up to the week's last day, so historic weeks
    # get the breaker state that was relevant then.
    logs_up_to_week = [l for l in all_logs if l.date <= week_last]
    metrics = latest_metrics(logs_up_to_week, sleep_baseline, cfg.sleep.debt_window_days)
    tripped = evaluate(metrics, cfg.circuit_breakers)
    base_score = compute_base_score(agg, week_logs, cfg.scoring)

    # --- Summary ---
    print("=" * 50)
    print("[Status: OK] Weekly Synthesis Complete")
    print("=" * 50)
    print(f"  Week of          : {monday.isoformat()}")
    print(f"  Days logged      : {agg.days_logged}")
    print(f"  Deep Work        : {agg.total_deep_work:.1f}h")
    print(f"  Avg Energy       : {agg.avg_energy:.1f}/10")
    print(f"  Avg Sleep        : {agg.avg_sleep:.2f}h")
    print(f"  Avg Deep min     : {agg.avg_deep_min:.0f}")
    print(f"  Avg REM min      : {agg.avg_rem_min:.0f}")
    print(f"  Avg Awake min    : {agg.avg_awake_min:.0f}")
    print(f"  Avg HRV          : {agg.avg_hrv:.0f}ms")
    print(f"  Avg tired_rate   : {agg.avg_tired_rate:.1f}")
    print(f"  Avg load_ratio   : {agg.avg_load_ratio:.2f}")
    print(f"  Poor Sleep days  : {agg.poor_sleep_days}")
    print(f"  Rolling 7d debt  : {agg.rolling_7d_sleep_debt:.1f}h")
    print(f"  Weekly debt (display): {agg.total_sleep_debt:.1f}h")
    print(f"  Training sessions: {agg.training_sessions}")
    print(f"  Weekly load      : {agg.weekly_total_load:.0f}")
    if agg.latest_body:
        print(f"  Body Fat         : {agg.latest_body.get('body_fat_pct')}%")
        print(f"  Muscle           : {agg.latest_body.get('muscle_kg')}kg")
    print(f"  Total Spend      : RM{agg.total_spend:.2f}")
    print(f"  Breakers Trip    : {len(tripped)}")
    for tb in tripped:
        print(f"    [TRIPPED] {tb.name}: {tb.metric}={tb.actual}")
    print("-" * 50)
    print(base_score.summary_line())
    print("=" * 50)

    # --- Prompt assembly ---
    profile_file = PROJECT_ROOT / "data" / "user_profile.md"
    profile_content = profile_file.read_text(encoding="utf-8") if profile_file.exists() else "未找到 user_profile.md。"

    # Per-day slices
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
            f"```yaml\n{meta_dump}\n```\n"
            f"**核心摘录：**\n{snippet}...\n"
        )

    sunday = monday + timedelta(days=6)
    lines: list[str] = []
    lines.append("# Weekly Report Input — 本周注入数据")
    lines.append("")
    lines.append("> 本文件由 `scripts/weekly_synthesis.py` 自动生成，供 weekly-review skill 消费。")
    lines.append("> System prompt 由 skill 本身提供；本文件仅含数据。")
    lines.append("")
    lines.append("## 0. 全局用户画像与偏好 (User Profile)")
    lines.append(profile_content.strip())
    lines.append("")
    lines.append("## 1. 过去 7 天的宏观聚合数据 (Aggregated Metrics)")
    lines.append(f"- 统计周期：{monday.isoformat()} ~ {sunday.isoformat()}")
    lines.append(f"- 有效记录天数：{agg.days_logged} 天")
    lines.append(f"- 总专注工作时长：{agg.total_deep_work:.1f} 小时")
    lines.append(f"- 平均精力值：{agg.avg_energy:.1f}/10")
    lines.append(f"- 平均心智负荷：{agg.avg_mental_load:.1f}/10")
    lines.append("- **睡眠结构 (COROS)**:")
    lines.append(f"  - 平均睡眠时长：{agg.avg_sleep:.2f}h")
    lines.append(f"  - 平均深睡：{agg.avg_deep_min:.0f} min")
    lines.append(f"  - 平均 REM：{agg.avg_rem_min:.0f} min")
    lines.append(f"  - 平均 Awake：{agg.avg_awake_min:.0f} min")
    lines.append(f"  - 平均夜间 HRV：{agg.avg_hrv:.0f}ms")
    lines.append("- **就绪度 (Readiness)**:")
    lines.append(f"  - 平均 tired_rate：{agg.avg_tired_rate:.1f}")
    lines.append(f"  - 平均 load_ratio：{agg.avg_load_ratio:.2f}")
    lines.append("- **训练 (Training)**:")
    lines.append(f"  - 本周训练次数：{agg.training_sessions}")
    lines.append(f"  - 本周总训练负荷：{agg.weekly_total_load:.0f}")
    lines.append(f"- Poor Sleep 天数 (Option P-d derivation)：{agg.poor_sleep_days} 天")
    lines.append(f"- 本周累计睡眠负债 (display): {agg.total_sleep_debt:.1f} 小时")
    lines.append(f"- 7 日滚动睡眠负债 (breaker input): {agg.rolling_7d_sleep_debt:.1f} 小时")
    lines.append(f"- 连续 Poor 睡眠天数：{agg.consecutive_poor} 天")
    lines.append(f"- 咖啡因截断时间记录：{', '.join(agg.caffeine_cutoffs) if agg.caffeine_cutoffs else '暂无数据'}")
    lines.append("- 本周主要效率阻碍 (Primary Blockers):")
    if agg.primary_blockers:
        for b in agg.primary_blockers:
            lines.append(f"  - {b}")
    else:
        lines.append("  - 暂无明显数据")
    lines.append(f"- 本周显性支出：RM{agg.total_spend:.2f}")
    lines.append("")

    lines.append("## 2. 🚨 Circuit Breaker 熔断状态 (System Alerts)")
    if tripped:
        for tb in tripped:
            lines.append(
                f"- **[TRIPPED] {tb.name}**: `{tb.metric}` = {tb.actual} (阈值: {tb.operator} {tb.threshold})"
            )
            lines.append("  - 强制行为限制:")
            for a in tb.actions:
                lines.append(f"    - {a}")
    else:
        lines.append("- [Status: OK] 所有熔断器正常，无触发。")
    lines.append("")

    lines.append("## 2.5 身体成分快照 (Zepp Life — 最新测量)")
    lb = agg.latest_body or {}
    if lb and lb.get("body_fat_pct") is not None:
        lines.append(f"- 体脂率: {lb.get('body_fat_pct')}%")
        lines.append(f"- 肌肉量: {lb.get('muscle_kg')}kg")
        lines.append(f"- 内脏脂肪: {lb.get('visceral_fat')}")
        lines.append(f"- BMI: {lb.get('bmi')}")
        lines.append(f"- 水分: {lb.get('water_pct')}%")
        lines.append(f"- 蛋白质: {lb.get('protein_pct')}%")
        lines.append(f"- 骨量: {lb.get('bone_mass_kg')}kg")
        lines.append(f"- 基础代谢: {lb.get('basal_metabolism')}kcal")
    else:
        lines.append("- 本周无体成分数据。")
    lines.append("")

    lines.append("## 3. Deterministic Base Score (代码自动计算，AI 只做 bonus/penalty 调整)")
    lines.append("")
    lines.append(format_breakdown_md(base_score))
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
        "monday": monday.isoformat(),
        "iso_week": f"{iso_year}-W{iso_week:02d}",
        "days_logged": agg.days_logged,
        "tripped_breakers": [tb.name for tb in tripped],
        "base_score_total": round(base_score.total, 2),
        "base_score": {
            "output": round(base_score.output.points, 2),
            "health": round(base_score.health.points, 2),
            "mental": round(base_score.mental.points, 2),
            "habits": round(base_score.habits.points, 2),
        },
        "avg_sleep": round(agg.avg_sleep, 2),
        "avg_hrv": round(agg.avg_hrv, 1),
        "rolling_7d_sleep_debt": round(agg.rolling_7d_sleep_debt, 2),
        "training_sessions": agg.training_sessions,
    })


def main() -> int:
    parser = argparse.ArgumentParser(description="Weekly Synthesis")
    parser.add_argument("--date", help="Target date (YYYY-MM-DD), defaults to today", default=None)
    args = parser.parse_args()
    target = date.fromisoformat(args.date) if args.date else None
    generate_weekly_synthesis(target_date=target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
