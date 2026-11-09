"""Finance manager research proposals: a deterministic buy-vs-rent projection.

The Finance manager (wealth-manager skill) writes a private proposal file with
inputs and a prose recommendation; this module owns every number shown for it.
The owner's review is an append-only event; nothing here moves money.
See docs/design/finance-research.md.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .files import FINANCE_DIR, ROOT

STRICT = ConfigDict(extra="forbid", allow_inf_nan=False, str_strip_whitespace=True, json_schema_serialization_defaults_required=True)
RESEARCH_DIR = FINANCE_DIR / "research"
POSTS_DIR = ROOT / "data" / "posts"
RULES_PATH = ROOT / "config" / "research" / "kl_rent_vs_buy.yaml"
ID = Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9-]{0,79}$")]
Rate = Annotated[float, Field(ge=-0.5, le=0.5)]
Money = Annotated[float, Field(ge=0, le=1e9)]
Text = Annotated[str, Field(min_length=1, max_length=600)]


class Model(BaseModel):
    model_config = STRICT


class ResearchError(Exception):
    def __init__(self, code: str, status: int = 400):
        super().__init__(code)
        self.code, self.status = code, status


# ---- Public market rules (config/research/kl_rent_vs_buy.yaml) ----

class Tier(Model):
    up_to: float | None = Field(description="Upper bound of this slice in MYR; null for the last slice")
    rate: Annotated[float, Field(ge=0, le=0.2)]


class Source(Model):
    label: Text
    url: Annotated[str, Field(pattern=r"^https://", max_length=500)]
    verified_at: date


class PurchaseRules(Model):
    transfer_stamp_tiers: list[Tier] = Field(min_length=1)
    loan_stamp_rate: Annotated[float, Field(ge=0, le=0.05)]
    legal_fee_tiers: list[Tier] = Field(min_length=1)
    legal_fee_tax_rate: Annotated[float, Field(ge=0, le=0.2)] = Field(description="Service tax charged on legal fees")
    first_home_exemption_cap: Money = Field(description="Price at or below which a qualifying first home pays no transfer or loan stamp duty")
    rpgt_by_holding_year: list[Annotated[float, Field(ge=0, le=0.5)]] = Field(min_length=1, description="Index 0 = disposal in year 1; later years use 0")
    sources: list[Source] = Field(min_length=1)
    verified_at: date
    fresh_days: int = Field(ge=1, le=730)


def sliced(amount: float, tiers: list[Tier]) -> float:
    total, floor = 0.0, 0.0
    for tier in tiers:
        top = amount if tier.up_to is None else min(amount, tier.up_to)
        if top > floor:
            total += (top - floor) * tier.rate
        if tier.up_to is None or amount <= tier.up_to:
            break
        floor = tier.up_to
    return total


def load_rules(path: Path = RULES_PATH) -> PurchaseRules:
    return PurchaseRules.model_validate(yaml.safe_load(path.read_text(encoding="utf-8"))["rules"])


# ---- Inputs and result ----

class Range(Model):
    low: Rate
    base: Rate
    high: Rate

    @model_validator(mode="after")
    def ordered(self):
        if not self.low <= self.base <= self.high:
            raise ValueError("Range must satisfy low <= base <= high")
        return self


class RentVsBuyInputs(Model):
    horizon_years: int = Field(ge=1, le=35)
    property_price: Annotated[float, Field(gt=0, le=1e8)]
    loan_margin: Annotated[float, Field(ge=0, le=1)]
    loan_rate: Annotated[float, Field(ge=0, le=0.2)]
    loan_tenure_years: int = Field(ge=1, le=35)
    first_home_exemption: bool
    other_purchase_costs: Money = Field(description="Valuation, disbursements, insurance set-up")
    renovation: Money
    maintenance_monthly: Money = Field(description="Maintenance plus sinking fund")
    property_tax_yearly: Money = Field(description="Quit rent plus assessment")
    insurance_yearly: Money
    repair_rate: Annotated[float, Field(ge=0, le=0.05)] = Field(description="Repairs per year as a share of property value")
    room_income_monthly: Money = Field(description="Rent from spare rooms the buyer lets out")
    cost_growth: Rate = Field(description="Annual growth of maintenance, taxes and insurance")
    property_growth: Range
    selling_cost_rate: Annotated[float, Field(ge=0, le=0.2)]
    rent_monthly: Money
    rent_growth: Rate
    etf_return: Range = Field(description="Gross nominal annual total return")
    etf_cost_drag: Annotated[float, Field(ge=0, le=0.05)] = Field(description="Fund fee plus dividend withholding drag per year")
    inflation: Annotated[float, Field(ge=-0.05, le=0.2)]


class Upfront(Model):
    down_payment: float
    transfer_stamp_duty: float
    loan_stamp_duty: float
    legal_fees: float
    other: float
    renovation: float
    total: float
    loan: float
    monthly_instalment: float


class YearRow(Model):
    year: int
    property_value: float
    loan_balance: float
    sale_costs: float = Field(description="Agent, legal and RPGT if sold at this year end")
    home_equity: float = Field(description="Value minus loan minus sale costs")
    buyer_portfolio: float = Field(description="ETF bought with any monthly surplus the buyer had")
    buy_net_worth: float
    rent_net_worth: float
    gap: float = Field(description="Buy minus rent; positive means buying is ahead")
    owner_monthly_cost: float = Field(description="Average monthly cost of owning during this year")
    rent_monthly: float
    deflator: float = Field(description="Divide by this for today's ringgit")


class Scenario(Model):
    property_growth: float
    etf_return: float
    rows: list[YearRow]
    final_gap: float
    first_buy_ahead_year: int | None = Field(description="First year from which buying stays ahead to the horizon")


class RentVsBuyResult(Model):
    upfront: Upfront
    property_growth_levels: list[float]
    etf_return_levels: list[float]
    scenarios: list[Scenario] = Field(description="Row-major: property growth level × ETF return level")
    base_index: int
    breakeven_property_growth: float | None = Field(description="Property growth that ties the two paths at the horizon, base ETF return")
    inputs_fingerprint: str


def fingerprint(inputs: RentVsBuyInputs) -> str:
    return hashlib.sha256(json.dumps(inputs.model_dump(mode="json"), sort_keys=True).encode()).hexdigest()[:16]


def upfront_costs(i: RentVsBuyInputs, rules: PurchaseRules) -> Upfront:
    loan = i.property_price * i.loan_margin
    exempt = i.first_home_exemption and i.property_price <= rules.first_home_exemption_cap
    transfer = 0.0 if exempt else sliced(i.property_price, rules.transfer_stamp_tiers)
    loan_duty = 0.0 if exempt else loan * rules.loan_stamp_rate
    legal = (sliced(i.property_price, rules.legal_fee_tiers) + (sliced(loan, rules.legal_fee_tiers) if loan else 0.0)) * (1 + rules.legal_fee_tax_rate)
    down = i.property_price - loan
    n, r = i.loan_tenure_years * 12, i.loan_rate / 12
    instalment = 0.0 if not loan else (loan / n if r == 0 else loan * r / (1 - (1 + r) ** -n))
    total = down + transfer + loan_duty + legal + i.other_purchase_costs + i.renovation
    return Upfront(down_payment=down, transfer_stamp_duty=transfer, loan_stamp_duty=loan_duty, legal_fees=legal,
                   other=i.other_purchase_costs, renovation=i.renovation, total=total, loan=loan, monthly_instalment=instalment)


def simulate(i: RentVsBuyInputs, rules: PurchaseRules, up: Upfront, growth: float, etf: float) -> Scenario:
    """Monthly simulation. Both paths spend the same each month on housing; the cheaper path invests the difference.

    Both start with the same capital: the buyer spends it on the purchase, the renter invests all of it.
    """
    monthly = (1 + etf - i.etf_cost_drag) ** (1 / 12) - 1
    r = i.loan_rate / 12
    balance, buyer, renter = up.loan, 0.0, up.total
    rows: list[YearRow] = []

    def row(year: int, owner_cost: float, rent: float) -> YearRow:
        value = i.property_price * (1 + growth) ** year
        rpgt_rate = rules.rpgt_by_holding_year[year - 1] if 1 <= year <= len(rules.rpgt_by_holding_year) else (rules.rpgt_by_holding_year[0] if year == 0 else 0.0)
        selling = value * i.selling_cost_rate
        gain = value - selling - i.property_price - (up.total - up.down_payment)
        sale = selling + max(gain, 0.0) * rpgt_rate
        equity = value - balance - sale
        buy = equity + buyer
        return YearRow(year=year, property_value=value, loan_balance=balance, sale_costs=sale, home_equity=equity,
                       buyer_portfolio=buyer, buy_net_worth=buy, rent_net_worth=renter, gap=buy - renter,
                       owner_monthly_cost=owner_cost, rent_monthly=rent, deflator=(1 + i.inflation) ** year)

    rows.append(row(0, 0.0, 0.0))
    for year in range(1, i.horizon_years + 1):
        lift, owner_sum = (1 + i.cost_growth) ** (year - 1), 0.0
        rent = i.rent_monthly * (1 + i.rent_growth) ** (year - 1)
        room = i.room_income_monthly * (1 + i.rent_growth) ** (year - 1)
        for m in range(12):
            value = i.property_price * (1 + growth) ** (year - 1 + m / 12)
            instalment = up.monthly_instalment if balance > 0.005 else 0.0
            if instalment:
                interest = balance * r
                balance = max(balance + interest - instalment, 0.0)
            owner = instalment + (i.maintenance_monthly + (i.property_tax_yearly + i.insurance_yearly) / 12) * lift + value * i.repair_rate / 12 - room
            budget = max(owner, rent)
            buyer = buyer * (1 + monthly) + (budget - owner)
            renter = renter * (1 + monthly) + (budget - rent)
            owner_sum += owner
        rows.append(row(year, owner_sum / 12, rent))
    ahead = None
    for row_ in reversed(rows[1:]):
        if row_.gap < 0:
            break
        ahead = row_.year
    return Scenario(property_growth=growth, etf_return=etf, rows=rows, final_gap=rows[-1].gap, first_buy_ahead_year=ahead)


def project(i: RentVsBuyInputs, rules: PurchaseRules) -> RentVsBuyResult:
    up = upfront_costs(i, rules)
    growths = [i.property_growth.low, i.property_growth.base, i.property_growth.high]
    etfs = [i.etf_return.low, i.etf_return.base, i.etf_return.high]
    scenarios = [simulate(i, rules, up, g, e) for g in growths for e in etfs]

    def gap(g: float) -> float:
        return simulate(i, rules, up, g, i.etf_return.base).final_gap

    lo, hi, breakeven = -0.1, 0.2, None
    if gap(lo) < 0 < gap(hi):
        for _ in range(60):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if gap(mid) < 0 else (lo, mid)
        breakeven = round((lo + hi) / 2, 5)
    return RentVsBuyResult(upfront=up, property_growth_levels=growths, etf_return_levels=etfs, scenarios=scenarios,
                           base_index=4, breakeven_property_growth=breakeven, inputs_fingerprint=fingerprint(i))


# ---- Proposals written by the Finance manager ----

class Recommendation(Model):
    headline: Annotated[str, Field(min_length=1, max_length=160)]
    summary: Annotated[str, Field(min_length=1, max_length=1500)]
    conditions_to_flip: list[Text] = Field(min_length=1, max_length=5, description="What would change the answer")
    risks: list[Text] = Field(min_length=1, max_length=5)
    next_steps: list[Text] = Field(min_length=1, max_length=5)
    written_for: Annotated[str, Field(pattern=r"^[0-9a-f]{16}$")] = Field(description="inputs_fingerprint the prose was written against")


class Proposal(Model):
    schema_version: Literal[1]
    id: ID
    kind: Literal["rent_vs_buy"]
    title: Annotated[str, Field(min_length=1, max_length=120)]
    question: Annotated[str, Field(min_length=1, max_length=600)]
    prepared_by: Literal["finance-manager"]
    prepared_on: date
    review_by: date = Field(description="After this date the market inputs need refreshing")
    inputs: RentVsBuyInputs
    input_notes: dict[str, Text] = Field(description="Why each input has its value; keys are input field names")
    recommendation: Recommendation
    post: PostBrief | None = None

    @model_validator(mode="after")
    def notes_name_inputs(self):
        unknown = set(self.input_notes) - set(RentVsBuyInputs.model_fields)
        if unknown:
            raise ValueError(f"input_notes name unknown inputs: {sorted(unknown)}")
        if self.post:
            private, public = self.inputs.model_dump(), self.post.public_inputs.model_dump()
            reused = [k for k in self.post.owner_derived if private[k] == public[k]]
            if reused:
                raise ValueError(f"public post reuses the owner's recorded values: {reused}")
        return self


class PostBrief(Model):
    """Public XHS post handed to Content Lab. Generic market numbers only, never the owner's records."""
    public_inputs: RentVsBuyInputs
    owner_derived: list[str] = Field(description="Inputs taken from the owner's private records; the public scenario must change each one")
    public_notes: dict[str, Text] = Field(description="Public reason for each changed input")
    reader_moment: Annotated[str, Field(min_length=1, max_length=400)]
    hypothesis: Annotated[str, Field(min_length=1, max_length=400)]
    changed_variable: Annotated[str, Field(min_length=1, max_length=200)]
    must_avoid: list[Text] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def public_differs_from_private_records(self):
        fields = set(RentVsBuyInputs.model_fields)
        unknown = (set(self.owner_derived) | set(self.public_notes)) - fields
        if unknown:
            raise ValueError(f"post names unknown inputs: {sorted(unknown)}")
        missing = set(self.owner_derived) - set(self.public_notes)
        if missing:
            raise ValueError(f"owner-derived inputs need a public note: {sorted(missing)}")
        return self


