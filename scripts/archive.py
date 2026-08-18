#!/usr/bin/env python3
"""Archive cold daily logs + prune the COROS staging buffer (C-layer).

Two separate problems, deliberately handled differently:

`data/fitness/*.yaml` is **not** an archive target — it is a staging buffer.
`sync_coros.py` writes it, `patch_coros.py` merges it into the matching daily
frontmatter, and nothing else in the repo reads it. 94 of its 114 files are
byte-for-byte redundant with a daily log that already holds the same values.
So the treatment is a retention window, not a digest: keep a replay buffer,
drop the rest. The exception is a date with fitness data but *no* daily file
(sync_coros skips the patch when the file is absent) — that data has never
landed anywhere, so it gets a daily log created before anything is pruned.

`data/daily/*.md` is real data, but nothing consumes it at per-day granularity
beyond the current week: weekly-review reads the target week, identity-audit
wants 12-week distributions, meta-coach reads reports rather than logs, and the
body-composition trend needs only the sparse `body.*` points. So days past the
hot window collapse into one digest row per ISO week, with three carve-outs
kept as full files — incident days, plan-break days, and measurement days —
because those are the ones actually worth re-reading.

Dry-run by default. `--apply` is what writes and deletes.
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from lib.config import load_thresholds  # noqa: E402
from lib.clock import today_kl  # noqa: E402
from lib.daily_log import derive_poor_sleep, load_safe  # noqa: E402
from lib.defaults import measured_fields  # noqa: E402
from lib.logger import emit_event  # noqa: E402
from lib.schema import DailyLog  # noqa: E402

DATA_DIR = PROJECT_ROOT / "data"
DAILY_DIR = DATA_DIR / "daily"
FITNESS_DIR = DATA_DIR / "fitness"
ARCHIVE_DIR = DATA_DIR / "archive"
TEMPLATE = PROJECT_ROOT / "templates" / "daily.md"

DEFAULT_HOT_DAYS = 90
DEFAULT_FITNESS_DAYS = 30

BODY_FIELDS = (
    "weight", "body_fat_pct", "muscle_kg", "visceral_fat",
    "bmi", "water_pct", "protein_pct", "bone_mass_kg", "basal_metabolism",
)


# --------------------------------------------------------------------------
# keep rules
# --------------------------------------------------------------------------

def keep_reason(log: DailyLog, energy_low: int) -> str | None:
    """Why this cold day should survive as a full file, or None to digest it.

    Kept deliberately narrow. A first cut treated any non-empty
    `primary_blocker` as an incident and that retained 45 of 62 cold days —
    because in the pre-W22 narrative-era logs the field was filled every single
    day as routine commentary ("前夜睡眠质量差导致精力基线下降"), not to flag an
    event. Blocker text is not lost: every cold day that had one is listed in
    the quarter file's 事件 section.

    Measurement days are also *not* kept — `archive/body.csv` carries the full
    `body.*` series across all time, so the surrounding file adds nothing.

    What survives is what you would actually reopen: the plan broke, the body
    gave out, or the night collapsed.
    """
    if log.adherence.timetable == "🔴":
        return "plan-break"
    if log.energy_level is not None and log.energy_level <= energy_low:
        return "energy-critical"
    if log.sleep.duration is not None and log.sleep.duration < 5.0:
        return "severe-short-sleep"
    return None


# --------------------------------------------------------------------------
# digest
# --------------------------------------------------------------------------

def _rel(p: Path) -> str:
    """Repo-relative path for display, falling back to the absolute one."""
    try:
        return str(p.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(p)


def _fmt(v: float | None, spec: str = ".1f", dash: str = "—") -> str:
    return dash if v is None else format(v, spec)


def _avg(xs: list[float]) -> float | None:
    return sum(xs) / len(xs) if xs else None


def week_digest_row(
    monday: date,
    logs: list[DailyLog],
    sleep_baseline: float,
    sleep_cfg=None,
) -> str:
    """One markdown row summarizing an ISO week of cold logs."""
    iso_year, iso_week, _ = monday.isocalendar()
    energies = [float(l.energy_level) for l in logs if l.energy_level is not None]
    sleeps = [float(l.sleep.duration) for l in logs if l.sleep.duration is not None]
    hrvs = [float(l.readiness.hrv) for l in logs if l.readiness.hrv is not None]
    dw = sum(l.deep_work_hours for l in logs if l.deep_work_hours is not None)
    spend = sum(s.amount for l in logs for s in l.daily_spend if s.amount is not None)
    load = sum(l.training.today_load for l in logs if l.training.today_load is not None)
    sessions = sum(len(l.activities) for l in logs)
    poor = sum(1 for l in logs if derive_poor_sleep(l, sleep_cfg))
    debt = sum(max(0.0, sleep_baseline - float(l.sleep.duration)) for l in logs if l.sleep.duration is not None)
    weights = [float(l.body.weight) for l in logs if l.body.weight is not None]
    blockers = sum(1 for l in logs if l.primary_blocker and str(l.primary_blocker).strip())

    return (
        f"| {iso_year}-W{iso_week:02d} | {monday.isoformat()} | {len(logs)}/7 | "
        f"{_fmt(_avg(energies))} | {dw:.1f}h | {_fmt(_avg(sleeps), '.2f')} | {poor} | {debt:.1f}h | "
        f"{_fmt(_avg(hrvs), '.0f')} | {_fmt(weights[-1] if weights else None, '.1f')} | "
        f"RM{spend:.0f} | {sessions}/{load:.0f} | {blockers or '—'} |"
    )


DIGEST_HEADER = (
    "| 周 | 起始 | 记录 | Energy | Deep Work | 睡眠 | Poor | 负债 | HRV | 体重 | 支出 | 训练次/负荷 | Blocker数 |\n"
    "|---|---|---|---|---|---|---|---|---|---|---|---|---|"
)


def event_lines(logs: list[DailyLog]) -> list[str]:
    """Every cold day that recorded a blocker, one line each.

    This is where the narrative survives the fold: the files go away, the text
    that made them worth reading does not.
    """
    out = []
    for log in sorted(logs, key=lambda l: l.date):
        b = str(log.primary_blocker).strip() if log.primary_blocker else ""
        if b:
            e = "" if log.energy_level is None else f" · E{log.energy_level}"
            out.append(f"- **{log.date.isoformat()}**{e} — {b}")
    return out


def quarter_of(d: date) -> str:
    return f"{d.year}-Q{(d.month - 1) // 3 + 1}"


def build_digests(
    cold: list[DailyLog], sleep_baseline: float, sleep_cfg=None
) -> dict[str, tuple[list[str], list[str]]]:
    """Group cold logs by ISO week, bucket by quarter → (digest rows, event lines)."""
    by_week: dict[date, list[DailyLog]] = defaultdict(list)
    for log in cold:
        by_week[log.date - timedelta(days=log.date.weekday())].append(log)

    rows: dict[str, list[str]] = defaultdict(list)
    events: dict[str, list[str]] = defaultdict(list)
    for monday in sorted(by_week):
        week = sorted(by_week[monday], key=lambda l: l.date)
        q = quarter_of(monday)
        rows[q].append(week_digest_row(monday, week, sleep_baseline, sleep_cfg))
        events[q].extend(event_lines(week))
    return {q: (rows[q], events[q]) for q in rows}


def body_rows(logs: list[DailyLog]) -> list[dict]:
    rows = []
    for log in sorted(logs, key=lambda l: l.date):
        if any(getattr(log.body, f) is not None for f in BODY_FIELDS):
            row = {"date": log.date.isoformat()}
            row.update({f: getattr(log.body, f) for f in BODY_FIELDS})
            rows.append(row)
    return rows


def merge_body_rows(body_csv: Path, current_rows: list[dict]) -> list[dict]:
    """Preserve archived body points while refreshing rows from live daily logs.

    Cold daily files are deleted after they are folded into the archive.  On a
    later run, ``current_rows`` therefore cannot contain the already-archived
    measurements.  Keep the existing CSV as the historical source and let a
    currently present daily log replace the row for the same date.
    """
    by_date: dict[str, dict] = {}
    if body_csv.is_file():
        with body_csv.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                day = row.get("date")
                if day:
                    by_date[day] = {
                        "date": day,
                        **{field: row.get(field, "") for field in BODY_FIELDS},
                    }

    for row in current_rows:
        by_date[str(row["date"])] = row

    return [by_date[day] for day in sorted(by_date)]


# --------------------------------------------------------------------------
# fitness staging buffer
# --------------------------------------------------------------------------

def orphan_fitness(cutoff: date) -> list[Path]:
    """Fitness files whose daily log was never created (sync_coros skipped the patch)."""
    if not FITNESS_DIR.is_dir():
        return []
    out = []
    for fp in sorted(FITNESS_DIR.glob("*.yaml")):
        try:
            d = date.fromisoformat(fp.stem)
        except ValueError:
            continue
        if not (DAILY_DIR / f"{d.isoformat()}.md").exists():
            out.append(fp)
    return out


def prunable_fitness(cutoff: date) -> list[Path]:
    """Fitness files older than the replay window *and* already merged into a daily log."""
    if not FITNESS_DIR.is_dir():
        return []
    out = []
    for fp in sorted(FITNESS_DIR.glob("*.yaml")):
        try:
            d = date.fromisoformat(fp.stem)
        except ValueError:
            continue
        if d >= cutoff:
            continue
        if (DAILY_DIR / f"{d.isoformat()}.md").exists():
            out.append(fp)
    return out


def repair_orphan(fp: Path, apply: bool) -> str:
    """Create the missing daily log, then patch the fitness data into it."""
    d = fp.stem
    target = DAILY_DIR / f"{d}.md"
    if not apply:
        return f"  would create {_rel(target)} + patch COROS"
    target.write_text(TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8")
    from patch_coros import patch_daily
    fitness = yaml.safe_load(fp.read_text(encoding="utf-8"))
    patch_daily(target, fitness)
    return f"  created {_rel(target)} + patched COROS"


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def run(hot_days: int, fitness_days: int, apply: bool, today: date | None = None) -> int:
    if not DAILY_DIR.is_dir():
        print("[Status: Expected] data/ 未 checkout，跳过 (make setup-private)")
        return 0

    cfg = load_thresholds()
    ref = today or today_kl()
    hot_cutoff = ref - timedelta(days=hot_days)
    fit_cutoff = ref - timedelta(days=fitness_days)

    mode = "APPLY" if apply else "DRY-RUN"
    print("=" * 60)
    print(f"[Archive] mode={mode} · hot={hot_days}d (<{hot_cutoff}) · fitness={fitness_days}d (<{fit_cutoff})")
    print("=" * 60)

    # --- 1. orphan fitness repair (must run before any pruning) ---
    orphans = orphan_fitness(fit_cutoff)
    print(f"\n[1/4] Orphan fitness (有 COROS 数据但没有 daily 日志): {len(orphans)}")
    for fp in orphans:
        print(repair_orphan(fp, apply))

    # --- 2. load all daily logs, split hot / cold / keep ---
    all_logs: list[DailyLog] = []
    errors: list[str] = []
    for fp in sorted(DAILY_DIR.glob("*.md")):
        log, err = load_safe(fp)
        if log is None:
            errors.append(err or fp.name)
        else:
            all_logs.append(log)
    if errors:
        print(f"\n[Status: Warning] {len(errors)} 个日志解析失败，已跳过:")
        for e in errors[:5]:
            print(f"  - {e}")

    cold = [l for l in all_logs if l.date < hot_cutoff]
    hot = [l for l in all_logs if l.date >= hot_cutoff]
    keeps = {l.date: keep_reason(l, cfg.energy.low_threshold) for l in cold}
    kept = {d: r for d, r in keeps.items() if r}
    digestible = [l for l in cold if not keeps[l.date]]

    print(f"\n[2/4] Daily logs: {len(all_logs)} 总计 · {len(hot)} 热窗口保留 · "
          f"{len(cold)} 冷数据 ({len(kept)} 保留原文 / {len(digestible)} 折叠为周行)")
    for d, r in sorted(kept.items()):
        print(f"  keep {d} — {r}")

    # --- 3. body.csv (全历史，跨热冷窗口) ---
    brows = body_rows(all_logs)
    body_csv = ARCHIVE_DIR / "body.csv"
    merged_brows = merge_body_rows(body_csv, brows)
    print(f"\n[3/4] 体成分测点: {len(merged_brows)} → {_rel(body_csv)}")
    if apply and brows:
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        with body_csv.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["date", *BODY_FIELDS])
            w.writeheader()
            w.writerows(merged_brows)

    # --- 4. quarterly digests + prune ---
    digests = build_digests(
        digestible, cfg.sleep.baseline_hours, cfg.sleep
    )
    print(f"\n[4/4] 季度归档: {len(digests)} 个文件")
    for q, (rows, events) in sorted(digests.items()):
        path = ARCHIVE_DIR / f"{q}.md"
        print(f"  {_rel(path)} — {len(rows)} 周 · {len(events)} 条事件")
        if apply:
            ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
            body = [
                f"# {q} 归档摘要",
                "",
                "> 由 `scripts/archive.py` 生成。逐日原文已折叠 —— 90 天外没有消费者需要那个粒度。",
                "> plan-break / energy-critical / 严重短睡日仍以原文保留在 `data/daily/`。",
                "> 体成分完整序列见 `data/archive/body.csv`。",
                "",
                DIGEST_HEADER,
                *rows,
                "",
            ]
            if events:
                body += ["## 事件记录 (primary_blocker)", "", *events, ""]
            path.write_text("\n".join(body), encoding="utf-8")

    pruned_daily = [DAILY_DIR / f"{l.date.isoformat()}.md" for l in digestible]
    prunable_fit = prunable_fitness(fit_cutoff)
    freed = sum(p.stat().st_size for p in pruned_daily + prunable_fit if p.exists())
    print(f"\n  prune: {len(pruned_daily)} daily + {len(prunable_fit)} fitness ≈ {freed / 1024:.0f}KB")
    if apply:
        for p in pruned_daily + prunable_fit:
            if p.exists():
                p.unlink()

    print("\n" + "=" * 60)
    if apply:
        print("[Status: OK] 归档完成。data/ 是 submodule，记得进去 commit。")
    else:
        print("[Status: OK] Dry-run 完成，未改动任何文件。加 APPLY=1 真写。")
    print("=" * 60)

    emit_event("archive", {
        "mode": mode,
        "hot_days": hot_days,
        "orphans_repaired": len(orphans),
        "cold_digested": len(digestible),
        "cold_kept": len(kept),
        "fitness_pruned": len(prunable_fit),
        "body_points": len(brows),
        "freed_kb": round(freed / 1024, 1),
    })
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Archive cold daily logs + prune COROS staging buffer")
    p.add_argument("--apply", action="store_true", help="真写 (默认 dry-run)")
    p.add_argument("--hot-days", type=int, default=DEFAULT_HOT_DAYS, help=f"daily 热窗口天数 (默认 {DEFAULT_HOT_DAYS})")
    p.add_argument("--fitness-days", type=int, default=DEFAULT_FITNESS_DAYS,
                   help=f"fitness 重放窗口天数 (默认 {DEFAULT_FITNESS_DAYS})")
    p.add_argument("--date", help="参考日期 YYYY-MM-DD (测试用)", default=None)
    a = p.parse_args()
    return run(a.hot_days, a.fitness_days, a.apply, date.fromisoformat(a.date) if a.date else None)


if __name__ == "__main__":
    sys.exit(main())
