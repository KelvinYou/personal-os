"""Tests for scripts/lib/nutrition — deterministic fixtures, no real dataset.

Meal-template support (meal_lookup/search_meals, basis-conversion paths) was
removed 2026-08-24 along with datasets/nutrition/meals/ — see
docs/plan-public-knowledge-integration.md's Phase 3/4 notes. Only food_lookup
remains.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.nutrition import NutritionDataError, NutritionSourceMissing, food_lookup, load_dataset  # noqa: E402
from lib.nutrition.loader import DEFAULT_DATASET_DIR  # noqa: E402

FIXTURE_DIR = ROOT / "tests" / "fixtures" / "nutrition"


class NutritionAdapterTests(unittest.TestCase):
    def setUp(self):
        self.dataset = load_dataset(FIXTURE_DIR)

    def test_missing_dataset_dir_raises_source_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(NutritionSourceMissing):
                load_dataset(Path(tmp) / "does-not-exist")

    def test_food_lookup_basic(self):
        f = food_lookup(self.dataset, "fixture_chicken_raw")
        self.assertEqual(f["macros"]["protein_g"], 20)
        self.assertEqual(f["price"], "RM1.5 / 100g")

    def test_food_lookup_unknown_id_raises(self):
        with self.assertRaises(NutritionDataError):
            food_lookup(self.dataset, "does_not_exist")

    def test_food_lookup_supplement_has_no_macros(self):
        f = food_lookup(self.dataset, "fixture_creatine")
        self.assertIsNone(f["macros"]["protein_g"])

    def test_food_lookup_no_price_record(self):
        f = food_lookup(self.dataset, "fixture_beef_no_yield")
        self.assertIsNone(f["price"])

    def test_real_dataset_loads_if_checked_out(self):
        """Smoke test against the real submodule dataset, skipped if not
        checked out (same posture as data/ private-submodule tests)."""
        if not DEFAULT_DATASET_DIR.exists():
            self.skipTest("repos/notes not checked out")
        dataset = load_dataset()
        self.assertGreater(len(dataset["foods"]), 0)
        for food_id in dataset["foods"]:
            food_lookup(dataset, food_id)  # must not raise for any real food record


if __name__ == "__main__":
    unittest.main()
