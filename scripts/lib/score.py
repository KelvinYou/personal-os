"""Deterministic base score computation (D4).

Computes the mechanical portion of the four-dimension rubric. AI handles
qualitative bonus/penalty and criteria flagged as AI-filled (target=1.0
with no observable metric from the pipeline).

compute_base_score(agg, rubric, extra) → ScoreBreakdown

`extra` is a dict of AI-supplied subjective scores (0-1) for criteria like
`output_quality` / `blocker_management` / `crisis_handling` — safe to omit
for backfill/replay where only the mechanical part is needed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from statistics import pstdev
from typing import Iterable

from .metrics import WeeklyAggregate
from .schema import DailyLog, Scoring, ScoringDim, ScoringFormula


@dataclass
class CriterionScore:
    name: str
    max_points: float
    points: float
    formula: str
    basis: float | None = None  # the observable input value


@dataclass
class DimensionScore:
    name: str
    max_points: float
    points: float
    criteria: list[CriterionScore] = field(default_factory=list)


@dataclass
class ScoreBreakdown:
    output: DimensionScore
    health: DimensionScore
    mental: DimensionScore
    habits: DimensionScore

    @property
    def total(self) -> float:
        return self.output.points + self.health.points + self.mental.points + self.habits.points

    def summary_line(self) -> str:
        return (
            f"Base Score (deterministic): Output {self.output.points:.1f}/{self.output.max_points:.0f} · "
            f"Health {self.health.points:.1f}/{self.health.max_points:.0f} · "
            f"Mental {self.mental.points:.1f}/{self.mental.max_points:.0f} · "
            f"Habits {self.habits.points:.1f}/{self.habits.max_points:.0f} = "
            f"{self.total:.1f}/100"
        )


def _apply_proportional(basis: float, target: float, max_points: float) -> float:
    if target <= 0:
        return 0.0
    pts = basis / target * max_points
    return max(0.0, min(max_points, pts))


def _apply_threshold(basis: float, thresholds: list[list[float]], else_points: float, max_points: float) -> float:
    """Cutoffs are `basis <= cutoff` → `pts`. First match wins."""
    for cutoff, pts in thresholds:
        if basis <= cutoff:
            return min(float(pts), max_points)
    return min(float(else_points), max_points)


def _apply_inverse_proportional(basis: float, target: float, scale: float, max_points: float) -> float:
    """max * max(0, 1 - (basis - target) / scale). Points decay linearly past target."""
    if scale <= 0:
        return max_points if basis <= target else 0.0
    factor = max(0.0, 1.0 - (basis - target) / scale)
    pts = max_points * factor
    return max(0.0, min(max_points, pts))


def _apply(formula: ScoringFormula, basis: float) -> float:
    if formula.formula == "proportional":
        target = formula.target_hours if formula.target_hours is not None else formula.target
        if target is None:
            return 0.0
        return _apply_proportional(basis, target, formula.max_points)
    if formula.formula == "threshold":
        if not formula.thresholds:
            return 0.0
        return _apply_threshold(basis, formula.thresholds, formula.else_points, formula.max_points)
    if formula.formula == "inverse_proportional":
        target = formula.target if formula.target is not None else 0.0
        scale = formula.scale if formula.scale is not None else 1.0
        return _apply_inverse_proportional(basis, target, scale, formula.max_points)
    return 0.0


def _score_dim(
    name: str,
    dim: ScoringDim,
    bases: dict[str, float | None],
) -> DimensionScore:
    criteria_scores: list[CriterionScore] = []
    total = 0.0
    for crit_name, formula in dim.criteria.items():
        basis = bases.get(crit_name)
        if basis is None:
            pts = 0.0
        else:
            pts = _apply(formula, basis)
        total += pts
        criteria_scores.append(CriterionScore(
            name=crit_name,
            max_points=formula.max_points,
            points=pts,
            formula=formula.formula,
            basis=basis,
        ))
    return DimensionScore(name=name, max_points=dim.max_points, points=total, criteria=criteria_scores)


def sleep_duration_stddev(logs: Iterable[DailyLog]) -> float | None:
    xs = [l.sleep.duration for l in logs if l.sleep.duration is not None]
    if len(xs) < 2:
        return None
    return pstdev(xs)


def caffeine_compliance_rate(logs: Iterable[DailyLog], cutoff: str = "14:00") -> float | None:
    """Fraction of days with caffeine_cutoff at or before `cutoff` (HH:MM string compare)."""
    observed = [l.caffeine_cutoff for l in logs if l.caffeine_cutoff and str(l.caffeine_cutoff).strip()]
    if not observed:
        return None
    good = sum(1 for c in observed if str(c).strip() <= cutoff)
    return good / len(observed)


def compute_base_score(
    agg: WeeklyAggregate,
    week_logs: list[DailyLog],
    rubric: Scoring,
    subjective: dict[str, float] | None = None,
) -> ScoreBreakdown:
    """Compute base score given aggregated metrics + the week's logs.

    `subjective` maps criterion name → 0-1 score. Any criterion left unsupplied
    defaults to 0 (AI can fill in the qualitative pass and re-score).
    """
    subj = subjective or {}

    def flat(crit: str, default: float = 0.0) -> float:
        return float(subj.get(crit, default))

    stddev = sleep_duration_stddev(week_logs)
    caff = caffeine_compliance_rate(week_logs, cutoff="14:00")

    output_bases = {
        "deep_work": agg.total_deep_work,
        "output_quality": flat("output_quality"),
        "blocker_management": flat("blocker_management"),
    }
    health_bases = {
        "avg_energy": agg.avg_energy,
        "poor_sleep_days": float(agg.poor_sleep_days),
        "rolling_sleep_debt": agg.rolling_7d_sleep_debt,
        "sleep_structure": flat("sleep_structure"),
        "body_composition": flat("body_composition"),
    }
    mental_bases = {
        "avg_mental_load": agg.avg_mental_load,
        "crisis_handling": flat("crisis_handling"),
        "emotional_resilience": flat("emotional_resilience"),
    }
    habits_bases: dict[str, float | None] = {
        "weekly_spend": agg.total_spend,
        "caffeine_compliance": caff,
        "sleep_duration_consistency": stddev,
    }

    if rubric.output is None or rubric.health is None or rubric.mental is None or rubric.habits is None:
        raise ValueError("thresholds.yaml scoring block is missing dimension rubrics")

    return ScoreBreakdown(
        output=_score_dim("Output", rubric.output, output_bases),
        health=_score_dim("Health", rubric.health, health_bases),
        mental=_score_dim("Mental", rubric.mental, mental_bases),
        habits=_score_dim("Habits", rubric.habits, habits_bases),
    )


def format_breakdown_md(bs: ScoreBreakdown) -> str:
    lines = ["### Deterministic Base Score", "", bs.summary_line(), ""]
    for dim in (bs.output, bs.health, bs.mental, bs.habits):
        lines.append(f"**{dim.name}** ({dim.points:.1f}/{dim.max_points:.0f}):")
        for c in dim.criteria:
            basis_str = "—" if c.basis is None else f"{c.basis:.2f}"
            lines.append(f"  - {c.name} [{c.formula}]: basis={basis_str} → {c.points:.1f}/{c.max_points:.0f}")
        lines.append("")
    return "\n".join(lines)
