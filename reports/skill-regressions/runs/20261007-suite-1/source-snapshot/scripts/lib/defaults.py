"""Baseline resolution for unfilled manual fields (A-layer, W34+).

Why this exists
---------------
`score.py::_score_dim` scores a missing basis as 0 without shrinking the
denominator. Since ~68 of the 100 rubric points hang off manual frontmatter
fields, "didn't log" was scored identically to "didn't do it" — which made the
daily log a chore you lose points for skipping, and pushed backfilled guesses
into the dataset (2026-08-09's `deep_work_hours: 0`).

`resolve()` flips the semantics: **silence means the baseline was executed.**
Unfilled manual fields are filled from `thresholds.logging_defaults`, and the
fields that were filled that way are reported back so downstream output can
mark them `~` and print a coverage ratio.

Three boundaries (mirrored in the thresholds.yaml comment):

1. Manual fields only. COROS blocks (sleep/readiness/training/activities) and
   `body.*` are never defaulted — those gaps are real, and inventing values
   there would fabricate physiological data.
2. Scoring only, never breakers. `metrics.latest_metrics` keeps reading raw
   logs so an alarm needs evidence; a baseline must not silence one.
3. Only days that have a log file. A missing file is a `days_logged` gap and
   surfaces through coverage, not through synthesized rows.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from .schema import DailyLog, DailySpend, LoggingDefaultsCfg

# Manual fields eligible for baseline resolution, in report order.
MANUAL_FIELDS = (
    "energy_level",
    "mental_load",
    "deep_work_hours",
    "caffeine_cutoff",
    "adherence",
    "daily_spend",
)


@dataclass
class Coverage:
    """How much of the week was actually measured vs. filled from baseline."""

    measured: int = 0
    expected: int = 0
    defaulted: dict[str, int] = field(default_factory=dict)  # field → days defaulted
    days_with_log: int = 0
    days_in_week: int = 7

    @property
    def ratio(self) -> float:
        return self.measured / self.expected if self.expected else 0.0

    def is_low(self, warn_ratio: float) -> bool:
        return self.ratio < warn_ratio

    def summary_line(self) -> str:
        return (
            f"Coverage: {self.measured}/{self.expected} manual fields measured "
            f"({self.ratio * 100:.0f}%) · {self.days_with_log}/{self.days_in_week} days logged"
        )

    def detail_md(self, warn_ratio: float) -> str:
        status = "Low Confidence" if self.is_low(warn_ratio) else "OK"
        lines = [
            "### Logging Coverage",
            "",
            f"[Status: {status}] {self.summary_line()}",
            "",
        ]
        if self.defaulted:
            lines.append("Baseline-filled (marked `~` in the report, **not** penalized):")
            for name in MANUAL_FIELDS:
                n = self.defaulted.get(name)
                if n:
                    lines.append(f"  - {name}: {n} day(s)")
            lines.append("")
        else:
            lines.append("All manual fields measured — no baseline fill.")
            lines.append("")
        return "\n".join(lines)


def _is_weekend(d: date) -> bool:
    return d.weekday() >= 5


def _blank(v) -> bool:
    return v is None or (isinstance(v, str) and not v.strip())


def measured_fields(log: DailyLog) -> list[str]:
    """Manual fields the user actually filled in, by raw inspection.

    Deliberately independent of `resolve()`: coverage must describe what was
    recorded, not what resolution happened to touch. Before `effective_from`
    resolution is a no-op, and counting "not resolved" as "measured" would have
    reported an empty log as 100% covered.
    """
    present: list[str] = []
    if not _blank(log.energy_level):
        present.append("energy_level")
    if not _blank(log.mental_load):
        present.append("mental_load")
    if not _blank(log.deep_work_hours):
        present.append("deep_work_hours")
    if not _blank(log.caffeine_cutoff):
        present.append("caffeine_cutoff")
    if not _blank(log.adherence.timetable):
        present.append("adherence")
    if log.daily_spend:
        present.append("daily_spend")
    return present


def resolve(log: DailyLog, cfg: LoggingDefaultsCfg) -> tuple[DailyLog, list[str]]:
    """Return (resolved copy, names of fields filled from baseline).

    A no-op returning `(log, [])` when the config is disabled or the log predates
    `effective_from` — historical weeks keep their original scores, since this is
    a rubric change and re-scoring them would break week-over-week comparison.
    """
    if not cfg.enabled:
        return log, []
    if cfg.effective_from is not None and log.date < cfg.effective_from:
        return log, []

    patch: dict = {}
    filled: list[str] = []

    if _blank(log.energy_level) and cfg.energy_level is not None:
        patch["energy_level"] = cfg.energy_level
        filled.append("energy_level")

    if _blank(log.mental_load) and cfg.mental_load is not None:
        patch["mental_load"] = cfg.mental_load
        filled.append("mental_load")

    if _blank(log.deep_work_hours):
        dw = cfg.deep_work_hours_weekend if _is_weekend(log.date) else cfg.deep_work_hours
        if dw is not None:
            patch["deep_work_hours"] = dw
            filled.append("deep_work_hours")

    if _blank(log.caffeine_cutoff) and cfg.caffeine_cutoff is not None:
        patch["caffeine_cutoff"] = cfg.caffeine_cutoff
        filled.append("caffeine_cutoff")

    if _blank(log.adherence.timetable) and cfg.adherence is not None:
        patch["adherence"] = log.adherence.model_copy(update={"timetable": cfg.adherence})
        filled.append("adherence")

    if not log.daily_spend and cfg.daily_spend is not None:
        patch["daily_spend"] = [
            DailySpend(
                amount=cfg.daily_spend,
                category="food",
                item="baseline (自炊日均)",
                note="baseline-filled by logging_defaults",
            )
        ]
        filled.append("daily_spend")

    if not patch:
        return log, []
    return log.model_copy(update=patch), filled


def resolve_all(
    logs: list[DailyLog],
    cfg: LoggingDefaultsCfg,
    days_in_week: int = 7,
) -> tuple[list[DailyLog], Coverage]:
    """Resolve a week's logs and tally coverage across them.

    `expected` counts only days that have a log file — a day with no file is a
    logging gap, reported via `days_with_log`, not diluted into the ratio.
    """
    cov = Coverage(days_with_log=len(logs), days_in_week=days_in_week)
    resolved: list[DailyLog] = []
    for log in logs:
        r, filled = resolve(log, cfg)
        resolved.append(r)
        cov.expected += len(MANUAL_FIELDS)
        cov.measured += len(measured_fields(log))
        for name in filled:
            cov.defaulted[name] = cov.defaulted.get(name, 0) + 1
    return resolved, cov
