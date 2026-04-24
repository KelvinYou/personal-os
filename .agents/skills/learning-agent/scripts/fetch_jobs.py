#!/usr/bin/env python3
"""
Thin CLI wrapper around python-jobspy for MY/SG job market scans.

Why JobSpy: it handles LinkedIn / Indeed / Glassdoor / Google Jobs in one call and
normalizes schemas. We stay at conservative defaults (<=50 results per source,
linkedin_fetch_description on) to minimize rate-limit risk without proxies.

Output: single JSON file with raw job records. Skill extraction happens in a
separate LLM pass (see references/job-market-mode.md) so the scraper stays
deterministic and fast to replay.

Usage:
    python fetch_jobs.py --query "software engineer" --location "Singapore" \
        --sources linkedin,indeed,google --limit 30 --output data/jobs/raw/sg.json

Cache behavior: if --output path already exists and was written today, exits
without re-fetching (override with --force). Keeps archival cheap.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

VALID_SOURCES = {"linkedin", "indeed", "glassdoor", "google", "zip_recruiter"}

# MY/SG country codes as expected by JobSpy's country_indeed param.
COUNTRY_MAP = {
    "malaysia": "Malaysia",
    "my": "Malaysia",
    "singapore": "Singapore",
    "sg": "Singapore",
}


def build_query_hash(query: str, location: str, sources: list[str]) -> str:
    payload = json.dumps({"q": query, "loc": location, "src": sorted(sources)}, sort_keys=True)
    return hashlib.md5(payload.encode()).hexdigest()[:8]


def is_fresh_today(path: Path) -> bool:
    """Skip re-fetch if file exists and was written today (UTC)."""
    if not path.exists():
        return False
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return mtime.date() == datetime.now(timezone.utc).date()


def scrape(query: str, location: str, sources: list[str], limit: int, hours_old: int) -> list[dict]:
    try:
        from jobspy import scrape_jobs  # type: ignore
    except ImportError:
        print(
            "ERROR: python-jobspy not installed. Run: pip install python-jobspy",
            file=sys.stderr,
        )
        sys.exit(2)

    country = COUNTRY_MAP.get(location.lower().strip(), location)

    # google_search_term is required for Google Jobs; construct a natural phrasing.
    google_term = f"{query} jobs near {country}"

    try:
        df = scrape_jobs(
            site_name=sources,
            search_term=query,
            google_search_term=google_term,
            location=country,
            results_wanted=limit,
            hours_old=hours_old,
            country_indeed=country,
            linkedin_fetch_description=True,
            verbose=1,
        )
    except Exception as exc:  # JobSpy raises plain Exception on various failures
        print(f"ERROR: JobSpy failed: {exc}", file=sys.stderr)
        sys.exit(3)

    if df is None or len(df) == 0:
        return []

    # Normalize to plain dicts, keep only fields useful for skill extraction.
    records: list[dict] = []
    for _, row in df.iterrows():
        records.append(
            {
                "id": str(row.get("id", "")),
                "site": row.get("site"),
                "title": row.get("title"),
                "company": row.get("company"),
                "location": row.get("location"),
                "job_url": row.get("job_url"),
                "description": row.get("description") or "",
                "job_type": row.get("job_type"),
                "date_posted": str(row.get("date_posted")) if row.get("date_posted") else None,
                "min_amount": row.get("min_amount"),
                "max_amount": row.get("max_amount"),
                "currency": row.get("currency"),
                "is_remote": row.get("is_remote"),
                "skills_extracted": None,  # populated by LLM pass downstream
            }
        )
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape MY/SG jobs via JobSpy.")
    parser.add_argument("--query", required=True, help="Search term, e.g. 'software engineer'")
    parser.add_argument("--location", required=True, help="Malaysia | Singapore (or my/sg)")
    parser.add_argument(
        "--sources",
        default="linkedin,indeed,google",
        help="Comma-separated: linkedin,indeed,glassdoor,google,zip_recruiter",
    )
    parser.add_argument("--limit", type=int, default=30, help="Per-source result cap (default 30, max 50)")
    parser.add_argument("--hours-old", type=int, default=168, help="Only jobs posted within N hours (default 168 = 7d)")
    parser.add_argument("--output", required=True, help="Output JSON path")
    parser.add_argument("--force", action="store_true", help="Re-fetch even if today's cache exists")
    args = parser.parse_args()

    sources = [s.strip() for s in args.sources.split(",") if s.strip()]
    invalid = set(sources) - VALID_SOURCES
    if invalid:
        print(f"ERROR: unknown sources: {invalid}. Valid: {VALID_SOURCES}", file=sys.stderr)
        return 1

    limit = min(max(args.limit, 1), 50)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    if is_fresh_today(output) and not args.force:
        print(f"Cache hit for today: {output}. Use --force to refresh.", file=sys.stderr)
        return 0

    started = time.time()
    jobs = scrape(args.query, args.location, sources, limit, args.hours_old)
    elapsed = time.time() - started

    payload = {
        "query": args.query,
        "location": args.location,
        "sources": sources,
        "limit": limit,
        "hours_old": args.hours_old,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "fetch_duration_sec": round(elapsed, 1),
        "query_hash": build_query_hash(args.query, args.location, sources),
        "job_count": len(jobs),
        "jobs": jobs,
    }
    output.write_text(json.dumps(payload, indent=2, default=str, ensure_ascii=False))
    print(f"Saved {len(jobs)} jobs to {output} ({elapsed:.1f}s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
