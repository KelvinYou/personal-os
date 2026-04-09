#!/usr/bin/env python3
"""
Logic Engine — 逻辑引擎告警检查器
从 config/thresholds.yaml 读取阈值，扫描 /daily 日志并触发规则告警。
"""
import sys
import yaml
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "thresholds.yaml"
DAILY_DIR = PROJECT_ROOT / "data" / "daily"


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def parse_frontmatter(file_path):
    """安全解析 YAML frontmatter，返回 metadata dict 或 None。"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    parts = content.split("---")
    if len(parts) < 3:
        return None
    return yaml.safe_load(parts[1]) or {}


def safe_float(value, default=0.0):
    """防御性转换：空字符串、None 均回退到 default。"""
    if value is None or (isinstance(value, str) and not value.strip()):
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def run_checks(log_dir=None, config=None):
    log_dir = log_dir or DAILY_DIR
    config = config or load_config()

    dw_min = config["deep_work"]["minimum_hours"]
    poor_streak = config["sleep"]["poor_streak_alert"]
    sleep_baseline = config["sleep"]["baseline_hours"]
    critical_debt = config["sleep"]["critical_debt_hours"]
    energy_warn = config["energy"]["warning_threshold"]
    spend_alert = config["finance"]["weekly_spend_alert"]
    late_caffeine = config["caffeine"]["late_cutoff_time"]

    recent_sleep = []
    total_spend = 0.0
    total_sleep_debt = 0.0
    alerts = []
    days = 0

    for fp in sorted(Path(log_dir).glob("*.md")):
        meta = parse_frontmatter(fp)
        if meta is None:
            continue
        days += 1
        name = fp.stem  # YYYY-MM-DD

        # --- Rule 1: Deep Work 关联性检查 ---
        dw = safe_float(meta.get("deep_work_hours"))
        energy = safe_float(meta.get("energy_level"))
        if 0 < dw < dw_min:
            blocker = meta.get("primary_blocker", "")
            reason = f"Blocker: {blocker}" if blocker else f"Energy={energy}"
            alerts.append(f"[Warning] {name}: Deep Work {dw}h < {dw_min}h. {reason}")

        # --- Rule 2: 精力预警 ---
        if energy and energy < energy_warn:
            alerts.append(f"[Warning] {name}: Energy {energy}/10 below threshold {energy_warn}.")

        # --- Rule 3: 睡眠质量追踪 (兼容新旧格式) ---
        sleep_data = meta.get("sleep")
        if isinstance(sleep_data, dict):
            sleep_q = sleep_data.get("quality")
            s_dur = safe_float(sleep_data.get("duration"))
        else:
            sleep_q = meta.get("sleep_quality")
            s_dur = safe_float(meta.get("sleep_duration"))
        if sleep_q:
            recent_sleep.append((name, sleep_q))

        # --- Rule 4: 睡眠负债累计 ---
        if s_dur > 0:
            debt = sleep_baseline - s_dur
            if debt > 0:
                total_sleep_debt += debt

        # --- Rule 5: 咖啡因截断违规 ---
        cutoff = meta.get("caffeine_cutoff")
        if cutoff and str(cutoff).strip() and str(cutoff).strip() > late_caffeine:
            alerts.append(f"[Warning] {name}: Caffeine cutoff {cutoff} exceeds {late_caffeine}. Sleep impact likely.")

        # --- Rule 6: 财务累计 ---
        spends = meta.get("daily_spend", [])
        if spends:
            for item in spends:
                if isinstance(item, dict):
                    total_spend += safe_float(item.get("amount"))

    # --- Circuit Breaker 熔断检查 ---
    breakers = config.get("circuit_breakers", [])
    tripped = []

    # 收集最近日志的指标快照用于熔断判定
    latest_metrics = {}
    if recent_sleep:
        last_name, _ = recent_sleep[-1]
        # 从最后一天获取 per-day 指标
        last_file = Path(log_dir) / f"{last_name}.md"
        if last_file.exists():
            last_meta = parse_frontmatter(last_file)
            if last_meta:
                # 兼容新旧 sleep 格式
                last_sleep = last_meta.get("sleep")
                if isinstance(last_sleep, dict):
                    latest_metrics["sleep_duration"] = safe_float(last_sleep.get("duration"))
                else:
                    latest_metrics["sleep_duration"] = safe_float(last_meta.get("sleep_duration"))
                latest_metrics["energy_level"] = safe_float(last_meta.get("energy_level"))
                latest_metrics["mental_load"] = safe_float(last_meta.get("mental_load"))

    # 累计/连续指标
    latest_metrics["cumulative_sleep_debt"] = total_sleep_debt

    consec_poor = 0
    for _, sq in reversed(recent_sleep):
        if sq == "Poor":
            consec_poor += 1
        else:
            break
    latest_metrics["consecutive_poor_sleep"] = consec_poor

    ops = {"<": lambda a, b: a < b, "<=": lambda a, b: a <= b,
           ">": lambda a, b: a > b, ">=": lambda a, b: a >= b,
           "==": lambda a, b: a == b}

    for cb in breakers:
        cond = cb.get("condition", {})
        metric_name = cond.get("metric", "")
        op_str = cond.get("operator", "")
        threshold = safe_float(cond.get("value"))
        actual = latest_metrics.get(metric_name, 0.0)

        op_fn = ops.get(op_str)
        if op_fn and op_fn(actual, threshold):
            tripped.append(cb)
            actions_str = " / ".join(cb.get("actions", []))
            alerts.append(
                f"[BREAKER] {cb['name']}: {metric_name}={actual} {op_str} {threshold} → {actions_str}"
            )

    # --- 聚合规则检查 ---

    # 连续 Poor 睡眠告警
    poor_count = 0
    for name, sq in recent_sleep:
        if sq == "Poor":
            poor_count += 1
            if poor_count >= poor_streak:
                alerts.append(f"[Critical] {name}: {poor_count} consecutive Poor sleep days. REST STRONGLY ADVISED.")
        else:
            poor_count = 0

    # 累计睡眠负债告警
    if total_sleep_debt >= critical_debt:
        alerts.append(f"[Critical] Accumulated sleep debt {total_sleep_debt:.1f}h >= {critical_debt}h. Health defense critically low.")

    # 周度支出告警
    if total_spend > spend_alert:
        alerts.append(f"[Warning] Weekly spend RM{total_spend:.2f} exceeds alert threshold RM{spend_alert:.2f}.")

    # --- 输出 ---
    print("=" * 50)
    print("[Logic Engine] System Check Report")
    print("=" * 50)
    print(f"  Days scanned  : {days}")
    print(f"  Sleep debt    : {total_sleep_debt:.1f}h")
    print(f"  Weekly spend  : RM{total_spend:.2f}")
    print("-" * 50)

    if not alerts:
        print("[Status: OK] All systems nominal. No alerts triggered.")
    else:
        for a in alerts:
            print(f"  {a}")

    print("=" * 50)
    return alerts


if __name__ == "__main__":
    run_checks()
