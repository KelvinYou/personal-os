"""Threshold loader with pydantic fail-fast validation."""
from __future__ import annotations

from pathlib import Path
import os

import yaml

from .schema import Thresholds

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PATH = ROOT / "data" / "config" / "thresholds.yaml"


def load_thresholds(path: Path | str | None = None) -> Thresholds:
    p = Path(path) if path else Path(os.environ.get("PERSONAL_OS_THRESHOLDS_PATH", DEFAULT_PATH))
    if not p.is_file():
        raise FileNotFoundError(f"Private thresholds missing: {p}. Run make setup-private and configure data/config/thresholds.yaml.")
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("owner_configured") is not True:
        raise ValueError(f"Set owner_configured: true in {p} after reviewing every personal threshold.")
    return Thresholds.model_validate(raw)
