"""Deterministic query adapter over the public kelvinyou-notes food dataset.

See docs/plan-public-knowledge-integration.md §6-8 for the design contract:
this package is the *only* place that computes cost/price derivations.
kelvinyou-notes's JS scripts render YAML as-is; they must never duplicate
this arithmetic.

Meal-template support (meal_lookup/search_meals, ingredient/basis-conversion
math) was removed 2026-08-24 along with datasets/nutrition/meals/ — see
docs/plan-public-knowledge-integration.md's Phase 3/4 notes.
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
