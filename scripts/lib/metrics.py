"""Pure aggregations over DailyLog streams.

Single source of truth for:
- rolling_7d_sleep_debt (for breakers)
- total_sleep_debt (for display)
- WeeklyAggregate (avg energy/sleep/hrv, readiness averages, training totals)
- latest_metrics snapshot (for breaker evaluation)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Iterable

from .daily_log import derive_poor_sleep
from .schema import DailyLog


def _avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


@dataclass
class WeeklyAggregate:
    monday: date
    days_logged: int = 0
    total_deep_work: float = 0.0
    avg_energy: float = 0.0
    avg_sleep: float = 0.0
    avg_deep_min: float = 0.0
    avg_rem_min: float = 0.0
    avg_awake_min: float = 0.0
    avg_hrv: float = 0.0
    avg_tired_rate: float = 0.0
    avg_load_ratio: float = 0.0
    avg_mental_load: float = 0.0
    poor_sleep_days: int = 0
    total_sleep_debt: float = 0.0        # display-only ("本周累计负债")
    rolling_7d_sleep_debt: float = 0.0   # for breaker (latest 7 days vs baseline)
    weekly_total_load: float = 0.0
    training_sessions: int = 0
    caffeine_cutoffs: list[str] = field(default_factory=list)
    primary_blockers: list[str] = field(default_factory=list)
    total_spend: float = 0.0
    latest_body: dict | None = None
    consecutive_poor: int = 0


def _append_if_some(xs: list[float], v: float | None) -> None:
    if v is not None:
        xs.append(float(v))


def compute_weekly_aggregate(
    week_logs: Iterable[DailyLog],
    all_logs: Iterable[DailyLog],
    sleep_baseline: float,
    debt_window_days: int = 7,
    today: date | None = None,
) -> WeeklyAggregate:
    """Aggregate week-of-Mon logs + compute rolling-7d debt across `all_logs`.

    `week_logs` drives week-scoped metrics; `all_logs` provides context for
    rolling_7d_sleep_debt (so the breaker uses the most recent 7 days, not
    just what happens to be in the target week).
    """
    week_logs = list(week_logs)
    week_logs.sort(key=lambda l: l.date)
    if not week_logs:
        return WeeklyAggregate(monday=_monday_of(today or date.today()))

    monday = _monday_of(week_logs[0].date)

    energies: list[float] = []
    sleeps: list[float] = []
    deep_mins: list[float] = []
    rem_mins: list[float] = []
    awake_mins: list[float] = []
    hrvs: list[float] = []
    tired: list[float] = []
    load_ratios: list[float] = []
    mental: list[float] = []

    agg = WeeklyAggregate(monday=monday)

    for log in week_logs:
        agg.days_logged += 1
        if log.deep_work_hours is not None:
            agg.total_deep_work += log.deep_work_hours
        _append_if_some(energies, log.energy_level)
        _append_if_some(mental, log.mental_load)
        _append_if_some(sleeps, log.sleep.duration)
        _append_if_some(deep_mins, log.sleep.deep_min)
        _append_if_some(rem_mins, log.sleep.rem_min)
        _append_if_some(awake_mins, log.sleep.awake_min)
        _append_if_some(hrvs, log.readiness.hrv)
        _append_if_some(tired, log.readiness.tired_rate)
        _append_if_some(load_ratios, log.readiness.load_ratio)

        if log.sleep.duration is not None:
            debt = sleep_baseline - log.sleep.duration
            if debt > 0:
                agg.total_sleep_debt += debt
        if derive_poor_sleep(log):
            agg.poor_sleep_days += 1

        if log.training.today_load is not None:
            agg.weekly_total_load += log.training.today_load
        agg.training_sessions += len(log.activities)

        if log.caffeine_cutoff and str(log.caffeine_cutoff).strip():
            agg.caffeine_cutoffs.append(str(log.caffeine_cutoff).strip())
        if log.primary_blocker and str(log.primary_blocker).strip():
            agg.primary_blockers.append(str(log.primary_blocker).strip())

        for s in log.daily_spend:
            if s.amount is not None:
                agg.total_spend += s.amount

        if log.body.body_fat_pct is not None:
            agg.latest_body = log.body.model_dump(exclude_none=False)

    agg.avg_energy = _avg(energies)
    agg.avg_sleep = _avg(sleeps)
    agg.avg_deep_min = _avg(deep_mins)
    agg.avg_rem_min = _avg(rem_mins)
    agg.avg_awake_min = _avg(awake_mins)
    agg.avg_hrv = _avg(hrvs)
    agg.avg_tired_rate = _avg(tired)
    agg.avg_load_ratio = _avg(load_ratios)
    agg.avg_mental_load = _avg(mental)

    ref = today or max((l.date for l in week_logs), default=date.today())
    agg.rolling_7d_sleep_debt = compute_rolling_debt(
        all_logs, sleep_baseline, ref=ref, window_days=debt_window_days
    )
    agg.consecutive_poor = _consec_poor_up_to(all_logs, ref)
    return agg


def compute_rolling_debt(
    logs: Iterable[DailyLog],
    sleep_baseline: float,
    ref: date,
    window_days: int = 7,
) -> float:
    """Sum (baseline - duration) over last N days up to (and including) `ref`, only where debt > 0."""
    lo = ref - timedelta(days=window_days)
    total = 0.0
    for log in logs:
        if log.sleep.duration is None:
            continue
        if lo < log.date <= ref:
            debt = sleep_baseline - log.sleep.duration
            if debt > 0:
                total += debt
    return total


def _consec_poor_up_to(logs: Iterable[DailyLog], ref: date) -> int:
    ordered = sorted((l for l in logs if l.date <= ref), key=lambda l: l.date, reverse=True)
    count = 0
    for log in ordered:
        if derive_poor_sleep(log):
            count += 1
        else:
            break
    return count


def latest_metrics(
    logs: list[DailyLog],
    sleep_baseline: float,
    debt_window_days: int = 7,
) -> dict:
    """Snapshot of metrics used for breaker evaluation.

    For per-day metrics, walks logs in reverse and takes the first non-None
    value — so an empty template day at the head doesn't mask yesterday's data.
    Rolling metrics span the full list. Missing values are omitted; the
    breaker evaluator None-guards separately.
    """
    if not logs:
        return {}
    ordered = sorted(logs, key=lambda l: l.date)
    metrics: dict = {}

    def take(key: str, getter):
        if key in metrics:
            return
        for log in reversed(ordered):
            v = getter(log)
            if v is not None:
                metrics[key] = v
                return

    take("sleep_duration", lambda l: l.sleep.duration)
    take("energy_level", lambda l: l.energy_level)
    take("mental_load", lambda l: l.mental_load)
    take("hrv", lambda l: l.readiness.hrv)
    take("load_ratio", lambda l: l.readiness.load_ratio)
    take("tired_rate", lambda l: l.readiness.tired_rate)

    ref = ordered[-1].date
    metrics["rolling_7d_sleep_debt"] = compute_rolling_debt(
        ordered, sleep_baseline, ref=ref, window_days=debt_window_days
    )
    metrics["consecutive_poor_sleep"] = _consec_poor_up_to(ordered, ref)
    return metrics


def _monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())
