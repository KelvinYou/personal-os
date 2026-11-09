#!/usr/bin/env python3
# flow: content
"""Render one exact chart page for an XHS post from a page spec and research-data.json.

Usage: post_chart.py SPEC.json OUT.png [--html-only]
Numbers on the page come only from the data file ({{fact}} placeholders); a typed digit
fails with the fix named. The HTML is kept beside the PNG as the editable source.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.post_chart import H, W, SpecError, build_page, load  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("spec", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--html-only", action="store_true")
    args = parser.parse_args()
    if ".." in args.spec.parts or ".." in args.out.parts:
        print("[Status: Critical] SPEC and OUT must not contain '..'")
        return 1
    posts = (ROOT / "data" / "posts").resolve()
    spec_path, out_path = args.spec.resolve(), args.out.resolve()
    if posts in spec_path.parents:
        folder = posts / spec_path.relative_to(posts).parts[0]
        if folder not in out_path.parents:
            print(f"[Status: Critical] OUT must stay inside the post folder {folder.relative_to(ROOT)}")
            return 1
    try:
        spec, data = load(args.spec)
        page = build_page(spec, data)
    except (SpecError, ValueError, OSError) as exc:
        print(f"[Status: Critical] {exc}")
        return 1
    source = args.out.with_suffix(".html")
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(page, encoding="utf-8")
    if args.html_only:
        print(json.dumps({"ok": True, "html": str(source)}))
        return 0
    done = subprocess.run(["node", str(ROOT / "scripts/render_html.mjs"), str(source), str(args.out), str(W), str(H)], capture_output=True, text=True)
    if done.returncode:
        print(f"[Status: Critical] render failed: {done.stderr.strip()[-800:]}")
        return 1
    print(done.stdout.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
