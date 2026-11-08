#!/usr/bin/env python3
# flow: ui
"""Build a standalone HTML page that embeds the shared design assets.

    python3 scripts/ui_build.py --input SPEC.json --output /abs/path/index.html

Writes ui-artifact.json beside the output; check it with scripts/ui_check.py.
Design: docs/design/ui-artifact-enforcement.md.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.ui_artifact import MANIFEST_NAME, build  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True, type=Path, help="spec JSON (title, pattern, body_html_file, …)")
    ap.add_argument("--output", required=True, type=Path, help="output HTML path; may be outside the repository")
    args = ap.parse_args()
    try:
        manifest = build(args.input.resolve(), args.output.resolve())
    except (OSError, ValueError, KeyError) as e:
        print(f"[Status: Critical] ui-build: {e}")
        return 1
    print(f"[Status: OK] built {manifest['artifact']}")
    print(f"  manifest: {Path(manifest['artifact']).parent / MANIFEST_NAME}")
    print(f"[Next] make ui-check MANIFEST={Path(manifest['artifact']).parent / MANIFEST_NAME}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
