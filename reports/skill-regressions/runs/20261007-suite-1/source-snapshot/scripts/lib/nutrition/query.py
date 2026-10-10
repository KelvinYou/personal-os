from __future__ import annotations

from typing import Any

from .errors import NutritionDataError

MACRO_FIELDS = ["protein_g", "carbs_g", "fat_g", "sugar_g", "kcal"]

# Mirrors datasets/nutrition/schema.yaml's food.micronutrient_fields in
# repos/notes — kept in sync manually (no cross-repo schema import at query
# time). A field absent from a food record means "not yet researched"; see
# schema.yaml's blank-vs-zero convention.
MICRONUTRIENT_FIELDS = [
    "iron_mg",
    "calcium_mg",
    "magnesium_mg",
    "zinc_mg",
    "potassium_mg",
    "sodium_mg",
    "iodine_ug",
    "vitamin_a_ug",
    "vitamin_d_ug",
    "vitamin_e_mg",
    "vitamin_k_ug",
    "vitamin_b1_mg",
    "vitamin_b2_mg",
    "vitamin_b6_mg",
    "vitamin_b12_ug",
    "folate_ug",
    "vitamin_c_mg",
    "omega3_g",
]


def parse_cost(value: Any) -> float:
    """"~7.20" / 7.2 -> 7.2. The "~" estimate marker lives on is_estimate,
    not the numeric value — see notes/datasets/nutrition/README.md."""
    return float(str(value).lstrip("~"))


def food_lookup(dataset: dict, food_id: str) -> dict:
    food = dataset["foods"].get(food_id)
    if food is None:
        raise NutritionDataError(f'unknown food id "{food_id}"')
    price = dataset["prices"].get(food_id)
    micronutrients = {f: food[f] for f in MICRONUTRIENT_FIELDS if food.get(f) is not None}
    return {
        "id": food["id"],
        "name": food["name"],
        "basis": food["basis"],
        "macros": {f: food.get(f) for f in MACRO_FIELDS},
        "glycemic_index": food.get("glycemic_index"),
        "price": None if price is None else f'{"~" if price.get("is_estimate") else ""}RM{parse_cost(price["unit_cost_myr"])} / {price["unit"].removeprefix("per ")}',
        "source": food.get("source"),
        "last_verified": food.get("last_verified"),
        "micronutrients": micronutrients,
        "micronutrient_source": food.get("micronutrient_source"),
        "micronutrient_fdc_id": food.get("micronutrient_fdc_id"),
    }
