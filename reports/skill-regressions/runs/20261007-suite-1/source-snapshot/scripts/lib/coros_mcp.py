"""Ephemeral evidence normalized by an official COROS MCP client.

This is our internal input format, not COROS's wire format. The client owns
OAuth/tool calls and verifies field meanings, units and dates before mapping.
No fetching, credentials or daily-log writes live here.
"""
from __future__ import annotations

import json
import math
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .metrics import latest_metrics
from .daily_log import consecutive_poor
from .schema import Activity, DailyLog, Readiness, Sleep, Training


class Observation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    date: date
    tools: list[str] = Field(min_length=1)
    sleep: Sleep = Field(default_factory=Sleep)
    readiness: Readiness = Field(default_factory=Readiness)
    training: Training = Field(default_factory=Training)
    activities: list[Activity] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_measurements(self):
        for block in (self.sleep, self.readiness, self.training, *self.activities):
            for value in block.model_dump().values():
                if isinstance(value, (int, float)) and not math.isfinite(value):
                    raise ValueError("Measurements must be finite")
        if self.sleep.duration is not None and not 0 <= self.sleep.duration <= 24:
            raise ValueError("sleep.duration must be main-sleep hours in [0, 24]")
        if any(not tool.strip() for tool in self.tools):
            raise ValueError("Tool provenance must not be blank")
        return self

    def has_evidence(self) -> bool:
        return "activities" in self.model_fields_set or any(
            value is not None
            for block in (self.sleep, self.readiness, self.training)
            for value in block.model_dump().values()
        )


class CorosSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: Literal["coros-official-mcp"]
    retrieved_at: datetime
    period_start: date
    period_end: date
    records: list[Observation]

    @model_validator(mode="after")
    def validate_period(self):
        if self.retrieved_at.utcoffset() is None:
            raise ValueError("retrieved_at requires a timezone offset")
        if self.period_start > self.period_end:
            raise ValueError("Invalid query period")
        days = [record.date for record in self.records]
        if len(set(days)) != len(days):
            raise ValueError("Duplicate observation dates")
        if any(not self.period_start <= day <= self.period_end for day in days):
            raise ValueError("Observation outside query period")
        return self

    def merge(self, local_logs: list[DailyLog]) -> list[DailyLog]:
        """Keep manual facts, clearing historical health instead of filling gaps."""
        logs = {}
        for log in local_logs:
            if self.period_start <= log.date <= self.period_end:
                logs[log.date] = DailyLog.model_validate({
                    **log.model_dump(), "sleep": {}, "readiness": {},
                    "training": {}, "activities": [], "coros_synced": None,
                })
        for record in self.records:
            if not record.has_evidence():
                continue
            base = logs.get(record.date, DailyLog(date=record.date))
            logs[record.date] = DailyLog.model_validate({
                **base.model_dump(),
                **record.model_dump(exclude={"date", "tools"}),
                "coros_synced": True,
            })
        return sorted(logs.values(), key=lambda log: log.date)

    def metrics(self, logs: list[DailyLog], cfg, ref: date) -> dict:
        metrics = latest_metrics(logs, cfg.sleep.baseline_hours,
                                 cfg.sleep.debt_window_days, sleep_cfg=cfg.sleep)
        current = next((r for r in self.records if r.date == ref), None)
        for key, value in {
            "sleep_duration": current.sleep.duration if current else None,
            "hrv": current.readiness.hrv if current else None,
            "load_ratio": current.readiness.load_ratio if current else None,
            "tired_rate": current.readiness.tired_rate if current else None,
        }.items():
            metrics.pop(key, None)
            if value is not None:
                metrics[key] = value
        lo = ref - timedelta(days=cfg.sleep.debt_window_days - 1)
        sleep_days = sum(lo <= r.date <= ref and r.sleep.duration is not None
                         for r in self.records)
        if not sleep_days:
            metrics.pop("rolling_7d_sleep_debt", None)
        if current is None or current.sleep.duration is None:
            metrics.pop("consecutive_poor_sleep", None)
        else:
            metrics["consecutive_poor_sleep"] = consecutive_poor(
                [log for log in logs if log.date <= ref and log.sleep.duration is not None],
                cfg.sleep,
            )
        return metrics

    def summary(self) -> str:
        days = sum(record.has_evidence() for record in self.records)
        return (f"COROS official MCP; queried {self.period_start}..{self.period_end}; "
                f"retrieved {self.retrieved_at.isoformat()}; {days} observed health days. "
                "Missing data is unknown; partial sleep debt is an observed lower bound.")


def load_snapshot(input_path: str) -> CorosSnapshot:
    raw = sys.stdin.read() if input_path == "-" else Path(input_path).read_text(encoding="utf-8")
    return CorosSnapshot.model_validate(json.loads(raw))
