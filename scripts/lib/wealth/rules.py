"""Validated external regulatory facts used by the wealth report."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, NonNegativeFloat

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PATH = ROOT / "config" / "wealth_rules.yaml"
STRICT = ConfigDict(extra="forbid")


class UsEstateRules(BaseModel):
    model_config = STRICT
    form_706na_filing_threshold_usd: NonNegativeFloat
    verified_at: date
    source: str


class PrsRules(BaseModel):
    model_config = STRICT
    annual_tax_relief_cap_myr: NonNegativeFloat
    verified_at: date
    source: str


class WealthRules(BaseModel):
    model_config = STRICT
    schema_version: int
    us_estate: UsEstateRules
    prs: PrsRules


def load_wealth_rules(path: Path | str | None = None) -> WealthRules:
    rules_path = Path(path) if path else DEFAULT_PATH
    raw = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
    return WealthRules.model_validate(raw)


def stale_rule_facts(
    rules: WealthRules, today: date, max_age_days: int
) -> list[str]:
    facts = {
        "us_estate.form_706na_filing_threshold_usd": rules.us_estate.verified_at,
        "prs.annual_tax_relief_cap_myr": rules.prs.verified_at,
    }
    return sorted(
        name
        for name, verified_at in facts.items()
        if (today - verified_at).days > max_age_days
    )
