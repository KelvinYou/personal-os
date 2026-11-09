"""Exact chart pages for XHS posts, in the account's page template.

Image generation cannot be trusted with numbers or chart geometry, so a data page is
built here as HTML from `sources/research-data.json` and screenshotted at 1080 × 1440 by
scripts/render_html.mjs. Text may only show numbers through {{fact}} placeholders bound to
the data file; [[words]] become the page's single magenta hotspot with the hand-drawn
underline; a line break is "\\n". Each chart places the orange handwritten aside next to
the mark it explains. Visual owner: docs/social-post-visual-guide.md; palette from
data/reference/artifact-style.md and the current post set.
"""
from __future__ import annotations

import glob
import html
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

W, H = 1080, 1440
CW, CH = 920, 580   # chart card; SVG units map 1:1 to page pixels
CARD_X, CARD_Y = 80, 570
INK, ORANGE, MAGENTA, GREEN, MUTED, CREAM = "#181A1B", "#FF642D", "#E2287A", "#35725B", "#9C8C80", "#FBF4EF"
PLACEHOLDER = re.compile(r"\{\{([a-z0-9_]+)\}\}")
DIGIT = re.compile(r"\d")
Line = Annotated[str, Field(max_length=120)]


class PageSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    data: str = Field(description="research-data.json, relative to the spec file")
    chart: Literal["networth", "breakeven", "monthly", "grid"]
    page: int = Field(ge=1, le=9)
    total: int = Field(ge=1, le=9)
    header_left: Line
    header_right: Line
    footer_left: Line
    footer_center: Line
    headline: Annotated[str, Field(min_length=1, max_length=80)]
    subline: Annotated[str, Field(max_length=80)] = ""
    aside: Annotated[str, Field(min_length=1, max_length=40)]
    takeaway: Annotated[str, Field(min_length=1, max_length=60)]
    labels: dict[str, Annotated[str, Field(max_length=24)]] = Field(default_factory=dict)


class SpecError(ValueError):
    pass


def bind(text: str, facts: dict[str, str], field: str) -> str:
    """Fill {{fact}}; any digit typed outside a placeholder is an error, so numbers stay data-bound."""
    unknown = [k for k in PLACEHOLDER.findall(text) if k not in facts]
    if unknown:
        raise SpecError(f"{field}: unknown facts {unknown}; available: {sorted(facts)}")
    if DIGIT.search(PLACEHOLDER.sub("", text)):
        raise SpecError(f"{field}: type numbers only through {{{{fact}}}} placeholders from research-data.json")
    return PLACEHOLDER.sub(lambda m: facts[m.group(1)], text)


def rich(text: str) -> str:
    """Escape, then turn [[words]] into the magenta hotspot with a hand-drawn underline."""
    parts = re.split(r"\[\[(.+?)\]\]", html.escape(text))
    out = "".join(f'<span class="hot">{p}<svg viewBox="0 0 100 12" preserveAspectRatio="none" aria-hidden="true"><path d="M2 8 C 30 3, 60 11, 98 5"/></svg></span>' if i % 2 else p for i, p in enumerate(parts))
    return out.replace("\n", "<br>")


def font_url(name: str) -> str:
    hits = glob.glob(f"/System/Library/AssetsV2/com_apple_MobileAsset_Font*/*/AssetData/{name}")
    return f", url('file://{hits[0]}')" if hits else ""


def wan(v: float) -> str:
    """Same rounding as the data file's facts (one decimal), so labels and headlines agree."""
    return f"{abs(v) / 10000:.1f}万".replace(".0万", "万") if abs(v) >= 10000 else f"{abs(v):,.0f}"


def esc(text: str) -> str:
    return html.escape(text)


@dataclass
class Chart:
    svg: str
    target: tuple[float, float]      # the mark the aside explains, chart coordinates
    aside_at: tuple[float, float]    # left baseline of the aside text, chart coordinates


# ---- charts: plain SVG, exact linear scales, 920 × 580 ----

