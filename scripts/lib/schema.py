"""Pydantic models: schema boundary for all frontmatter + thresholds."""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Sleep(BaseModel):
    model_config = ConfigDict(extra="forbid")
    duration: float | None = None
    deep_min: int | None = None
    light_min: int | None = None
    rem_min: int | None = None
    awake_min: int | None = None
    nap_min: int | None = None
    avg_hr: int | None = None
    min_hr: int | None = None
    max_hr: int | None = None


class Readiness(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hrv: float | None = None
    hrv_baseline: float | None = None
    rhr: int | None = None
    tired_rate: float | None = None
    ati: float | None = None
    cti: float | None = None
    load_ratio: float | None = None
    stamina_level: int | None = None
    performance: int | None = None


class Training(BaseModel):
    model_config = ConfigDict(extra="forbid")
    today_load: float | None = None
    vo2max: float | None = None
    lthr: int | None = None


class Activity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: str | None = None
    name: str | None = None
    duration_min: float | None = None
    distance_km: float | None = None
    avg_hr: int | None = None
    calories: int | None = None
    training_load: float | None = None
    elevation_m: float | None = None
    avg_power: int | None = None


class Body(BaseModel):
    model_config = ConfigDict(extra="forbid")
    weight: float | None = None
    body_fat_pct: float | None = None
    muscle_kg: float | None = None
    visceral_fat: int | None = None
    bmi: float | None = None
    water_pct: float | None = None
    protein_pct: float | None = None
    bone_mass_kg: float | None = None
    basal_metabolism: int | None = None


class DailySpend(BaseModel):
    model_config = ConfigDict(extra="forbid")
    amount: float | None = None
    category: str | None = None
    item: str | None = None
    note: str | None = None


class Adherence(BaseModel):
    """Timetable adherence flag — replaces narrative sections for plan-vs-reality tracking.

    timetable: ✅ = followed plan / ⚠️ = minor deviation / 🔴 = broke plan
    deviation_note: free-text root cause; expected only when timetable != ✅
    """
    model_config = ConfigDict(extra="forbid")
    timetable: Literal["✅", "⚠️", "🔴"] | None = None
    deviation_note: str | None = None


class DailyLog(BaseModel):
    """Frontmatter of a data/daily/YYYY-MM-DD.md file."""

    model_config = ConfigDict(extra="forbid")

    date: date  # derived from filename, not stored in frontmatter
    energy_level: int | None = Field(default=None, ge=1, le=10)
    deep_work_hours: float | None = None
    sleep: Sleep = Field(default_factory=Sleep)
    readiness: Readiness = Field(default_factory=Readiness)
    training: Training = Field(default_factory=Training)
    activities: list[Activity] = Field(default_factory=list)
    caffeine_cutoff: str | None = None
    primary_blocker: str | None = None
    daily_spend: list[DailySpend] = Field(default_factory=list)
    mental_load: int | None = Field(default=None, ge=1, le=7)
    body: Body = Field(default_factory=Body)
    adherence: Adherence = Field(default_factory=Adherence)

    @field_validator("activities", mode="before")
    @classmethod
    def _normalize_activities(cls, v: Any) -> Any:
        # YAML `activities: []` → []; `activities:` (None) → []
        if v is None:
            return []
        return v

    @field_validator("daily_spend", mode="before")
    @classmethod
    def _normalize_spend(cls, v: Any) -> Any:
        if v is None:
            return []
        return v

    @field_validator("sleep", "readiness", "training", "body", "adherence", mode="before")
    @classmethod
    def _normalize_nested(cls, v: Any) -> Any:
        if v is None:
            return {}
        return v


# --- Thresholds (config/thresholds.yaml) ---

class DeepWorkCfg(BaseModel):
    model_config = ConfigDict(extra="forbid")
    minimum_hours: float


class SleepCfg(BaseModel):
    model_config = ConfigDict(extra="allow")  # tolerate supplementary keys
    baseline_hours: float
    poor_sleep_duration_hours: float
    poor_sleep_hrv_ratio: float
    debt_window_days: int = 7
    debt_recovery_streak: int = 3
    ideal_range: list[float]
    poor_streak_alert: int = 3
    awake_min_warning: int | None = None
    nap_compensation_min: int | None = None
    deep_min_range: list[int] | None = None
    rem_min_range: list[int] | None = None
    hrv_warning_low: float | None = None


class ReadinessCfg(BaseModel):
    model_config = ConfigDict(extra="allow")
    hrv_rel_baseline_min: float | None = None
    load_ratio_overtraining: float | None = None
    tired_rate_warning: float | None = None


class EnergyCfg(BaseModel):
    model_config = ConfigDict(extra="allow")
    low_threshold: int
    warning_threshold: int


class FinanceCfg(BaseModel):
    model_config = ConfigDict(extra="allow")
    weekly_spend_alert: float
    daily_spend_alert: float | None = None
    savings_target_pct: float | None = None


class WealthCfg(BaseModel):
    # extra="allow" 是撒谎的：web/lib/report.ts 把 thresholds 声明为
    # Record<string, number>，而这里任何非 number 的值都能穿透（审计 §3.6 末）。
    model_config = ConfigDict(extra="forbid")
    maturity_alert_days: int = 30
    maturity_critical_days: int = 7
    staleness_warn_days: int = 30
    price_stale_days: int = 7
    # FX 比持仓变得快得多，所以它有自己的保质期，不跟 staleness_warn_days 混用。
    fx_stale_days: int = 1
    regulatory_rules_stale_days: int = 365
    rate_edge_min_pct: float = 0.25
    cap_utilization_warn: float = 0.90


class CaffeineCfg(BaseModel):
    model_config = ConfigDict(extra="allow")
    cutoff_time: str
    late_cutoff_time: str


class LoggingDefaultsCfg(BaseModel):
    """Baselines used to resolve *unfilled manual* fields (config/thresholds.yaml).

    Consumed by scripts/lib/defaults.py. Never applied to COROS blocks or body.*
    (see the三条边界 comment in thresholds.yaml), and never applied on the breaker
    path — alarms must fire on evidence, not on baselines.
    """
    model_config = ConfigDict(extra="forbid")
    enabled: bool = True
    effective_from: date | None = None
    energy_level: int | None = None
    mental_load: int | None = None
    deep_work_hours: float | None = None
    deep_work_hours_weekend: float | None = None
    caffeine_cutoff: str | None = None
    adherence: Literal["✅", "⚠️", "🔴"] | None = None
    daily_spend: float | None = None
    coverage_warn_ratio: float = 0.60
    adherence_drift_days: int


class BreakerCondition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    metric: str
    operator: str
    value: float


class Breaker(BaseModel):
    """一条熔断规则。

    ``enforcement`` 区分两类混在同一个 list 里的东西：
      - ``auto``     —— actions 是对时间表的硬约束（禁跑 / 降重 / DW 上限 / 断电时间），
                        coach-planner 排期时必须机械套用，不留判断余地。
      - ``advisory`` —— actions 是给 agent 读的 prose，engine 无法验证也无法执行。
                        照常评估并输出，但下游必须标注为「建议」而非「强制」。
    """
    model_config = ConfigDict(extra="allow")
    name: str
    description: str | None = None
    condition: BreakerCondition
    actions: list[str] = Field(default_factory=list)
    enforcement: Literal["auto", "advisory"] = "auto"


class ScoringFormula(BaseModel):
    """One scoring criterion. Supports proportional / threshold / inverse_proportional."""
    model_config = ConfigDict(extra="forbid")
    max_points: float
    formula: str  # "proportional" | "threshold" | "inverse_proportional"
    target: float | None = None
    target_hours: float | None = None
    thresholds: list[list[float]] | None = None  # [[cutoff, pts], ...]
    else_points: float = 0.0
    scale: float | None = None  # for inverse_proportional: fall-off span


class ScoringDim(BaseModel):
    model_config = ConfigDict(extra="allow")
    max_points: float
    criteria: dict[str, ScoringFormula] = Field(default_factory=dict)


class Scoring(BaseModel):
    model_config = ConfigDict(extra="allow")
    output_max: float
    health_max: float
    mental_max: float
    habits_max: float
    # optional deterministic rubric (D4)
    output: ScoringDim | None = None
    health: ScoringDim | None = None
    mental: ScoringDim | None = None
    habits: ScoringDim | None = None


class Thresholds(BaseModel):
    model_config = ConfigDict(extra="allow")
    deep_work: DeepWorkCfg
    sleep: SleepCfg
    energy: EnergyCfg
    finance: FinanceCfg
    wealth: WealthCfg = Field(default_factory=WealthCfg)
    caffeine: CaffeineCfg
    readiness: ReadinessCfg | None = None
    logging_defaults: LoggingDefaultsCfg = Field(default_factory=LoggingDefaultsCfg)
    circuit_breakers: list[Breaker] = Field(default_factory=list)
    scoring: Scoring


def parse_date_from_filename(path: Path) -> date:
    return date.fromisoformat(path.stem)
