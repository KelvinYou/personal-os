"""Agent wait on human for a week: how long agents sat idle waiting for the owner.

The definition lives in lib/office/attention.py `waits`; this module only scans a
bounded date range with the same adapters the live office uses and aggregates.
docs/design/office-attention-radar.md §5.
"""
from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from statistics import median
from zoneinfo import ZoneInfo

from lib.office.attention import timestamp, waits
from lib.office.monitor import Monitor
from lib.schema import OfficeCfg


@dataclass
class DayWaits:
    day: date
    closed: list[float] = field(default_factory=list)
    abandoned: int = 0
    open: int = 0


@dataclass
class WeekWaits:
    monday: date
    days: list[DayWaits]
    sessions: int
    partial_sessions: int
    # Closed wait seconds keyed by sessions in play when the wait opened (see in_play).
    by_play: dict[int, list[float]] = field(default_factory=dict)

    @property
    def closed(self) -> list[float]:
        return [s for d in self.days for s in d.closed]

    def summary(self) -> dict:
        values = sorted(self.closed)
        p90 = _p90(values)
        return {"waits": len(values), "total_minutes": round(sum(values) / 60, 1), "median_minutes": round(median(values) / 60, 1) if values else None,
                "p90_minutes": round(p90 / 60, 1) if p90 is not None else None, "longest_minutes": round(values[-1] / 60, 1) if values else None,
                "abandoned": sum(d.abandoned for d in self.days), "open": sum(d.open for d in self.days), "sessions": self.sessions, "partial_sessions": self.partial_sessions,
                "by_play": [{"in_play": label, "waits": len(v), "median_minutes": round(median(v) / 60, 1), "p90_minutes": round(_p90(sorted(v)) / 60, 1)} for label, v in self.play_buckets()]}

    def play_buckets(self) -> list[tuple[str, list[float]]]:
        """Closed waits grouped 1, 2, 3, 4, 5+ sessions in play; empty buckets omitted."""
        groups: dict[str, list[float]] = {}
        for count in sorted(self.by_play):
            groups.setdefault(str(count) if count < PLAY_TOP else f"{PLAY_TOP}+", []).extend(self.by_play[count])
        return list(groups.items())


PLAY_TOP = 5  # display grouping only: buckets 1..4 and 5+


def _p90(values: list[float]) -> float | None:
    return values[min(len(values) - 1, int(round(0.9 * (len(values) - 1))))] if values else None


def scan_cfg(cfg: OfficeCfg, monday: date, now: datetime) -> OfficeCfg:
    """Full-history budgets for an offline scan; the live limits stay untouched."""
    days = max(1, min(30, (now.date() - monday).days + 2))
    return cfg.model_copy(update={"history_days": days, "max_read_bytes": 16 * 1024 * 1024, "max_segments": 1000, "max_candidates": 2048})


RUNNING = {"active", "pending"}
QUEUED = {"ended", "input"}


Timeline = tuple[list[datetime], list[str]]


def timeline(segments: list[dict]) -> Timeline:
    points = [(t, p["phase"]) for p in segments if (t := timestamp(p.get("at")))]
    return [t for t, _ in points], [p for _, p in points]


def _phase_at(points: Timeline, at: datetime) -> tuple[datetime, str, datetime | None] | None:
    """(start, phase, next change) of the change point covering `at`, or None before the first."""
    starts, phases = points
    index = bisect_right(starts, at) - 1
    if index < 0: return None
    return starts[index], phases[index], starts[index + 1] if index + 1 < len(starts) else None


