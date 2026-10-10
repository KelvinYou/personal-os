"""Small, explicit, unit-aware formula evaluator for registered claims."""
from __future__ import annotations

from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP
from itertools import product
from typing import Mapping

from .models import FormulaOperation, FormulaSpec, Quantity


class FormulaError(ValueError):
    """Raised when a derivation is outside the safe formula allow-list."""


def _bounds(quantity: Quantity) -> tuple[Decimal, Decimal]:
    if quantity.scalar is not None:
        return quantity.scalar, quantity.scalar
    assert quantity.lower is not None and quantity.upper is not None
    return quantity.lower, quantity.upper


def _round(value: Decimal, precision: int, *, direction: str = "nearest") -> Decimal:
    quantum = Decimal(1).scaleb(-precision)
    mode = {
        "nearest": ROUND_HALF_UP,
        "floor": ROUND_FLOOR,
        "ceiling": ROUND_CEILING,
    }[direction]
    return value.quantize(quantum, rounding=mode)


def _result(
    lower: Decimal,
    upper: Decimal,
    *,
    unit: str,
    precision: int,
    scalar: bool,
) -> Quantity:
    if scalar:
        return Quantity(
            scalar=_round(lower, precision), unit=unit, precision=precision
        )
    return Quantity(
        lower=_round(lower, precision, direction="floor"),
        upper=_round(upper, precision, direction="ceiling"),
        unit=unit,
        precision=precision,
    )


def evaluate_formula(
    formula: FormulaSpec,
    quantities: Mapping[str, Quantity],
) -> Quantity:
    """Evaluate one allow-listed formula without executing arbitrary code."""
    if len(formula.operands) != len(set(formula.operands)):
        raise FormulaError("formula operands must be unique")
    missing = [key for key in formula.operands if key not in quantities]
    if missing:
        raise FormulaError(f"formula operands missing: {', '.join(missing)}")

    values = [quantities[key] for key in formula.operands]
    bounds = [_bounds(value) for value in values]
    scalar = all(value.scalar is not None for value in values)
    operation = formula.operation

    if operation in {
        FormulaOperation.ADD,
        FormulaOperation.SUBTRACT,
        FormulaOperation.MULTIPLY,
        FormulaOperation.MIN,
        FormulaOperation.MAX,
    } and len(values) < 2:
        raise FormulaError(f"{operation.value} requires at least two operands")
    if formula.rounding > max(value.precision for value in values):
        raise FormulaError(
            "formula rounding cannot add precision beyond its operands"
        )

    if operation in {
        FormulaOperation.ADD,
        FormulaOperation.SUBTRACT,
        FormulaOperation.MIN,
        FormulaOperation.MAX,
    }:
        if any(value.unit != values[0].unit for value in values):
            raise FormulaError(f"{operation.value} requires compatible units")
        if formula.output_unit != values[0].unit:
            raise FormulaError("formula output_unit must match arithmetic operands")

    if operation is FormulaOperation.ADD:
        lower = sum((pair[0] for pair in bounds), Decimal(0))
        upper = sum((pair[1] for pair in bounds), Decimal(0))
    elif operation is FormulaOperation.SUBTRACT:
        if len(bounds) < 2:
            raise FormulaError("subtract requires at least two operands")
        lower = bounds[0][0] - sum((pair[1] for pair in bounds[1:]), Decimal(0))
        upper = bounds[0][1] - sum((pair[0] for pair in bounds[1:]), Decimal(0))
    elif operation is FormulaOperation.MULTIPLY:
        if len(bounds) < 2:
            raise FormulaError("multiply requires at least two operands")
        products = [
            _product(combo)
            for combo in product(*bounds)
        ]
        lower, upper = min(products), max(products)
    elif operation in {FormulaOperation.DIVIDE, FormulaOperation.RATIO}:
        if len(bounds) != 2:
            raise FormulaError(f"{operation.value} requires exactly two operands")
        denominator_lower, denominator_upper = bounds[1]
        if denominator_lower <= 0 <= denominator_upper:
            raise FormulaError("division denominator may be zero")
        ratios = [
            numerator / denominator
            for numerator, denominator in product(bounds[0], bounds[1])
        ]
        lower, upper = min(ratios), max(ratios)
    elif operation is FormulaOperation.MIN:
        lower = min(pair[0] for pair in bounds)
        upper = min(pair[1] for pair in bounds)
    elif operation is FormulaOperation.MAX:
        lower = max(pair[0] for pair in bounds)
        upper = max(pair[1] for pair in bounds)
    else:  # pragma: no cover - Enum makes this unreachable
        raise FormulaError(f"unsupported operation: {operation}")

    return _result(
        lower,
        upper,
        unit=formula.output_unit,
        precision=formula.rounding,
        scalar=scalar,
    )


def _product(values: tuple[Decimal, ...]) -> Decimal:
    result = Decimal(1)
    for value in values:
        result *= value
    return result
