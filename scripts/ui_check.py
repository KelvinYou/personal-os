#!/usr/bin/env python3
# flow: ui
"""Check delivered standalone HTML for real design-system reuse.

    python3 scripts/ui_check.py --manifest /abs/path/ui-artifact.json   # built artifact
    python3 scripts/ui_check.py --html page.html [page2.html ...]        # any HTML, no manifest

Fails when a shared asset is not embedded, was edited, is stale against the current
upstream, comes after page CSS, or when the page loads code from the network or points
at missing local files. Content/provenance only: visual review stays a separate step.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.ui_artifact import check_html, check_manifest  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--manifest", type=Path)
    group.add_argument("--html", type=Path, nargs="+")
    args = ap.parse_args()

    reports = [check_manifest(args.manifest.resolve())] if args.manifest else [check_html(p.resolve()) for p in args.html]
    errors = 0
    for rep in reports:
        print(f"{'OK  ' if rep.ok else 'FAIL'} {rep.artifact}")
        for level, code, message in rep.findings:
            print(f"  {level:<5} [{code}] {message}")
        errors += 0 if rep.ok else 1
    status = "OK" if errors == 0 else "Critical"
    print(f"[Status: {status}] {len(reports) - errors}/{len(reports)} artifact(s) pass the reuse check")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
