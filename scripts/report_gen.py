#!/usr/bin/env python3
"""
Logic Engine — 逻辑引擎告警检查器
从 config/thresholds.yaml 读取阈值，扫描 /daily 日志并触发规则告警。
"""
import sys
import yaml
from datetime import date, timedelta
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
    energy_warn = config["energy"]["warning_threshold"]
    spend_alert = config["finance"]["weekly_spend_alert"]
    late_caffeine = config["caffeine"]["late_cutoff_time"]

    today = date.today()
    seven_days_ago = today - timedelta(days=7)

    recent_sleep = []              # list[(name, is_poor: bool)]
    total_spend = 0.0
    rolling_7d_debt = 0.0          # 与熔断器 metric 名对齐
    latest_hrv = None              # 最近一天的 readiness.hrv
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

        # --- Rule 3: 睡眠质量追踪 (新 schema: derive Poor from duration/awake/HRV) ---
        sleep_data = meta.get("sleep") or {}
        readiness = meta.get("readiness") or {}
        s_dur = safe_float(sleep_data.get("duration")) if isinstance(sleep_data, dict) else 0.0
        awake_min = safe_float(sleep_data.get("awake_min")) if isinstance(sleep_data, dict) else 0.0
        hrv = safe_float(readiness.get("hrv")) if isinstance(readiness, dict) else 0.0
        hrv_baseline = safe_float(readiness.get("hrv_baseline")) if isinstance(readiness, dict) else 0.0
        # Option P-d: 时长不足是刚性；否则碎片化+低 HRV 组合才算差
        is_poor = (s_dur > 0 and s_dur < 6.5) or (
            awake_min > 40 and hrv > 0 and hrv_baseline > 0 and hrv < hrv_baseline * 0.9
        )
        if s_dur > 0:
            recent_sleep.append((name, is_poor))

        # --- Rule 4: 滚动 7 日睡眠负债 ---
        if s_dur > 0:
            try:
                log_date = date.fromisoformat(name)
                if log_date >= seven_days_ago:
                    debt = sleep_baseline - s_dur
                    if debt > 0:
                        rolling_7d_debt += debt
            except ValueError:
                pass

        # 记录最近一天的 HRV (用于熔断器)
        if hrv > 0:
            latest_hrv = hrv

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
    latest_metrics: dict = {}
    if recent_sleep:
        last_name, _ = recent_sleep[-1]
        last_file = Path(log_dir) / f"{last_name}.md"
        if last_file.exists():
            last_meta = parse_frontmatter(last_file)
            if last_meta:
                last_sleep = last_meta.get("sleep")
                if isinstance(last_sleep, dict):
                    sd_val = safe_float(last_sleep.get("duration"))
                    if sd_val > 0:
                        latest_metrics["sleep_duration"] = sd_val
                energy_val = safe_float(last_meta.get("energy_level"))
                mental_val = safe_float(last_meta.get("mental_load"))
                if energy_val > 0:
                    latest_metrics["energy_level"] = energy_val
                if mental_val > 0:
                    latest_metrics["mental_load"] = mental_val

    # 滚动 / 衍生指标
    latest_metrics["rolling_7d_sleep_debt"] = rolling_7d_debt
    if latest_hrv is not None:
        latest_metrics["hrv"] = latest_hrv

    # 连续 Poor 睡眠日 (new schema derivation)
    consec_poor = 0
    for _, poor in reversed(recent_sleep):
        if poor:
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
        actual = latest_metrics.get(metric_name)
        # 缺数据跳过，不用 0 默认值触发 false positive
        if actual is None:
            continue

        op_fn = ops.get(op_str)
        if op_fn and op_fn(actual, threshold):
            tripped.append(cb)
            actions_str = " / ".join(cb.get("actions", []))
            alerts.append(
                f"[BREAKER] {cb['name']}: {metric_name}={actual} {op_str} {threshold} → {actions_str}"
            )

    # --- 聚合规则检查 ---

    # 连续 Poor 睡眠告警 (new schema: is_poor derived in Rule 3)
    poor_count = 0
    for name, poor in recent_sleep:
        if poor:
            poor_count += 1
            if poor_count >= poor_streak:
                alerts.append(f"[Critical] {name}: {poor_count} consecutive Poor sleep days. REST STRONGLY ADVISED.")
        else:
            poor_count = 0

    # 累计睡眠负债告警 -- 已由 Sleep Debt L1/L2 熔断器覆盖, 不再重复

    # 周度支出告警
    if total_spend > spend_alert:
        alerts.append(f"[Warning] Weekly spend RM{total_spend:.2f} exceeds alert threshold RM{spend_alert:.2f}.")

    # --- 输出 ---
    print("=" * 50)
    print("[Logic Engine] System Check Report")
    print("=" * 50)
    print(f"  Days scanned  : {days}")
    print(f"  7d Sleep debt : {rolling_7d_debt:.1f}h")
    print(f"  Weekly spend  : RM{total_spend:.2f}")
    if latest_hrv is not None:
        print(f"  Latest HRV    : {latest_hrv:.0f}ms")
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
