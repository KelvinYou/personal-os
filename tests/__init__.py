"""Run public tests against synthetic fixtures, never an owner's private data."""
import os
from pathlib import Path

_config = Path(__file__).resolve().parent / "fixtures" / "config"
os.environ["PERSONAL_OS_THRESHOLDS_PATH"] = str(_config / "thresholds.yaml")
os.environ["PERSONAL_OS_SETTINGS_PATH"] = str(_config / "settings.yaml")
