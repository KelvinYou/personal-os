#!/usr/bin/env python3
"""Decision calibration analysis.

Reads all reviewed decisions, computes calibration stats, and prints
a terminal-friendly summary. Brier score requires confidence field
(Phase 2+).
"""
from __future__ import annotations

import sys
from collections import Counter
from datetime import date
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DECISIONS_DIR = PROJECT_ROOT / "data" / "decisions"


def _parse_frontmatter(path: Path) -> dict | None:
    parts = path.read_text(encoding="utf-8").split("---", 2)
    if len(parts) < 3:
        return None
    return yaml.safe_load(parts[1]) or {}


def load_all() -> list[dict]:
    decisions: list[dict] = []
    if not DECISIONS_DIR.is_dir():
        return decisions
    for p in sorted(DECISIONS_DIR.glob("*.md")):
        if p.name.startswith("."):
            continue
        meta = _parse_frontmatter(p)
        if meta:
            meta["_path"] = str(p)
            decisions.append(meta)
    return decisions


def main() -> None:
    all_decisions = load_all()
    if not all_decisions:
        print("[OK] No decisions found.")
        return

    reviewed = [d for d in all_decisions if d.get("status") == "reviewed"]
    open_count = sum(1 for d in all_decisions if d.get("status") in ("open", "pushed"))
    expired = sum(1 for d in all_decisions if d.get("status") == "expired")

    print("=" * 50)
    print("[Decision Journal] Calibration Report")
    print("=" * 50)
    print(f"  Total decisions  : {len(all_decisions)}")
    print(f"  Open / Pushed    : {open_count}")
    print(f"  Reviewed         : {len(reviewed)}")
    print(f"  Expired          : {expired}")
    print("-" * 50)

    if not reviewed:
        print("  No reviewed decisions yet. Need ≥ 5 for meaningful analysis.")
        print("=" * 50)
        return

    # Calibration delta distribution
    delta_counts = Counter(d.get("calibration_delta", "unknown") for d in reviewed)
    print("  Calibration delta distribution:")
    for delta in ["as_expected", "better", "worse", "irrelevant", "too_early"]:
        count = delta_counts.get(delta, 0)
        bar = "█" * count
        print(f"    {delta:14s}: {count:2d}  {bar}")

    # Category distribution
    cat_counts = Counter(d.get("category", "unknown") for d in all_decisions)
    print("\n  Category distribution (all decisions):")
    for cat, count in cat_counts.most_common():
        print(f"    {cat:14s}: {count}")

    # Decision type distribution
    type_counts = Counter(d.get("decision_type", "unknown") for d in all_decisions)
    print("\n  Decision type distribution:")
    for dt, count in type_counts.most_common():
        print(f"    {dt:14s}: {count}")
    proactive = type_counts.get("proactive", 0)
    total = len(all_decisions)
    pct = (proactive / total * 100) if total else 0
    if pct < 30:
        print(f"  ⚠️  Proactive decisions at {pct:.0f}% (target ≥ 30%)")

    # Stakes distribution
    stakes_counts = Counter(d.get("stakes", "unknown") for d in all_decisions)
    print("\n  Stakes distribution:")
    for s, count in stakes_counts.most_common():
        print(f"    {s:14s}: {count}")

    # Brier score (only if confidence data exists)
    with_confidence = [d for d in reviewed if d.get("confidence") is not None]
    if len(with_confidence) >= 5:
        print("\n  Brier Score Analysis (confidence vs outcome):")
        brier_sum = 0.0
        for d in with_confidence:
            conf = float(d["confidence"])
            delta = d.get("calibration_delta", "")
            # Map outcome to binary: as_expected/better = 1, worse = 0
            if delta in ("as_expected", "better"):
                outcome = 1.0
            elif delta == "worse":
                outcome = 0.0
            else:
                continue
            brier_sum += (conf - outcome) ** 2
        n = sum(1 for d in with_confidence if d.get("calibration_delta") in ("as_expected", "better", "worse"))
        if n > 0:
            brier = brier_sum / n
            print(f"    Brier score: {brier:.3f}  (0 = perfect, 0.25 = random)")
            print(f"    Samples: {n}")
            if brier < 0.1:
                print("    ✅ Well-calibrated")
            elif brier < 0.2:
                print("    ⚠️  Moderate calibration — room for improvement")
            else:
                print("    ❌ Poor calibration — confidence doesn't match outcomes")
    elif with_confidence:
        print(f"\n  Confidence data on {len(with_confidence)} decisions (need ≥ 5 for Brier score)")
    else:
        print("\n  No confidence data yet. Add via /decision-review to enable Brier score.")

    # Lessons extracted
    with_lessons = [d for d in reviewed if d.get("lesson")]
    if with_lessons:
        print(f"\n  Lessons extracted: {len(with_lessons)}")
        for d in with_lessons[-5:]:  # show last 5
            print(f"    [{d.get('id', '?')}] {d['lesson']}")

    print("=" * 50)


if __name__ == "__main__":
    main()
