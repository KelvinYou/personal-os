from __future__ import annotations

from typing import Any

from .errors import NutritionDataError

MACRO_FIELDS = ["protein_g", "carbs_g", "fat_g", "sugar_g", "kcal"]


def parse_cost(value: Any) -> float:
    """"~7.20" / 7.2 -> 7.2. The "~" estimate marker lives on is_estimate,
    not the numeric value — see notes/datasets/nutrition/README.md."""
    return float(str(value).lstrip("~"))


def food_lookup(dataset: dict, food_id: str) -> dict:
    food = dataset["foods"].get(food_id)
    if food is None:
        raise NutritionDataError(f'unknown food id "{food_id}"')
    price = dataset["prices"].get(food_id)
    return {
        "id": food["id"],
        "name": food["name"],
        "basis": food["basis"],
        "macros": {f: food.get(f) for f in MACRO_FIELDS},
        "glycemic_index": food.get("glycemic_index"),
        "price": None if price is None else f'{"~" if price.get("is_estimate") else ""}RM{parse_cost(price["unit_cost_myr"])} / {price["unit"].removeprefix("per ")}',
        "source": food.get("source"),
        "last_verified": food.get("last_verified"),
    }