def in_play(timelines: dict[str, Timeline], at: datetime, cfg: OfficeCfg) -> int:
    """Sessions the owner is juggling at `at`: running agents plus other unanswered waits.

    Running = active/pending with fresh evidence (a final point counts only for
    stale_after_seconds). Queued = what the radar shows as needs-you or review:
    an explicit input request younger than wait_cap_seconds, or an ended turn
    inside review_window_seconds. The session that opened the wait counts itself.
    """
    count = 0
    for points in timelines.values():
        covering = _phase_at(points, at)
        if covering is None: continue
        start, phase, following = covering
        age = (at - start).total_seconds()
        if phase in RUNNING and (following is not None or age <= cfg.stale_after_seconds): count += 1
        elif phase == "input" and age <= cfg.wait_cap_seconds: count += 1
        elif phase == "ended" and age <= cfg.review_window_seconds: count += 1
    return count


def week_waits(codex_sessions: Path, workspace: Path, claude_projects: Path | None, cfg: OfficeCfg, monday: date, tz: ZoneInfo, now: datetime | None = None, signals_dir: Path | None = None) -> WeekWaits:
    now = now or datetime.now(timezone.utc)
    start = datetime.combine(monday, time.min, tz).astimezone(timezone.utc)
    end = start + timedelta(days=7)
    scan = scan_cfg(cfg, monday, now)
    # The cache directory is unused by raw_entries; pass a non-existent path to make that explicit.
    # Hook signals (exact permission waits) are read from the live private directory.
    monitor = Monitor(codex_sessions, workspace, workspace / ".unused-office-cache", scan, claude_projects, signals_dir or workspace / "data" / "runtime" / "ai-office")
    entries = monitor.raw_entries(min(now, end + timedelta(days=1)))
    days = {monday + timedelta(days=i): DayWaits(monday + timedelta(days=i)) for i in range(7)}
    timelines = {entry["id"]: timeline(entry["segments"]) for entry in entries}
    by_play: dict[int, list[float]] = {}
    touched = partial = 0
    for entry in entries:
        found = waits(entry["segments"], scan, start, end)
        if not found: continue
        touched += 1; partial += bool(entry["coverage_gap"])
        for wait in found:
            opened = timestamp(wait["opened"])
            if opened is None: continue
            bucket = days[opened.astimezone(tz).date()]
            if wait["kind"] == "closed":
                bucket.closed.append(wait["seconds"])
                by_play.setdefault(max(1, in_play(timelines, opened, scan)), []).append(wait["seconds"])
            elif wait["kind"] == "abandoned": bucket.abandoned += 1
            else: bucket.open += 1
    return WeekWaits(monday, list(days.values()), touched, partial, by_play)


def markdown(week: WeekWaits, cfg: OfficeCfg) -> list[str]:
    s = week.summary()
    lines = ["## 4.6 Agent wait on human (review latency)", ""]
    if not s["waits"] and not s["abandoned"] and not s["open"]:
        return lines + ["- No agent turns waited for you this week (or no Codex / Claude Code records in this workspace).", ""]
    status = "OK" if (s["median_minutes"] or 0) * 60 <= cfg.wait_median_warning_seconds else "Warning"
    lines += [
        f"- [Status: {status}] {s['waits']} turns waited for you; total {s['total_minutes']} min; median {s['median_minutes']} min (warning above {cfg.wait_median_warning_seconds // 60}); p90 {s['p90_minutes']} min; longest {s['longest_minutes']} min.",
        f"- Abandoned (> {round(cfg.wait_cap_seconds / 3600, 1)} h, excluded from totals): {s['abandoned']}. Sessions left at a final turn (not counted): {s['open']}.",
        f"- Sessions: {s['sessions']} ({s['partial_sessions']} with partial history).",
        f"- Reading: {play_reading(week, cfg)}",
        "",
        "| Day | Waits | Median min | Total min |",
        "|---|---|---|---|",
    ]
    for day in week.days:
        values = day.closed
        lines.append(f"| {day.day.strftime('%a %m-%d')} | {len(values)} | {round(median(values) / 60, 1) if values else '-'} | {round(sum(values) / 60, 1)} |")
    buckets = week.play_buckets()
    if buckets:
        long = cfg.wait_median_warning_seconds
        lines += ["", "Waits by sessions in play when the turn ended (running agents + others in needs-you/review, self included):", "",
                  f"| In play | Waits | Median min | p90 min | Over {long // 60} min |", "|---|---|---|---|---|"]
        for label, values in buckets:
            ordered = sorted(values)
            lines.append(f"| {label} | {len(values)} | {round(median(ordered) / 60, 1)} | {round(_p90(ordered) / 60, 1)} | {round(100 * sum(v > long for v in values) / len(values))}% |")
    lines.append("")
    return lines