def chart_networth(d: dict, L: dict) -> Chart:
    rows = d["base"]["rows"]
    left, right, top, bottom = 96, 210, 40, 70
    buy, rent = [r["buy_net_worth"] for r in rows], [r["rent_net_worth"] for r in rows]
    lo, hi = min(0, *buy, *rent), max(*buy, *rent)
    magnitude = 10 ** (len(str(int(hi))) - 1)
    step = magnitude * (2 if hi / magnitude > 5 else 1)
    top_tick = (int(hi // step) + 1) * step
    x = lambda i: left + i * (CW - left - right) / (len(rows) - 1)
    y = lambda v: top + (top_tick - v) * (CH - top - bottom) / (top_tick - lo)
    path = lambda vs: " ".join(f"{'M' if i == 0 else 'L'}{x(i):.1f},{y(v):.1f}" for i, v in enumerate(vs))
    ticks = "".join(f'<line x1="{left}" x2="{x(len(rows) - 1):.1f}" y1="{y(t):.1f}" y2="{y(t):.1f}" class="grid"/><text x="{left - 16}" y="{y(t) + 9:.1f}" class="tick" text-anchor="end">{wan(t) if t else 0}</text>' for t in range(int(lo // step) * step, top_tick + 1, step))
    years = "".join(f'<text x="{x(i):.1f}" y="{CH - 26}" class="tick" text-anchor="middle">{i}</text>' for i in range(0, len(rows), 5))
    end, bx = len(rows) - 1, x(len(rows) - 1)
    yb, yr = y(buy[-1]), y(rent[-1])
    bracket = f'<path d="M{bx - 18:.1f} {yr + 16:.1f} L{bx - 18:.1f} {yb - 16:.1f}" class="bracket"/>'
    labels = (f'<circle cx="{bx:.1f}" cy="{yr:.1f}" r="11" fill="{GREEN}"/><circle cx="{bx:.1f}" cy="{yb:.1f}" r="11" fill="{INK}"/>'
              f'<text x="{bx + 24:.1f}" y="{yr + 4:.1f}" class="end" fill="{GREEN}">{wan(rent[-1])}</text><text x="{bx + 24:.1f}" y="{yr + 40:.1f}" class="endlabel" fill="{GREEN}">{esc(L.get("rent", "租房+ETF"))}</text>'
              f'<text x="{bx + 24:.1f}" y="{yb + 4:.1f}" class="end" fill="{INK}">{wan(buy[-1])}</text><text x="{bx + 24:.1f}" y="{yb + 40:.1f}" class="endlabel" fill="{INK}">{esc(L.get("buy", "买房自住"))}</text>')
    svg = f'{ticks}{years}<text x="{bx + 24:.1f}" y="{CH - 26}" class="tick">{esc(L.get("year", "年"))}</text><path d="{path(buy)}" class="line" stroke="{INK}"/><path d="{path(rent)}" class="line" stroke="{GREEN}"/>{bracket}{labels}'
    return Chart(svg, (bx - 26, (yr + yb) / 2), (left + 40, top + 70))


def chart_breakeven(d: dict, L: dict) -> Chart:
    items = [(L.get("needed", "买房要赢需要"), d["breakeven_property_growth"] or 0, INK),
             (L.get("history_10y", "过去十年 KL 房价"), d["history"]["kl_10y"], MUTED),
             (L.get("history_5y", "过去五年 KL 房价"), d["history"]["kl_5y"], MUTED)]
    left, bar, span = 50, 72, CW - 50 - 240
    top_v = max(v for _, v, _ in items)
    rows = ""
    for i, (label, v, color) in enumerate(items):
        y0 = 60 + i * 150
        length = span * v / top_v
        rows += f'<text x="{left}" y="{y0}" class="barlabel">{esc(label)}</text><rect x="{left}" y="{y0 + 18}" width="{length:.1f}" height="{bar}" rx="18" fill="{color}"/><text x="{left + length + 22:.1f}" y="{y0 + 18 + bar * .68:.1f}" class="end" fill="{color}">{v * 100:.1f}% / 年</text>'
    # Dotted span from the 10-year history to the required growth: the gap the aside explains.
    hist_end, need_end, gy = left + span * items[1][1] / top_v, left + span * items[0][1] / top_v, 60 + 18 + bar + 20
    gap = f'<path d="M{hist_end:.1f} {gy} L{need_end:.1f} {gy}" class="bracket"/><path d="M{hist_end:.1f} {gy - 12} L{hist_end:.1f} {gy + 12} M{need_end:.1f} {gy - 12} L{need_end:.1f} {gy + 12}" class="arrow"/>'
    return Chart(rows + gap, ((hist_end + need_end) / 2, gy + 14), (CW - 360, 500))


def chart_monthly(d: dict, L: dict) -> Chart:
    inputs, row = d["inputs"], d["base"]["rows"][1]
    instalment = d["upfront"]["monthly_instalment"]
    fees = inputs["maintenance_monthly"] + (inputs["property_tax_yearly"] + inputs["insurance_yearly"]) / 12
    repairs = row["owner_monthly_cost"] - instalment - fees + inputs["room_income_monthly"]
    rent, own = row["rent_monthly"], row["owner_monthly_cost"]
    base, col, own_x, rent_x = 500, 210, 110, 600
    scale = (base - 70) / max(own, rent)
    stack, y0 = "", base
    for label, v, color in [(L.get("instalment", "供款"), instalment, INK), (L.get("fees", "管理费+税+保险"), fees, "#5B5552"), (L.get("repairs", "维修预留"), repairs, MUTED)]:
        hgt = v * scale
        y0 -= hgt
        stack += f'<rect x="{own_x}" y="{y0:.1f}" width="{col}" height="{hgt - 4:.1f}" rx="12" fill="{color}"/><text x="{own_x + col + 18}" y="{y0 + hgt / 2 + 10:.1f}" class="seg">{esc(label)} RM{v:,.0f}</text>'
    rent_top = base - rent * scale
    gx = rent_x + col + 44   # the difference, drawn right of the rent bar
    gap = f'<path d="M{gx:.1f} {rent_top:.1f} L{gx:.1f} {y0 + 6:.1f}" class="bracket"/><line x1="{own_x + col:.1f}" x2="{gx + 14:.1f}" y1="{y0:.1f}" y2="{y0:.1f}" class="guide"/><line x1="{rent_x + col:.1f}" x2="{gx + 14:.1f}" y1="{rent_top:.1f}" y2="{rent_top:.1f}" class="guide"/>'
    svg = (f'<line x1="50" x2="{CW - 40}" y1="{base}" y2="{base}" class="axis"/>{stack}'
           f'<text x="{own_x + col / 2}" y="{y0 - 16:.1f}" class="end" text-anchor="middle" fill="{INK}">RM{own:,.0f}</text><text x="{own_x + col / 2}" y="{base + 52}" class="barlabel" text-anchor="middle">{esc(L.get("own", "买房 / 月"))}</text>'
           f'<rect x="{rent_x}" y="{rent_top:.1f}" width="{col}" height="{rent * scale - 4:.1f}" rx="12" fill="{GREEN}"/><text x="{rent_x + col / 2}" y="{rent_top - 16:.1f}" class="end" text-anchor="middle" fill="{GREEN}">RM{rent:,.0f}</text><text x="{rent_x + col / 2}" y="{base + 52}" class="barlabel" text-anchor="middle">{esc(L.get("rent", "租房 / 月"))}</text>{gap}')
    return Chart(svg, (gx - 10, (rent_top + y0) / 2 + 30), (rent_x - 30, (rent_top + y0) / 2 + 10))


def chart_grid(d: dict, L: dict) -> Chart:
    g = d["grid"]
    left, top, cw, ch = 230, 76, 220, 128
    peak = max(map(abs, g["final_gap"])) or 1
    cells = f'<text x="{left - 22}" y="{top - 26}" class="tick" text-anchor="end">{esc(L.get("price", "房价每年"))}</text>'
    cells += "".join(f'<text x="{left + j * cw + cw / 2}" y="{top - 26}" class="tick" text-anchor="middle">ETF {e * 100:.0f}%</text>' for j, e in enumerate(g["etf_return"]))
    for i, p in enumerate(g["property_growth"]):
        cells += f'<text x="{left - 22}" y="{top + i * ch + ch / 2 + 10}" class="tick" text-anchor="end">+{p * 100:.1f}%</text>'
        for j in range(len(g["etf_return"])):
            v = g["final_gap"][i * len(g["etf_return"]) + j]
            color, who = (INK, L.get("buy_short", "买房")) if v >= 0 else (GREEN, L.get("rent_short", "租+ETF"))
            cells += (f'<rect x="{left + j * cw + 6}" y="{top + i * ch + 6}" width="{cw - 12}" height="{ch - 12}" rx="18" fill="{color}" fill-opacity="{.12 + .5 * abs(v) / peak:.2f}"/>'
                      f'<text x="{left + j * cw + cw / 2}" y="{top + i * ch + ch / 2 - 6}" class="cellwho" text-anchor="middle">{esc(who)}</text><text x="{left + j * cw + cw / 2}" y="{top + i * ch + ch / 2 + 32}" class="cellv" text-anchor="middle">+{wan(v)}</text>')
    # The aside explains the scenario that favours buying most: highest price growth, lowest ETF return.
    best = (len(g["property_growth"]) - 1, 0)
    target = (left + best[1] * cw + cw / 2, top + (best[0] + 1) * ch - 4)
    return Chart(cells, target, (left + cw * .9, top + 3 * ch + 64))


CHARTS = {"networth": chart_networth, "breakeven": chart_breakeven, "monthly": chart_monthly, "grid": chart_grid}


ASIDE_PX = 38


def aside_width(text: str) -> float:
    """Rendered width estimate for the handwritten font: CJK full width, Latin about half."""
    return sum(ASIDE_PX * (.55 if ord(c) < 0x2E80 else 1.0) for c in text)


def aside_svg(text: str, chart: Chart) -> str:
    """Handwritten orange aside, slightly rotated, with a short curved arrow to its mark."""
    width = aside_width(text)
    ax, ay = min(chart.aside_at[0], CW - 36 - width), chart.aside_at[1]
    tx, ty = chart.target
    sx, sy = (ax + width / 2, ay - 40) if ty < ay else (ax + width / 2, ay + 14)
    cx, cy = (sx + tx) / 2 + (40 if tx > sx else -40), min(sy, ty) - 20 if ty < ay else max(sy, ty) + 20
    angle = math.atan2(ty - cy, tx - cx)
    head = [(tx - 22 * math.cos(angle + s), ty - 22 * math.sin(angle + s)) for s in (.5, -.5)]
    return (f'<text x="{ax:.1f}" y="{ay:.1f}" class="aside" transform="rotate(-4 {ax:.1f} {ay:.1f})">{esc(text)}</text>'
            f'<path d="M{sx:.1f} {sy:.1f} Q{cx:.1f} {cy:.1f} {tx:.1f} {ty:.1f}" class="arrow"/>'
            f'<path d="M{head[0][0]:.1f} {head[0][1]:.1f} L{tx:.1f} {ty:.1f} L{head[1][0]:.1f} {head[1][1]:.1f}" class="arrow"/>')


def build_page(spec: PageSpec, data: dict) -> str:
    facts = data["facts"]
    text = {k: bind(getattr(spec, k), facts, k) for k in ("headline", "subline", "aside", "takeaway")}
    labels = {k: bind(v, facts, f"labels.{k}") for k, v in spec.labels.items()}
    chart = CHARTS[spec.chart](data, labels)
    hanzi, heavy = font_url("Hanzipen.ttc"), font_url("Lantinghei.ttc")
    return f"""<!doctype html><html lang="zh"><head><meta charset="utf-8"><style>
@font-face {{ font-family: Hand; src: local("HanziPen SC"){hanzi}; }}
@font-face {{ font-family: Heavy; src: local("Lantinghei SC Heavy"){heavy}; font-weight: 800; }}
* {{ margin: 0; box-sizing: border-box; }}
body {{ width: {W}px; height: {H}px; overflow: hidden; background: radial-gradient(120% 90% at 50% 0%, #F8E7E3 0%, #F3DAD6 70%, #F0D3CF 100%); color: {INK};
  font-family: "Avenir Next", "PingFang SC", sans-serif; position: relative; }}
.top, .bottom {{ position: absolute; left: 80px; right: 80px; display: flex; justify-content: space-between; align-items: center; font-weight: 700; font-size: 30px; }}
.top {{ top: 52px; padding-bottom: 22px; border-bottom: 3px solid {ORANGE}; }}
.bottom {{ bottom: 46px; font-size: 28px; }} .bottom .mid {{ font-size: 22px; font-weight: 500; color: #4a4446; }}
h1 {{ position: absolute; left: 80px; right: 80px; top: 170px; font-family: "Avenir Next", Heavy, "PingFang SC", sans-serif; font-weight: 800; font-size: 92px; line-height: 1.16; letter-spacing: -1px; }}
.hot {{ color: {MAGENTA}; position: relative; display: inline-block; }}
.hot svg {{ position: absolute; left: -2%; width: 104%; bottom: -14px; height: 22px; overflow: visible; }}
.hot path {{ fill: none; stroke: {MAGENTA}; stroke-width: 5; stroke-linecap: round; vector-effect: non-scaling-stroke; }}
.sub {{ position: absolute; left: 80px; right: 80px; top: 476px; font-size: 44px; font-weight: 700; }}
.card {{ position: absolute; left: {CARD_X}px; top: {CARD_Y}px; width: {CW}px; height: {CH}px; background: {CREAM}; border-radius: 40px; box-shadow: 0 18px 40px rgba(120, 60, 50, .10), 0 2px 0 rgba(255,255,255,.7) inset; overflow: visible; }}
.card svg {{ width: {CW}px; height: {CH}px; overflow: visible; font-family: "Avenir Next", "PingFang SC", sans-serif; }}
.grid {{ stroke: #E8DBD3; stroke-width: 2; }} .axis {{ stroke: #CDBDB2; stroke-width: 3; }}
.guide {{ stroke: {INK}; stroke-width: 2; stroke-dasharray: 6 8; opacity: .45; }}
.bracket {{ stroke: {ORANGE}; stroke-width: 4; stroke-dasharray: 2 10; stroke-linecap: round; fill: none; }}
.tick {{ font-size: 28px; fill: #6F6461; font-weight: 600; }}
.line {{ fill: none; stroke-width: 8; stroke-linecap: round; stroke-linejoin: round; }}
.end {{ font-size: 40px; font-weight: 800; }} .endlabel {{ font-size: 26px; font-weight: 700; }}
.barlabel {{ font-size: 32px; font-weight: 700; fill: {INK}; }} .seg {{ font-size: 26px; font-weight: 600; fill: #3d3638; }}
.cellwho {{ font-size: 32px; font-weight: 800; fill: {INK}; }} .cellv {{ font-size: 30px; font-weight: 700; fill: {INK}; }}
.aside {{ font-family: Hand, "Kaiti SC", cursive; fill: {ORANGE}; font-size: {ASIDE_PX}px; }}
.arrow {{ fill: none; stroke: {ORANGE}; stroke-width: 4; stroke-linecap: round; stroke-linejoin: round; }}
.take {{ position: absolute; left: 80px; right: 80px; top: 1206px; font-size: 42px; font-weight: 800; }}
</style></head><body>
<div class="top"><span>{esc(spec.header_left)}</span><span>{esc(spec.header_right)}</span></div>
<h1>{rich(text["headline"])}</h1>
{f'<p class="sub">{rich(text["subline"])}</p>' if text["subline"] else ""}
<div class="card"><svg viewBox="0 0 {CW} {CH}" role="img" aria-label="{esc(text["headline"])}">{chart.svg}{aside_svg(text["aside"], chart)}</svg></div>
<p class="take">{esc(text["takeaway"])}</p>
<div class="bottom"><span>{esc(spec.footer_left)}</span><span class="mid">{esc(spec.footer_center)}</span><span>{spec.page:02d} / {spec.total:02d}</span></div>
</body></html>"""


def load(spec_path: Path) -> tuple[PageSpec, dict]:
    spec = PageSpec.model_validate(json.loads(spec_path.read_text(encoding="utf-8")))
    data_path = (spec_path.parent / spec.data).resolve()
    data = json.loads(data_path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or "facts" not in data:
        raise SpecError(f"{data_path} is not a research-data.json (schema_version 1 with facts)")
    return spec, data
