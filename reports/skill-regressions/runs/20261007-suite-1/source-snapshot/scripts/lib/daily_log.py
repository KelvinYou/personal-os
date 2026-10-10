"""Daily log I/O and Poor-sleep derivation.

All access to data/daily/*.md goes through `load()` so schema violations
surface at the single boundary.
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import sys
from typing import Iterable, Iterator

import yaml

from .clock import today_kl
from .schema import DailyLog, SleepCfg, parse_date_from_filename

ROOT = Path(__file__).resolve().parents[2]
DAILY_DIR = ROOT / "data" / "daily"


def _split_frontmatter(content: str) -> tuple[dict, str] | None:
    parts = content.split("---", 2)
    if len(parts) < 3:
        return None
    meta = yaml.safe_load(parts[1]) or {}
    body = parts[2]
    return meta, body


def load(path: Path) -> DailyLog:
    """Parse a daily log path → DailyLog. Raises ValidationError on schema drift."""
    content = path.read_text(encoding="utf-8")
    split = _split_frontmatter(content)
    if split is None:
        raise ValueError(f"{path.name}: no frontmatter")
    meta, _ = split
    meta["date"] = parse_date_from_filename(path)
    return DailyLog.model_validate(meta)


def load_safe(path: Path) -> tuple[DailyLog | None, str | None]:
    """Like load() but returns (None, error_message) instead of raising."""
    try:
        return load(path), None
    except Exception as e:  # pydantic ValidationError / file errors
        return None, f"{path.name}: {e}"


def iter_all(log_dir: Path | None = None) -> Iterator[DailyLog]:
    d = Path(log_dir) if log_dir else DAILY_DIR
    for fp in sorted(d.glob("*.md")):
        log, err = load_safe(fp)
        if log is not None:
            yield log
        elif err:
            print(f"[Status: Warning] {err}", file=sys.stderr)


def iter_week(monday: date, log_dir: Path | None = None) -> Iterator[DailyLog]:
    """Yield logs for Mon..Sun of the week starting at `monday`."""
    d = Path(log_dir) if log_dir else DAILY_DIR
    for i in range(7):
        fp = d / f"{(monday + timedelta(days=i)).isoformat()}.md"
        if fp.exists():
            log, err = load_safe(fp)
            if log is not None:
                yield log
            elif err:
                print(f"[Status: Warning] {err}", file=sys.stderr)


def week_bounds(target: date | None = None) -> date:
    t = target or today_kl()
    return t - timedelta(days=t.weekday())


def derive_poor_sleep(log: DailyLog, sleep_cfg: SleepCfg | None = None) -> bool:
    """Apply Option P-d using the configured sleep thresholds.

    ``sleep_cfg`` is optional for callers that use this public helper directly;
    the fallback loads the same thresholds used by the production pipeline.
    """
    if sleep_cfg is None:
        # Lazy import avoids a config → schema → daily_log import cycle while
        # keeping the backwards-compatible one-argument helper.
        from .config import load_thresholds

        sleep_cfg = load_thresholds().sleep

    dur = log.sleep.duration
    if dur is None:
        return False
    if dur < sleep_cfg.poor_sleep_duration_hours:
        return True
    awake = log.sleep.awake_min or 0
    hrv = log.readiness.hrv
    baseline = log.readiness.hrv_baseline
    awake_threshold = sleep_cfg.awake_min_warning
    if (
        awake_threshold is not None
        and awake > awake_threshold
        and hrv is not None
        and baseline is not None
        and baseline > 0
    ):
        if hrv < baseline * sleep_cfg.poor_sleep_hrv_ratio:
            return True
    return False


def consecutive_poor(logs: Iterable[DailyLog], sleep_cfg: SleepCfg | None = None) -> int:
    """Consecutive Poor days counted backward from the latest log."""
    ordered = sorted(logs, key=lambda l: l.date, reverse=True)
    count = 0
    for log in ordered:
        if derive_poor_sleep(log, sleep_cfg):
            count += 1
        else:
            break
    return count
