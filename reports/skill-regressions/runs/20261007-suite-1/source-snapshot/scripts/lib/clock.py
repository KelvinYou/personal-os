"""Project clock helpers using the owner's private timezone setting."""
from __future__ import annotations

from datetime import date, datetime
import os
from pathlib import Path
from zoneinfo import ZoneInfo
import yaml

SETTINGS_PATH = Path(__file__).resolve().parents[2] / "data" / "config" / "settings.yaml"


def user_timezone(path: Path | None = None) -> ZoneInfo:
    target = path or Path(os.environ.get("PERSONAL_OS_SETTINGS_PATH", SETTINGS_PATH))
    if not target.is_file():
        raise FileNotFoundError(f"Private settings missing: {target}. Configure data/config/settings.yaml.")
    settings = yaml.safe_load(target.read_text(encoding="utf-8"))
    if not isinstance(settings, dict) or not settings.get("timezone") or settings.get("owner_configured") is not True:
        raise ValueError(f"Set timezone and owner_configured: true in {target} after reviewing it")
    return ZoneInfo(str(settings["timezone"]))


def today_kl() -> date:
    return datetime.now(user_timezone()).date()


def now_kl() -> datetime:
    return datetime.now(user_timezone())
