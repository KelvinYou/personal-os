"""Policy audit and cash-only planning. No prices, investment forecasts or trades."""
from __future__ import annotations

import hashlib
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

from .files import FINANCE_DIR

def cents_only(value: float) -> float:
    if Decimal(str(value)) != Decimal(str(value)).quantize(Decimal(".01")):
        raise ValueError("Money inputs support at most two decimal places")
    return value


Money = Annotated[float, Field(ge=0, strict=True), AfterValidator(cents_only)]
Percent = Annotated[float, Field(ge=0, le=100, strict=True)]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, str_strip_whitespace=True, json_schema_serialization_defaults_required=True)


class EmergencyPolicy(Model):
    target_months: float | None = Field(default=None, gt=0, strict=True)
    monthly_required_expenses: Money | None = None


class CashPolicy(Model):
    monthly_investable_amount: Money | None = None


class AllocationPolicy(Model):
    equity_target_pct_of_tracked_investable_assets: Percent | None = None
    rebalance_band_percentage_points: Percent | None = None


class SleevePolicy(Model):
    core_target_pct: Percent | None = None
    satellite_target_pct: Percent | None = None

    @model_validator(mode="after")
    def total(self):
        if self.core_target_pct is not None and self.satellite_target_pct is not None and abs(self.core_target_pct + self.satellite_target_pct - 100) > .000001:
            raise ValueError("Core and satellite targets must total 100")
        return self


class ConcentrationPolicy(Model):
    max_single_position_pct_of_equity: Percent | None = None
    max_sector_pct_of_equity: Percent | None = None
    max_usd_pct_of_tracked_investable_assets: Percent | None = None


class ConstraintsPolicy(Model):
    us_situs_warning_buffer_pct: Percent | None = None


class TaxPolicy(Model):
    marginal_tax_rate_pct: Percent | None = None
    prs_status: Literal["unused", "used", "not_applicable"] | None = None
    us_estate_applicability: Literal["nonresident_noncitizen", "not_applicable", "unknown"] | None = None


class Policy(Model):
    schema_version: Literal[1] = 1
    base_currency: Literal["MYR"] = "MYR"
    emergency_fund: EmergencyPolicy = Field(default_factory=EmergencyPolicy)
    cash_flow: CashPolicy = Field(default_factory=CashPolicy)
    allocation: AllocationPolicy = Field(default_factory=AllocationPolicy)
    equity_sleeve: SleevePolicy = Field(default_factory=SleevePolicy)
    concentration: ConcentrationPolicy = Field(default_factory=ConcentrationPolicy)
    constraints: ConstraintsPolicy = Field(default_factory=ConstraintsPolicy)
    tax: TaxPolicy = Field(default_factory=TaxPolicy)


class PolicyAudit(Model):
    state: Literal["configured", "missing", "invalid"]
    source: Literal["data/finance/policy.yaml"] = "data/finance/policy.yaml"
    policy: Policy | None
    fingerprint: str | None
    missing_keys: list[str]
    currency: Literal["MYR"] = "MYR"
    # Existing policy has no verified-at contract; file mtime never substitutes for it.
    verified_at: None = None
    message: str


def fingerprint(policy: Policy) -> str:
    return hashlib.sha256(policy.model_dump_json().encode()).hexdigest()


def audit_policy(path: Path = FINANCE_DIR / "policy.yaml") -> PolicyAudit:
    if not path.exists():
        return PolicyAudit(state="missing", policy=None, fingerprint=None, missing_keys=[], message="Policy is missing. Planning needs explicit inputs; no targets were assumed.")
    try:
        policy = Policy.model_validate(yaml.safe_load(path.read_text()))
    except (ValueError, OSError, yaml.YAMLError):
        return PolicyAudit(state="invalid", policy=None, fingerprint=None, missing_keys=[], message="Policy cannot be validated. Correct its schema before accepting an allocation.")
    missing = [f"{section}.{key}" for section, values in policy.model_dump().items() if isinstance(values, dict) for key, value in values.items() if value is None]
    return PolicyAudit(state="configured", policy=policy, fingerprint=fingerprint(policy), missing_keys=missing, message="Configured values have no verification date. Confirm current assumptions for each worksheet.")