def content_review_summary(records: list, start: datetime, end: datetime, now: datetime) -> dict:
    """Content Lab packages waiting for owner review, by when they reached review (lib/content_lab.py review_waits)."""
    from lib.content_lab import review_waits
    closed: list[float] = []; open_ages: list[float] = []; unmeasured = 0
    for record in records:
        for wait in review_waits(record):
            opened = wait["opened"]
            if wait["kind"] == "open":
                # Still waiting is a fact about now: report it only for the week that contains now.
                if start <= now < end: open_ages.append((now - opened).total_seconds())
            elif start <= opened < end:
                if wait["kind"] == "closed": closed.append(wait["seconds"])
                else: unmeasured += 1
    closed.sort()
    hours = lambda seconds: round(seconds / 3600, 1)
    return {"reviewed": len(closed), "median_hours": hours(median(closed)) if closed else None, "longest_hours": hours(closed[-1]) if closed else None,
            "open": len(open_ages), "oldest_open_hours": hours(max(open_ages)) if open_ages else None, "unmeasured": unmeasured}


def content_review_markdown(summary: dict | None) -> list[str]:
    """One line under §4.6: the owner is the reviewer for content, too. None = posts root unavailable."""
    if summary is None:
        return ["- Content Lab review: private posts are unavailable; not measured.", ""]
    if not any(summary[k] for k in ("reviewed", "open", "unmeasured")):
        return ["- Content Lab review: no package reached review this week.", ""]
    parts = [f"{summary['reviewed']} reviewed" + (f", median {summary['median_hours']} h, longest {summary['longest_hours']} h" if summary["reviewed"] else "")]
    if summary["open"]: parts.append(f"{summary['open']} still waiting (oldest {summary['oldest_open_hours']} h)")
    if summary["unmeasured"]: parts.append(f"{summary['unmeasured']} without a recorded review time")
    return [f"- Content Lab review (package ready → your decision): {'; '.join(parts)}.", ""]


def content_review_week(posts: Path, monday: date, tz: ZoneInfo, now: datetime | None = None) -> dict | None:
    """Read the private posts root for one week; None when it is unavailable."""
    from lib.content_lab import read_collection
    now = now or datetime.now(timezone.utc)
    start = datetime.combine(monday, time.min, tz).astimezone(timezone.utc)
    try:
        collection, _errors = read_collection(posts)
    except (OSError, ValueError):
        return None
    return content_review_summary([item.record for item in collection.items if item.record], start, start + timedelta(days=7), now)


def play_reading(week: WeekWaits, cfg: OfficeCfg) -> str:
    """Name where long waits happen, so the advice follows the data rather than a fixed rule.

    Long = over wait_median_warning_seconds. Compares the long-wait share with
    one or two sessions in play against three or more.
    """
    long = cfg.wait_median_warning_seconds
    low = [v for count, values in week.by_play.items() if count <= 2 for v in values]
    high = [v for count, values in week.by_play.items() if count >= 3 for v in values]
    if not low or not high:
        return "not enough spread in parallel sessions this week to tell overload from time away."
    low_share, high_share = sum(v > long for v in low) / len(low), sum(v > long for v in high) / len(high)
    if high_share > low_share:
        return f"long waits are more common with 3+ sessions in play ({high_share:.0%} vs {low_share:.0%}) — review is the constraint; cap parallel sessions instead of starting more."
    return f"long waits are more common with only 1–2 sessions in play ({low_share:.0%} vs {high_share:.0%}) — the tail is time away, not overload; a session cap would not shorten it, a reachable alert would."
