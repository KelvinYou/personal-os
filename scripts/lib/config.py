"""Threshold loader with pydantic fail-fast validation."""
from __future__ import annotations

from pathlib import Path

import yaml

from .schema import Thresholds

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PATH = ROOT / "config" / "thresholds.yaml"


def load_thresholds(path: Path | str | None = None) -> Thresholds:
    p = Path(path) if path else DEFAULT_PATH
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    return Thresholds.model_validate(raw)
