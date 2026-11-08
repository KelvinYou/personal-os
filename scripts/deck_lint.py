#!/usr/bin/env python3
# flow: docs-check
"""Lint .pptx decks against docs/presentation-guide.md § Visual acceptance.

Exit code 0 = no ERROR findings; 1 = at least one.
Usage: deck_lint.py DECK.pptx [...] [--exempt 4,12] [--layouts]
  --exempt   slide numbers excluded from FOCAL and RHYTHM (e.g. appendix inventories);
             default: {"deck_lint": {"exempt": [...], "reason": "..."}} in production.json
  --layouts  print each slide's derived layout fingerprint
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from lib.config import load_thresholds  # noqa: E402
from lib.deck import layout_of, lint_deck, read_deck, sidecar_exempt  # noqa: E402


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("decks", nargs="+", type=Path)
    ap.add_argument("--exempt", default="",
                    help="comma-separated slide numbers; default: deck_lint.exempt in production.json")
    ap.add_argument("--layouts", action="store_true",
                    help="print each slide's derived layout (paste into production notes)")
    args = ap.parse_args(argv)
    override = {int(x) for x in args.exempt.split(",") if x.strip()}

    cfg = load_thresholds().presentation
    if cfg is None:
        print("[Status: Critical] No `presentation:` block in data/config/thresholds.yaml; "
              "copy it from templates/thresholds.example.yaml.")
        return 1

    errors = 0
    for deck in args.decks:
        if args.layouts:
            for s in read_deck(deck):
                print(f"{deck.name} slide {s.number}: {layout_of(s, cfg)}")
        findings = lint_deck(deck, cfg, override or sidecar_exempt(deck))
        if not findings:
            print(f"[Status: OK] {deck.name}: clean")
            continue
        print(f"\n{deck.name}")
        for f in findings:
            print(f"  {f.format()}")
        errors += len(findings)

    if errors:
        print(f"\n[Status: Critical] {errors} finding(s) across {len(args.decks)} deck(s).")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
