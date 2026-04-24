#!/usr/bin/env python3
"""
Best-effort scraper for JobStreet MY/SG.

Why a custom client: JobStreet migrated to the SEEK platform (2023-2024) and
no maintained open-source library wraps its API. The main site proxies a
JSON search endpoint that the browser hits; we replicate that request.

Two strategies, tried in order:
  1. JSON API (fast, clean). Endpoint shape is undocumented and may drift,
     so we fail loudly rather than silently degrade when the response shape
     stops matching our expectations.
  2. HTML fallback (slower). Currently not implemented — when the API
     breaks, exit non-zero so Claude can tell the user to upgrade this
     script rather than trust stale output.

Output schema matches fetch_jobs.py so aggregate_skills.py can read both.

Usage:
    python fetch_jobstreet.py --query "software engineer" --country my \
        --limit 30 --output data/jobs/raw/jobstreet_my.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# JobStreet/SEEK JSON search endpoints.
# These are the endpoints the browser hits when you search on my.jobstreet.com
# or sg.jobstreet.com. Schema is not documented — if JobStreet changes it
# we want to fail loudly, not silently return zero jobs.
ENDPOINTS = {
    "my": "https://my.jobstreet.com/api/jobsearch/v5/search",
    "sg": "https://sg.jobstreet.com/api/jobsearch/v5/search",
}

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


def is_fresh_today(path: Path) -> bool:
    if not path.exists():
        return False
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return mtime.date() == datetime.now(timezone.utc).date()


def build_query_hash(query: str, country: str) -> str:
    payload = json.dumps({"q": query, "c": country}, sort_keys=True)
    return hashlib.md5(payload.encode()).hexdigest()[:8]


def fetch_api(query: str, country: str, limit: int) -> list[dict]:
    try:
        import httpx  # type: ignore
    except ImportError:
        print("ERROR: httpx not installed. Run: pip install httpx", file=sys.stderr)
        sys.exit(2)

    url = ENDPOINTS[country]
    # page size capped at 30 on most SEEK deployments — request extra pages if needed.
    page_size = min(limit, 30)
    pages_needed = (limit + page_size - 1) // page_size

    all_records: list[dict] = []
    site_tag = f"jobstreet-{country}"

    with httpx.Client(
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": f"https://{country}.jobstreet.com/",
        },
        timeout=30.0,
        follow_redirects=True,
    ) as client:
        for page in range(1, pages_needed + 1):
            params = {
                "siteKey": f"{country.upper()}-Main",
                "sourcesystem": "houston",
                "page": page,
                "pageSize": page_size,
                "keywords": query,
                "locale": "en-MY" if country == "my" else "en-SG",
            }
            try:
                resp = client.get(url, params=params)
            except httpx.HTTPError as exc:
                print(f"ERROR: network failure page {page}: {exc}", file=sys.stderr)
                sys.exit(3)

            if resp.status_code != 200:
                print(
                    f"ERROR: JobStreet returned HTTP {resp.status_code} on page {page}. "
                    f"API schema may have changed — upgrade fetch_jobstreet.py.",
                    file=sys.stderr,
                )
                sys.exit(4)

            try:
                payload = resp.json()
            except ValueError:
                print("ERROR: JobStreet returned non-JSON body. API likely changed.", file=sys.stderr)
                sys.exit(4)

            # The SEEK response nests the actual list under 'data' in current schema.
            # Fall back to a few alternative keys so minor drift doesn't kill us.
            raw_jobs = (
                payload.get("data")
                or payload.get("jobs")
                or payload.get("results")
                or []
            )
            if not isinstance(raw_jobs, list):
                print(f"ERROR: unexpected payload shape on page {page}. Keys: {list(payload.keys())}", file=sys.stderr)
                sys.exit(4)

            if not raw_jobs:
                break

            for j in raw_jobs:
                all_records.append(
                    {
                        "id": str(j.get("id") or j.get("jobId") or ""),
                        "site": site_tag,
                        "title": j.get("title") or j.get("jobTitle"),
                        "company": (j.get("advertiser") or {}).get("description")
                        if isinstance(j.get("advertiser"), dict)
                        else j.get("company"),
                        "location": (j.get("location") or {}).get("label")
                        if isinstance(j.get("location"), dict)
                        else j.get("location"),
                        "job_url": f"https://{country}.jobstreet.com/job/{j.get('id') or j.get('jobId') or ''}",
                        "description": (
                            j.get("teaser")
                            or j.get("summary")
                            or j.get("abstract")
                            or ""
                        ),
                        "job_type": j.get("workType"),
                        "date_posted": j.get("listingDate") or j.get("postedDate"),
                        "min_amount": (j.get("salary") or {}).get("min")
                        if isinstance(j.get("salary"), dict)
                        else None,
                        "max_amount": (j.get("salary") or {}).get("max")
                        if isinstance(j.get("salary"), dict)
                        else None,
                        "currency": "MYR" if country == "my" else "SGD",
                        "is_remote": bool(j.get("isRemote", False)),
                        "skills_extracted": None,
                    }
                )

            if len(all_records) >= limit:
                break
            # small sleep between pages to stay polite
            time.sleep(1)

    return all_records[:limit]


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape JobStreet MY/SG.")
    parser.add_argument("--query", required=True)
    parser.add_argument("--country", required=True, choices=["my", "sg"])
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--output", required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    if is_fresh_today(output) and not args.force:
        print(f"Cache hit for today: {output}. Use --force to refresh.", file=sys.stderr)
        return 0

    started = time.time()
    jobs = fetch_api(args.query, args.country, args.limit)
    elapsed = time.time() - started

    payload = {
        "query": args.query,
        "location": "Malaysia" if args.country == "my" else "Singapore",
        "sources": [f"jobstreet-{args.country}"],
        "limit": args.limit,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "fetch_duration_sec": round(elapsed, 1),
        "query_hash": build_query_hash(args.query, args.country),
        "job_count": len(jobs),
        "jobs": jobs,
    }
    output.write_text(json.dumps(payload, indent=2, default=str, ensure_ascii=False))
    print(f"Saved {len(jobs)} JobStreet-{args.country} jobs to {output} ({elapsed:.1f}s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
