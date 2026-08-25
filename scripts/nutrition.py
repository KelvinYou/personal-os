#!/usr/bin/env python3
"""Deterministic query CLI over the public kelvinyou-notes food dataset.

Usage:
    python3 scripts/nutrition.py food chicken_breast_raw

See docs/plan-public-knowledge-integration.md §8. All cost/price parsing
lives in scripts/lib/nutrition/ — this file only parses args and formats
output.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.nutrition import NutritionDataError, NutritionSourceMissing, food_lookup, load_dataset


def print_food(dataset: dict, food_id: str) -> None:
    f = food_lookup(dataset, food_id)
    print(f"id: {f['id']}")
    print(f"name: {f['name']}")
    print(f"basis: {f['basis']}")
    m = f["macros"]
    print(f"protein: {m['protein_g']}g  carbs: {m['carbs_g']}g  fat: {m['fat_g']}g  sugar: {m['sugar_g']}g")
    print(f"kcal: {m['kcal']}")
    if f["glycemic_index"] is not None:
        print(f"gi: {f['glycemic_index']}")
    print(f"price: {f['price'] or 'n/a'}")
    print(f"source_updated: {f['last_verified']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_food = sub.add_parser("food", help="Look up one food record")
    p_food.add_argument("food_id")

    args = parser.parse_args()

    try:
        dataset = load_dataset()
        if args.command == "food":
            print_food(dataset, args.food_id)
    except (NutritionDataError, NutritionSourceMissing) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