Decision = Literal["accepted", "revise", "declined"]


class Review(Model):
    proposal_id: ID
    decision: Decision
    note: Annotated[str, Field(max_length=1500)] = ""
    written_for: Annotated[str, Field(pattern=r"^[0-9a-f]{16}$")]
    reviewed_at: datetime


class ProposalView(Model):
    proposal: Proposal
    result: RentVsBuyResult
    status: Literal["ready_for_review", "accepted", "revise", "declined"]
    reviews: list[Review]
    stale: bool = Field(description="Past review_by, or the recommendation was written for other inputs")
    post_id: str | None = Field(description="Content Lab post folder already filed from this proposal")


class ResearchSnapshot(Model):
    as_of: date
    source: Literal["private", "demo", "missing"]
    rules_verified_at: date
    rules_stale: bool
    rules_sources: list[Source]
    proposals: list[ProposalView]
    invalid_files: list[str] = Field(description="Proposal files that failed validation; never silently skipped")


def read_reviews(path: Path) -> list[Review]:
    if not path.exists():
        return []
    try:
        return [Review.model_validate_json(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except ValueError as exc:
        raise ResearchError("invalid_review_ledger", 503) from exc


def find_post(proposal_id: str, posts_dir: Path | None) -> str | None:
    """The post folder whose research data came from this proposal, if one was filed."""
    for path in sorted(posts_dir.glob("*/sources/research-data.json")) if posts_dir and posts_dir.is_dir() else []:
        try:
            if json.loads(path.read_text(encoding="utf-8")).get("proposal_id") == proposal_id:
                return path.parent.parent.name
        except (ValueError, OSError):
            continue
    return None


def view(proposal: Proposal, rules: PurchaseRules, reviews: list[Review], today: date, posts_dir: Path | None = None) -> ProposalView:
    result = project(proposal.inputs, rules)
    mine = [r for r in reviews if r.proposal_id == proposal.id and r.written_for == result.inputs_fingerprint]
    stale = today > proposal.review_by or proposal.recommendation.written_for != result.inputs_fingerprint
    return ProposalView(proposal=proposal, result=result, status=mine[-1].decision if mine else "ready_for_review", reviews=mine, stale=stale,
                        post_id=find_post(proposal.id, posts_dir))


def read_snapshot(directory: Path | None, today: date, rules: PurchaseRules, source: Literal["private", "demo", "missing"], posts_dir: Path | None = None) -> ResearchSnapshot:
    proposals, invalid = [], []
    reviews = read_reviews(directory / "reviews.jsonl") if directory else []
    for path in sorted(directory.glob("*.yaml")) if directory and directory.is_dir() else []:
        try:
            proposals.append(view(Proposal.model_validate(yaml.safe_load(path.read_text(encoding="utf-8"))), rules, reviews, today, posts_dir))
        except (ValueError, yaml.YAMLError):
            invalid.append(path.name)
    proposals.sort(key=lambda v: v.proposal.prepared_on, reverse=True)
    return ResearchSnapshot(as_of=today, source=source, rules_verified_at=rules.verified_at,
                            rules_stale=(today - rules.verified_at).days > rules.fresh_days, rules_sources=rules.sources,
                            proposals=proposals, invalid_files=invalid)


def append_review(directory: Path, proposal_id: str, decision: str, note: str, written_for: str, known: list[ProposalView]) -> None:
    target = next((v for v in known if v.proposal.id == proposal_id), None)
    if target is None:
        raise ResearchError("proposal_not_found", 404)
    if target.result.inputs_fingerprint != written_for:
        raise ResearchError("proposal_changed", 409)
    review = Review(proposal_id=proposal_id, decision=decision, note=note, written_for=written_for, reviewed_at=datetime.now(timezone.utc))
    with (directory / "reviews.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(review.model_dump_json() + "\n")


def whatif(proposal: Proposal, changes: dict, rules: PurchaseRules) -> RentVsBuyResult:
    """Recompute with owner-edited inputs; never saved."""
    merged = {**proposal.inputs.model_dump(mode="json"), **changes}
    return project(RentVsBuyInputs.model_validate(merged), rules)
