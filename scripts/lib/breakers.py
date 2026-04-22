"""Single entry point for circuit breaker evaluation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .schema import Breaker


_OPS: dict[str, Callable[[float, float], bool]] = {
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "==": lambda a, b: a == b,
}


@dataclass
class TrippedBreaker:
    name: str
    metric: str
    actual: float
    operator: str
    threshold: float
    actions: list[str]


def evaluate(metrics: dict, breakers: list[Breaker]) -> list[TrippedBreaker]:
    tripped: list[TrippedBreaker] = []
    for cb in breakers:
        cond = cb.condition
        actual = metrics.get(cond.metric)
        if actual is None:
            # missing data — skip to avoid false positives
            continue
        op_fn = _OPS.get(cond.operator)
        if op_fn is None:
            continue
        if op_fn(float(actual), float(cond.value)):
            tripped.append(TrippedBreaker(
                name=cb.name,
                metric=cond.metric,
                actual=float(actual),
                operator=cond.operator,
                threshold=float(cond.value),
                actions=list(cb.actions),
            ))
    return tripped
