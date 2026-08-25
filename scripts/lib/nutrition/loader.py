from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .errors import NutritionSourceMissing

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATASET_DIR = REPO_ROOT / "repos" / "notes" / "datasets" / "nutrition"


def _load_yaml_dir(dir_path: Path) -> list[dict[str, Any]]:
    if not dir_path.exists():
        return []
    records: list[dict[str, Any]] = []
    for f in sorted(dir_path.glob("*.yaml")):
        doc = yaml.safe_load(f.read_text(encoding="utf-8"))
        if isinstance(doc, list):
            records.extend(doc)
    return records


def load_dataset(dataset_dir: Path | None = None) -> dict[str, dict]:
    """Loads foods/prices, keyed by id/food_id. Raises NutritionSourceMissing
    if the dataset directory doesn't exist (submodule not checked out)."""
    dir_path = dataset_dir or DEFAULT_DATASET_DIR
    if not dir_path.exists():
        raise NutritionSourceMissing(
            f"{dir_path} not found. Run: git submodule update --init repos/notes"
        )

    foods = {f["id"]: f for f in _load_yaml_dir(dir_path / "foods")}
    prices = {p["food_id"]: p for p in _load_yaml_dir(dir_path / "prices")}
    return {"foods": foods, "prices": prices}
