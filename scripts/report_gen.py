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


# ---------------------------------------------------------------------------
# 告警规则 —— 每条抽成纯函数。
#
# 抽出来不是为了复用（只有一个调用点），是为了**能测**：`run_checks()` 直接调
# `load_thresholds()` + `iter_all()`，没有注入点，于是整个逻辑引擎长期一条断言都没有。
# 单日规则返回 `str | None`，由调用方按原顺序拼装 —— 保持 per-day 交错的输出顺序不变。
# ---------------------------------------------------------------------------

def deep_work_alert(log, dw_min: float) -> str | None:
    """Rule 1 —— Deep Work 关联性检查。

    `0 < dw` 的下界是有意的：dw=0 是「今天整天没做 deep work」，那是另一回事
    （由排期/adherence 负责），不是「做了但不够」。
    """
    dw = log.deep_work_hours
    if dw is None or not (0 < dw < dw_min):
        return None
    blocker = log.primary_blocker or ""
    reason = f"Blocker: {blocker}" if blocker else f"Energy={log.energy_level}"
    return f"[Warning] {log.date.isoformat()}: Deep Work {dw}h < {dw_min}h. {reason}"


def energy_alert(log, energy_warn: float) -> str | None:
    """Rule 2 —— 精力预警。"""
    if log.energy_level is None or log.energy_level >= energy_warn:
        return None
    return (
        f"[Warning] {log.date.isoformat()}: Energy {log.energy_level}/10 "
        f"below threshold {energy_warn}."
    )


def caffeine_alert(log, late_cutoff: str) -> str | None:
    """Rule 5 —— 咖啡因截断违规。

    只在值确实是 HH:MM 时比较：字符串比较对 "下午两点" 这种自由文本会给出无意义的
    结果，宁可不报也不要报错的。
    """
    cutoff = log.caffeine_cutoff
    if not cutoff:
        return None
    val = str(cutoff).strip()
    if not _HHMM_RE.match(val) or val <= late_cutoff:
        return None
    return (
        f"[Warning] {log.date.isoformat()}: Caffeine cutoff {cutoff} "
        f"exceeds {late_cutoff}. Sleep impact likely."
    )


def log_spend_total(log) -> float:
    """Rule 6 的累加单元 —— 单日已记录消费之和（`amount` 为空的条目跳过）。"""
    return sum(s.amount for s in log.daily_spend if s.amount is not None)


def weekly_spend_alert(total: float, threshold: float) -> str | None:
    """Rule 6 —— 累计消费超阈值。"""
    if total <= threshold:
        return None
    return (
        f"[Warning] Weekly spend RM{total:.2f} exceeds alert threshold RM{threshold:.2f}."
    )


def poor_sleep_streak_alerts(logs, poor_streak: int, sleep_cfg=None) -> list[str]:
    """Rule 4 —— 连续 Poor 睡眠。

    达到阈值后**每一天**都继续告警（不是只在跨过阈值那天报一次）—— 连续第 5 天
    和第 3 天不是同一个严重程度，静默会让它看起来已经缓解。
    """
    alerts: list[str] = []
    count = 0
    for log in sorted(logs, key=lambda l: l.date):
        if derive_poor_sleep(log, sleep_cfg):
            count += 1
            if count >= poor_streak:
                alerts.append(
                    f"[Critical] {log.date}: {count} consecutive Poor sleep days. "
                    f"REST STRONGLY ADVISED."
                )
        else:
            count = 0
    return alerts


def breaker_alerts(tripped) -> list[str]:
    """Rule 3 —— 熔断器渲染。advisory 的 actions 是 prose，换 tag，别伪装成硬约束。"""
    out: list[str] = []
    for tb in tripped:
        tag = "BREAKER" if tb.enforcement == "auto" else "ADVISORY"
        actions_str = " / ".join(tb.actions)
        out.append(
            f"[{tag}] {tb.name}: {tb.metric}={tb.actual} {tb.operator} {tb.threshold} → {actions_str}"
        )
    return out


def adherence_drift_alerts(logs: list, drift_days: int) -> list[str]:
    """Rule 7 — N consecutive ⚠️/🔴 days → timetable 与 reality 系统性偏离，coach-planner 需重排。

    空值语义（有意为之，不要"修"成读 logging_defaults）：
      - `timetable` 留空 = 按 standard_week 执行 = ✅，见 templates/daily.md 与
        `logging_defaults.adherence`。所以留空**打断** streak，与显式 ✅ 同义。
      - 日志文件整天缺失的日子根本不在 `logs` 里，自然跳过 —— 与
        `metrics._consec_poor_up_to` 对「缺日」的处理一致。

    这里刻意**不**走 `lib.defaults` 的兜底填充：defaults 只用于评分，不用于告警
    （见 config/thresholds.yaml `logging_defaults` 注释第 2 条 + DECISIONS §2）。
    代价是本函数硬编码了「留空 ≡ ✅」这个假设，而 `logging_defaults.adherence` 是
    它的声明 owner —— 两者一旦分叉就静默失配，所以由 tests/test_logic_engine.py
    的 parity 测试钉住。
    """
    alerts: list[str] = []
    streak = 0
    start: str | None = None
    for log in sorted(logs, key=lambda l: l.date):
        if log.adherence.timetable in ("⚠️", "🔴"):
            if streak == 0:
                start = log.date.isoformat()
            streak += 1
            if streak == drift_days:
                alerts.append(
                    f"[Warning] {start} → {log.date}: {streak} consecutive adherence drift days. "
                    f"Timetable 与 reality 系统性偏离，下次 coach-planner 排期需调整。"
                )
        else:
            streak = 0
            start = None
    return alerts


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
        # Rule 1 / 2 / 5 —— 单日规则，保持 per-day 交错顺序
        for rule in (
            deep_work_alert(log, dw_min),
            energy_alert(log, energy_warn),
            caffeine_alert(log, late_caffeine),
        ):
            if rule:
                alerts.append(rule)
        total_spend += log_spend_total(log)  # Rule 6 累计

    metrics = latest_metrics(
        logs, sleep_baseline, cfg.sleep.debt_window_days, sleep_cfg=cfg.sleep
    )
    tripped = evaluate(metrics, cfg.circuit_breakers)
    alerts.extend(breaker_alerts(tripped))                                  # Rule 3
    alerts.extend(poor_sleep_streak_alerts(logs, poor_streak, cfg.sleep))   # Rule 4

    # --- Rule 7: Adherence drift (W22+ lightweight log) ---
    alerts.extend(
        adherence_drift_alerts(logs, cfg.logging_defaults.adherence_drift_days)
    )

    if (sp := weekly_spend_alert(total_spend, spend_alert)):                # Rule 6
        alerts.append(sp)

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

    # --- Decision Journal: surface due reviews ---
    from decisions_due import iter_due  # noqa: E402
    due = iter_due()
    if due:
        print("")
        print(f"[Decision Review] {len(due)} decision(s) due for review:")
        for path, meta in due:
            title = meta.get("id", path.stem)
            print(f"  → {title}  (review_date: {meta.get('review_date')})")
        print("  Run: /decision-review")

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
