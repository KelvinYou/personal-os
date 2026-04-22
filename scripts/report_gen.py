#!/usr/bin/env python3
"""Logic Engine — 逻辑引擎告警检查器.

Thin glue over scripts/lib/: loads config, iterates all daily logs via the
lib layer, evaluates circuit breakers on the latest-metrics snapshot, and
prints any alerts.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from lib.breakers import evaluate  # noqa: E402
from lib.config import load_thresholds  # noqa: E402
from lib.daily_log import derive_poor_sleep, iter_all  # noqa: E402
from lib.logger import emit_event  # noqa: E402
from lib.metrics import latest_metrics  # noqa: E402


_HHMM_RE = re.compile(r"^\d{2}:\d{2}$")


def run_checks() -> list[str]:
    cfg = load_thresholds()
    dw_min = cfg.deep_work.minimum_hours
    poor_streak = cfg.sleep.poor_streak_alert
    sleep_baseline = cfg.sleep.baseline_hours
    energy_warn = cfg.energy.warning_threshold
    spend_alert = cfg.finance.weekly_spend_alert
    late_caffeine = cfg.caffeine.late_cutoff_time

    logs = list(iter_all())
    alerts: list[str] = []
    total_spend = 0.0

    for log in logs:
        name = log.date.isoformat()

        # --- Rule 1: Deep Work 关联性检查 ---
        dw = log.deep_work_hours
        if dw is not None and 0 < dw < dw_min:
            blocker = log.primary_blocker or ""
            reason = f"Blocker: {blocker}" if blocker else f"Energy={log.energy_level}"
            alerts.append(f"[Warning] {name}: Deep Work {dw}h < {dw_min}h. {reason}")

        # --- Rule 2: 精力预警 ---
        if log.energy_level is not None and log.energy_level < energy_warn:
            alerts.append(f"[Warning] {name}: Energy {log.energy_level}/10 below threshold {energy_warn}.")

        # --- Rule 5: 咖啡因截断违规 (仅 HH:MM 格式才比较) ---
        cutoff = log.caffeine_cutoff
        if cutoff and _HHMM_RE.match(str(cutoff).strip()) and str(cutoff).strip() > late_caffeine:
            alerts.append(f"[Warning] {name}: Caffeine cutoff {cutoff} exceeds {late_caffeine}. Sleep impact likely.")

        # --- Rule 6: 财务累计 ---
        for spend in log.daily_spend:
            if spend.amount is not None:
                total_spend += spend.amount

    metrics = latest_metrics(logs, sleep_baseline, cfg.sleep.debt_window_days)
    tripped = evaluate(metrics, cfg.circuit_breakers)
    for tb in tripped:
        actions_str = " / ".join(tb.actions)
        alerts.append(
            f"[BREAKER] {tb.name}: {tb.metric}={tb.actual} {tb.operator} {tb.threshold} → {actions_str}"
        )

    # 连续 Poor 睡眠告警 (aggregate rule — emits on every day that crosses the threshold)
    poor_count = 0
    for log in logs:
        if derive_poor_sleep(log):
            poor_count += 1
            if poor_count >= poor_streak:
                alerts.append(
                    f"[Critical] {log.date}: {poor_count} consecutive Poor sleep days. REST STRONGLY ADVISED."
                )
        else:
            poor_count = 0

    if total_spend > spend_alert:
        alerts.append(f"[Warning] Weekly spend RM{total_spend:.2f} exceeds alert threshold RM{spend_alert:.2f}.")

    # --- 输出 ---
    print("=" * 50)
    print("[Logic Engine] System Check Report")
    print("=" * 50)
    print(f"  Days scanned  : {len(logs)}")
    print(f"  7d Sleep debt : {metrics.get('rolling_7d_sleep_debt', 0.0):.1f}h")
    print(f"  Weekly spend  : RM{total_spend:.2f}")
    if "hrv" in metrics:
        print(f"  Latest HRV    : {metrics['hrv']:.0f}ms")
    print("-" * 50)

    if not alerts:
        print("[Status: OK] All systems nominal. No alerts triggered.")
    else:
        for a in alerts:
            print(f"  {a}")

    print("=" * 50)

    emit_event("check_run", {
        "days_scanned": len(logs),
        "alerts": alerts,
        "tripped_breakers": [tb.name for tb in tripped],
        "latest_metrics": metrics,
    })
    return alerts


if __name__ == "__main__":
    run_checks()
