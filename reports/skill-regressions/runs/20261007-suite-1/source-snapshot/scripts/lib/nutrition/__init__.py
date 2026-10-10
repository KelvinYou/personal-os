"""Deterministic query adapter over the public notes food dataset.

The public food dataset is owned by `repos/notes`; this package is the
*only* place that computes cost/price derivations. The notes repository's
JS scripts render YAML as-is and must never duplicate this arithmetic.

Meal-template support (meal_lookup/search_meals, ingredient/basis-conversion
math) was removed 2026-08-24 along with datasets/nutrition/meals/ — see
the current read contract in
`.agents/skills/coach-planner/references/nutrition-source.md`.
"""
from .errors import NutritionSourceMissing, NutritionDataError
from .loader import load_dataset
from .query import food_lookup

__all__ = [
    "NutritionSourceMissing",
    "NutritionDataError",
    "load_dataset",
    "food_lookup",
]
