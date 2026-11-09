"""Hand an accepted research proposal to Content Lab as a public XHS post idea.

The post uses the proposal's public scenario only (PostBrief.public_inputs), never the
owner's recorded figures. Exact numbers travel as data (sources/research-data.json);
chart pages are rendered from it by scripts/post_chart.py, never by image generation.
See docs/design/finance-research.md §6.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import yaml

from .research import POSTS_DIR, Proposal, ProposalView, PurchaseRules, ResearchError, find_post, project
from .files import ROOT

REFERENCE_PATH = ROOT / "config" / "research" / "kl_rent_vs_buy.yaml"


def wan(value: float) -> str:
    """Chinese ten-thousands, as the account writes money: 49.8万."""
    return f"{abs(value) / 10000:.1f}万".replace(".0万", "万")


def rm(value: float) -> str:
    return f"RM{abs(round(value)):,}"


def public_data(proposal: Proposal, rules: PurchaseRules, today: date) -> dict:
    if not proposal.post:
        raise ResearchError("post_brief_missing", 409)
    inputs = proposal.post.public_inputs
    result = project(inputs, rules)
    base = result.scenarios[result.base_index]
    final, first = base.rows[-1], base.rows[1]
    reference = yaml.safe_load(REFERENCE_PATH.read_text(encoding="utf-8"))["reference"]
    history = reference["kl_price_growth"]
    facts = {
        "horizon": str(inputs.horizon_years),
        "price": rm(inputs.property_price), "price_wan": wan(inputs.property_price),
        "rent": rm(inputs.rent_monthly),
        "loan_rate": f"{inputs.loan_rate * 100:.1f}%",
        "etf_return": f"{inputs.etf_return.base * 100:.0f}%",
        "upfront": rm(result.upfront.total), "upfront_wan": wan(result.upfront.total),
        "instalment": rm(result.upfront.monthly_instalment),
        "owner_cost_y1": rm(first.owner_monthly_cost), "rent_y1": rm(first.rent_monthly),
        "owner_rent_ratio": f"{first.owner_monthly_cost / first.rent_monthly:.1f}",
        "buy_final": rm(final.buy_net_worth), "buy_final_wan": wan(final.buy_net_worth),
        "rent_final": rm(final.rent_net_worth), "rent_final_wan": wan(final.rent_net_worth),
        "gap_final": rm(final.gap), "gap_final_wan": wan(final.gap),
        "leader": "买房" if final.gap >= 0 else "租房+ETF",
        "breakeven": "—" if result.breakeven_property_growth is None else f"{result.breakeven_property_growth * 100:.1f}%",
        "history_10y": f"{history['annualized_10y'] * 100:.1f}%", "history_5y": f"{history['annualized_5y'] * 100:.1f}%",
        "rent_wins": str(sum(s.final_gap < 0 for s in result.scenarios)),
    }
    return {
        "schema_version": 1, "kind": proposal.kind, "proposal_id": proposal.id, "as_of": today.isoformat(),
        "inputs": inputs.model_dump(mode="json"), "public_notes": proposal.post.public_notes,
        "upfront": result.upfront.model_dump(mode="json"),
        "base": base.model_dump(mode="json"),
        "grid": {"property_growth": result.property_growth_levels, "etf_return": result.etf_return_levels,
                 "final_gap": [s.final_gap for s in result.scenarios]},
        "breakeven_property_growth": result.breakeven_property_growth,
        "history": {"kl_10y": history["annualized_10y"], "kl_5y": history["annualized_5y"], "note": history["note"]},
        "facts": facts,
        "sources": [s.model_dump(mode="json") for s in rules.sources],
    }


def brief_markdown(proposal: Proposal, data: dict) -> str:
    post, f = proposal.post, data["facts"]
    avoid = "\n".join(f"- {item}" for item in post.must_avoid)
    sources = "\n".join(f"- [{s['label']}]({s['url']}) — verified {s['verified_at']}" for s in data["sources"])
    return f"""# 在 KL 买房 vs 租房 + 投 ETF：{f['horizon']} 年后谁比较多？

Filed by the Finance manager from research proposal `{proposal.id}` (accepted on the Research desk).

## Reader moment

{post.reader_moment}

## Why now

None beyond the evergreen question; KL high-rise prices and the 2.75% OPR are current as of {data['as_of']}.

## Hypothesis

{post.hypothesis}

## Changed variable

{post.changed_variable}

## Evidence so far

Public scenario (generic market numbers, not the owner's): {f['price']} condo, 90% loan at {f['loan_rate']},
room rent {f['rent']} a month, ETF {f['etf_return']} a year before costs, KL prices +{data['inputs']['property_growth']['base'] * 100:.1f}% a year.
Both paths spend the same on housing each month; the cheaper one invests the difference.

- Year {f['horizon']}: buy {f['buy_final']} vs rent + ETF {f['rent_final']} → {f['leader']} ahead by {f['gap_final']}.
- Owning costs {f['owner_rent_ratio']}× the rent in year 1 ({f['owner_cost_y1']} vs {f['rent_y1']} a month).
- Day-one cash for buying: {f['upfront']}.
- Buying only wins at year {f['horizon']} if KL prices grow faster than {f['breakeven']} a year (NAPIC KL history: {f['history_10y']} a year over 10 years, {f['history_5y']} over 5).
- Rent + ETF leads in {f['rent_wins']} of 9 scenarios.

Exact numbers: `sources/research-data.json`. Chart pages must be rendered from it with
`make post-chart SPEC=… OUT=…` (charts and every number on them stay exact); see the social-post skill.

Sources:
{sources}

## Must avoid

{avoid}
- Investment advice wording ("你应该买/不要买"); this is a worked example with stated assumptions.
- Any number on an image that is not in `sources/research-data.json`.
"""


def file_post_idea(view: ProposalView, rules: PurchaseRules, today: date, posts_dir: Path = POSTS_DIR) -> str:
    """Create data/posts/<slug>-<date>/ as a Content Lab idea. Never overwrites."""
    if view.status != "accepted":
        raise ResearchError("proposal_not_accepted", 409)
    proposal = view.proposal
    if not proposal.post:
        raise ResearchError("post_brief_missing", 409)
    if not posts_dir.is_dir():
        raise ResearchError("posts_unavailable", 503)
    if find_post(proposal.id, posts_dir):
        raise ResearchError("post_exists", 409)
    post_id = f"{proposal.id.removesuffix('-' + proposal.prepared_on.strftime('%Y-%m'))}-{today.isoformat()}"
    folder = posts_dir / post_id
    if folder.exists():
        raise ResearchError("post_exists", 409)
    data = public_data(proposal, rules, today)
    (folder / "sources").mkdir(parents=True)
    (folder / "sources" / "research-data.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (folder / "post.md").write_text(brief_markdown(proposal, data), encoding="utf-8")
    lab = {"schema_version": 1, "stage": "idea",
           "experiment": {"hypothesis": proposal.post.hypothesis, "changed_variable": proposal.post.changed_variable}}
    (folder / "lab.yaml").write_text(yaml.safe_dump(lab, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return post_id
