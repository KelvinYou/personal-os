#!/usr/bin/env python3
"""
Weekly Synthesis — 周度数据聚合管道
扫描 /daily 日志，聚合遥测指标，拼装完整的 Weekly Review Agent prompt。
从 config/thresholds.yaml 读取基准值，消除硬编码。
"""
import sys
import yaml
from pathlib import Path
from datetime import date, timedelta

PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "thresholds.yaml"
DAILY_DIR = PROJECT_ROOT / "daily"
PROMPTS_DIR = PROJECT_ROOT / "prompts"
REPORTS_DIR = PROJECT_ROOT / "reports"


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def safe_float(value, default=0.0):
    """防御性转换：空字符串、None 均回退到 default。"""
    if value is None or (isinstance(value, str) and not value.strip()):
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def parse_log(file_path):
    """解析单个日志文件，返回 (metadata_dict, body_text) 或 (None, None)。"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    parts = content.split("---")
    if len(parts) < 3:
        return None, None
    meta = yaml.safe_load(parts[1]) or {}
    body = "---".join(parts[2:]).strip()
    return meta, body


def get_week_files(log_dir, target_date=None):
    """获取目标日期所在周 (Mon-Sun) 的所有日志文件。"""
    target = target_date or date.today()
    # 回退到本周一
    monday = target - timedelta(days=target.weekday())
    week_dates = [monday + timedelta(days=i) for i in range(7)]
    files = []
    for d in week_dates:
        fp = Path(log_dir) / f"{d.isoformat()}.md"
        if fp.exists():
            files.append(fp)
    return files, monday


def generate_weekly_synthesis(log_dir=None, config=None, target_date=None):
    """target_date: 指定任意日期，聚合该日期所在周的数据。默认为今天。"""
    log_dir = log_dir or DAILY_DIR
    config = config or load_config()

    sleep_baseline = config["sleep"]["baseline_hours"]

    files, monday = get_week_files(log_dir, target_date)
    if not files:
        print("[Status: Warning] No daily logs found for this week.")
        return

    # --- 聚合指标 ---
    total_deep_work = 0.0
    energy_levels = []
    sleep_records = []
    total_spend = 0.0
    total_sleep_debt = 0.0
    caffeine_cutoffs = []
    primary_blockers = []
    incidents = 0
    logs_compiled = []

    for fp in sorted(files):
        meta, body = parse_log(fp)
        if meta is None:
            print(f"[Warning] Could not parse {fp.name}, skipping.")
            continue

        # Deep Work
        total_deep_work += safe_float(meta.get("deep_work_hours"))

        # Energy
        e = safe_float(meta.get("energy_level"))
        if e > 0:
            energy_levels.append(e)

        # Sleep
        sq = meta.get("sleep_quality")
        if sq:
            sleep_records.append(sq)
            if sq == "Poor":
                incidents += 1

        # Sleep Debt
        sd = safe_float(meta.get("sleep_duration"))
        if sd > 0:
            debt = sleep_baseline - sd
            if debt > 0:
                total_sleep_debt += debt

        # Caffeine
        cc = meta.get("caffeine_cutoff")
        if cc and str(cc).strip():
            caffeine_cutoffs.append(str(cc).strip())

        # Blockers
        pb = meta.get("primary_blocker")
        if pb and str(pb).strip():
            primary_blockers.append(str(pb).strip())

        # Financials
        spends = meta.get("daily_spend", [])
        if spends:
            for item in spends:
                if isinstance(item, dict):
                    total_spend += safe_float(item.get("amount"))

        # 日志切片（截取前 500 字符降低 Token 负担）
        snippet = body[:500] if body else "(空)"
        logs_compiled.append(
            f"### {fp.stem}\n"
            f"```yaml\n{yaml.dump(meta, allow_unicode=True, default_flow_style=False).strip()}\n```\n"
            f"**核心摘录：**\n{snippet}...\n"
        )

    days_logged = len(logs_compiled)
    avg_energy = sum(energy_levels) / len(energy_levels) if energy_levels else 0

    # --- 打印聚合摘要 ---
    print("=" * 50)
    print("[Status: OK] Weekly Synthesis Complete")
    print("=" * 50)
    print(f"  Week of        : {monday.isoformat()}")
    print(f"  Days logged    : {days_logged}")
    print(f"  Deep Work      : {total_deep_work:.1f}h")
    print(f"  Avg Energy     : {avg_energy:.1f}/10")
    print(f"  Poor Sleep     : {incidents} days")
    print(f"  Sleep Debt     : {total_sleep_debt:.1f}h")
    print(f"  Total Spend    : ${total_spend:.2f}")
    print("=" * 50)

    # --- 拼装 Agent Prompt ---
    # 读取 Weekly Review Agent prompt
    prompt_file = PROMPTS_DIR / "weekly_review_agent.md"
    if prompt_file.exists():
        system_prompt = prompt_file.read_text(encoding="utf-8")
    else:
        print("[Warning] prompts/weekly_review_agent.md not found.")
        system_prompt = "你现在是系统配置的 Weekly Review Agent。\n"

    # 读取 User Profile
    profile_file = PROJECT_ROOT / "user_profile.md"
    if profile_file.exists():
        profile_content = profile_file.read_text(encoding="utf-8")
    else:
        profile_content = "未找到 user_profile.md。"

    prompt_context = f"""{system_prompt}

---------------------------------------------------------

# 以下为本周注入系统数据作为 Input:

## 0. 全局用户画像与偏好 (User Profile)
{profile_content}

## 1. 过去 7 天的宏观聚合数据 (Aggregated Metrics)
- 统计周期：{monday.isoformat()} ~ {(monday + timedelta(days=6)).isoformat()}
- 有效记录天数：{days_logged} 天
- 总专注工作时长：{total_deep_work:.1f} 小时
- 平均精力值：{avg_energy:.1f}/10
- 睡眠红色告警天数：{incidents} 天
- 累计睡眠负债 (Sleep Debt)：{total_sleep_debt:.1f} 小时
- 咖啡因截断时间记录：{', '.join(caffeine_cutoffs) if caffeine_cutoffs else '暂无数据'}
- 本周主要效率阻碍 (Primary Blockers)：
{chr(10).join(['  - ' + b for b in primary_blockers]) if primary_blockers else '  - 暂无明显数据'}
- 总量化显性支出：${total_spend:.2f}

## 2. 每日日志切片采样 (Daily Slices)
{''.join(logs_compiled)}
"""

    # --- 输出到文件 ---
    # 计算 ISO 周号
    iso_year, iso_week, _ = monday.isocalendar()
    output_name = f"weekly_report_prompt.md"
    output_path = PROJECT_ROOT / output_name

    output_path.write_text(prompt_context, encoding="utf-8")
    print(f"\n[Output] Prompt written to {output_path}")
    print("[Action Required] 将该文件内容粘贴给 Claude / ChatGPT 生成最终周报。")
    print(f"[Tip] 生成的周报建议存档至 reports/{iso_year}-w{iso_week:02d}-weekly-report.md")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Weekly Synthesis")
    parser.add_argument("--date", help="Target date (YYYY-MM-DD), defaults to today", default=None)
    args = parser.parse_args()
    target = date.fromisoformat(args.date) if args.date else None
    generate_weekly_synthesis(target_date=target)
