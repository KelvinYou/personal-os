#!/usr/bin/env python3
"""
Aggregate skill frequencies across archived job fetches.

Reads every JSON file under data/jobs/raw/ that has the skills_extracted field
populated (see references/job-market-mode.md for how Claude fills that field),
then computes:
  - Overall skill frequency ranking
  - Per-location breakdown (MY vs SG)
  - Per-source breakdown (linkedin / jobstreet / indeed / ...)
  - Recent-vs-prior delta: compares last 30 days vs the 30 days before that,
    flags "emerging" (>50% growth) and "fading" (<-30%) skills

Output: data/jobs/trends.json, a compact digest Claude reads to produce the
final report. This script is pure aggregation — no network, no LLM — so it's
fast and deterministic.

Usage:
    python aggregate_skills.py --archive-dir data/jobs/raw \
        --output data/jobs/trends.json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


def load_enriched_files(archive_dir: Path) -> list[dict]:
    """Load fetch output files that have at least some skills extracted."""
    files = sorted(archive_dir.glob("*.json"))
    loaded = []
    for f in files:
        try:
            payload = json.loads(f.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        # Keep only if at least one job has skills filled in.
        if any(
            isinstance(j.get("skills_extracted"), list) and j["skills_extracted"]
            for j in payload.get("jobs", [])
        ):
            payload["_file"] = str(f)
            loaded.append(payload)
    return loaded


def parse_fetched_at(payload: dict) -> datetime | None:
    raw = payload.get("fetched_at")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def normalize_skill(skill: str) -> str:
    """Light canonicalization so 'Python' and 'python' collapse."""
    return skill.strip().lower()


def aggregate(payloads: list[dict], window_days: int = 30) -> dict:
    now = datetime.now(timezone.utc)
    recent_cutoff = now - timedelta(days=window_days)
    prior_cutoff = now - timedelta(days=window_days * 2)

    overall = Counter()
    by_location: dict[str, Counter] = defaultdict(Counter)
    by_source: dict[str, Counter] = defaultdict(Counter)
    recent = Counter()
    prior = Counter()
    total_jobs = 0
    jobs_with_skills = 0

    for payload in payloads:
        fetched_at = parse_fetched_at(payload)
        location = payload.get("location", "Unknown")

        for job in payload.get("jobs", []):
            total_jobs += 1
            skills = job.get("skills_extracted")
            if not isinstance(skills, list) or not skills:
                continue
            jobs_with_skills += 1
            site = job.get("site") or "unknown"

            unique_skills = {normalize_skill(s) for s in skills if s}
            for skill in unique_skills:
                overall[skill] += 1
                by_location[location][skill] += 1
                by_source[site][skill] += 1
                if fetched_at and fetched_at >= recent_cutoff:
                    recent[skill] += 1
                elif fetched_at and fetched_at >= prior_cutoff:
                    prior[skill] += 1

    # Compute deltas for skills present in either window.
    deltas: list[dict] = []
    candidate_skills = set(recent) | set(prior)
    for skill in candidate_skills:
        r = recent[skill]
        p = prior[skill]
        # Require minimum volume to avoid noise from skills mentioned once.
        if r + p < 3:
            continue
        if p == 0:
            growth = float("inf") if r > 0 else 0.0
        else:
            growth = (r - p) / p
        tag = None
        if growth > 0.5 and r >= 3:
            tag = "emerging"
        elif growth < -0.3 and p >= 3:
            tag = "fading"
        if tag:
            deltas.append(
                {
                    "skill": skill,
                    "recent_count": r,
                    "prior_count": p,
                    "growth_ratio": None if growth == float("inf") else round(growth, 2),
                    "tag": tag,
                }
            )
    deltas.sort(key=lambda d: (d["tag"], -d["recent_count"]))

    return {
        "generated_at": now.isoformat(),
        "window_days": window_days,
        "source_files": len(payloads),
        "total_jobs": total_jobs,
        "jobs_with_skills": jobs_with_skills,
        "top_overall": overall.most_common(30),
        "top_by_location": {
            loc: counter.most_common(20) for loc, counter in by_location.items()
        },
        "top_by_source": {
            site: counter.most_common(15) for site, counter in by_source.items()
        },
        "deltas": deltas,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate skill frequency trends.")
    parser.add_argument("--archive-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--window-days",
        type=int,
        default=30,
        help="Recent window size for delta calc (default 30)",
    )
    args = parser.parse_args()

    archive = Path(args.archive_dir)
    if not archive.exists():
        print(f"ERROR: archive dir not found: {archive}", file=sys.stderr)
        return 1

    payloads = load_enriched_files(archive)
    if not payloads:
        print(
            f"WARN: no enriched fetch files found in {archive}. Extract skills first.",
            file=sys.stderr,
        )
        # Still write an empty digest so callers don't crash.
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(
                {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "source_files": 0,
                    "total_jobs": 0,
                    "message": "no enriched data",
                },
                indent=2,
            )
        )
        return 0

    digest = aggregate(payloads, window_days=args.window_days)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(digest, indent=2, ensure_ascii=False))
    print(
        f"Aggregated {digest['jobs_with_skills']}/{digest['total_jobs']} jobs "
        f"across {digest['source_files']} files → {output}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