class ConfirmedInput(Model):
    as_of: date
    assumptions_confirmed: bool = Field(strict=True)

    @model_validator(mode="after")
    def confirmed(self):
        if self.assumptions_confirmed is not True:
            raise ValueError("Confirm current input assumptions before saving")
        return self


class AllocationInput(ConfirmedInput):
    available_after_bills_myr: Money
    near_term_need_myr: Money
    protected_reserve_myr: Money


class AllocationResult(Model):
    emergency_target_myr: Money
    near_term_allocation_myr: Money
    near_term_unfunded_myr: Money
    emergency_allocation_myr: Money
    emergency_remaining_gap_myr: Money
    unassigned_myr: Money
    warnings: list[str]


class ScenarioInput(ConfirmedInput):
    starting_cash_myr: Money
    monthly_income_myr: Money
    monthly_expenses_myr: Money
    protected_buffer_myr: Money
    one_off_cost_myr: Money
    extra_monthly_expense_myr: Money
    income_pause_months: int = Field(ge=0, le=60, strict=True)
    horizon_months: int = Field(ge=1, le=60, strict=True)


class CashMonth(Model):
    month: int
    baseline_myr: float
    alternative_myr: float


class ScenarioResult(Model):
    months: list[CashMonth]
    baseline_end_myr: float
    alternative_end_myr: float
    minimum_alternative_myr: float
    end_difference_myr: float
    first_buffer_breach_month: int | None
    scope: Literal["Cash only; no investment returns, tax estimates or financial execution."] = "Cash only; no investment returns, tax estimates or financial execution."


def money(value) -> float:
    return float(Decimal(str(value)).quantize(Decimal(".01"), rounding=ROUND_HALF_UP))


def allocate(inputs: AllocationInput, policy: Policy) -> AllocationResult:
    ef = policy.emergency_fund
    if ef.target_months is None or ef.monthly_required_expenses is None:
        raise ValueError("Emergency target months and monthly expenses are required in policy")
    target = money(Decimal(str(ef.target_months)) * Decimal(str(ef.monthly_required_expenses)))
    near = min(inputs.available_after_bills_myr, inputs.near_term_need_myr)
    remaining = money(inputs.available_after_bills_myr - near)
    gap = max(0, money(target - inputs.protected_reserve_myr))
    emergency = min(remaining, gap)
    return AllocationResult(emergency_target_myr=target, near_term_allocation_myr=money(near), near_term_unfunded_myr=money(inputs.near_term_need_myr - near), emergency_allocation_myr=money(emergency), emergency_remaining_gap_myr=money(gap - emergency), unassigned_myr=money(remaining - emergency), warnings=["Available amount must already exclude usual bills. Existing protected reserve is separate from this cycle's available money.", "Unassigned is not an investment instruction. Target ratios, earmarks and account evidence still need review."])


def compare(inputs: ScenarioInput) -> ScenarioResult:
    base = alternate = money(inputs.starting_cash_myr)
    rows = [CashMonth(month=0, baseline_myr=base, alternative_myr=alternate)]
    for month in range(1, inputs.horizon_months + 1):
        base = money(Decimal(str(base)) + Decimal(str(inputs.monthly_income_myr)) - Decimal(str(inputs.monthly_expenses_myr)))
        income = 0 if month <= inputs.income_pause_months else inputs.monthly_income_myr
        alternate = money(Decimal(str(alternate)) + Decimal(str(income)) - Decimal(str(inputs.monthly_expenses_myr)) - Decimal(str(inputs.extra_monthly_expense_myr)) - Decimal(str(inputs.one_off_cost_myr if month == 1 else 0)))
        rows.append(CashMonth(month=month, baseline_myr=base, alternative_myr=alternate))
    return ScenarioResult(months=rows, baseline_end_myr=base, alternative_end_myr=alternate, minimum_alternative_myr=min(r.alternative_myr for r in rows), end_difference_myr=money(alternate - base), first_buffer_breach_month=next((r.month for r in rows if r.alternative_myr < inputs.protected_buffer_myr), None))
