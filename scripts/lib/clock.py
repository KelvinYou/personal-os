"""Project clock helpers.

All user-facing dates are calendar dates in Kuala Lumpur, not the machine's
local timezone. Keeping this in one module prevents a midnight boundary from
splitting a daily log, decision review, or archive run into different days.
"""
from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

KL_TIMEZONE = ZoneInfo("Asia/Kuala_Lumpur")


def today_kl() -> date:
    return datetime.now(KL_TIMEZONE).date()


def now_kl() -> datetime:
    return datetime.now(KL_TIMEZONE)
