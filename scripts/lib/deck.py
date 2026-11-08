"""Mechanical PPTX checks for docs/presentation-guide.md § Visual acceptance.

Stdlib only (zipfile + ElementTree), so no python-pptx dependency. Three rules:

- DECK-ART: the cover (slide 1) has no artwork picture, or the whole deck has
  none. Catches the 2026-11-06 deck: 12 slides, 0 pictures.
- FOCAL: a content slide has neither a text run >= focal_text_ratio x its body
  size nor a picture/chart covering >= focal_visual_min_area of the slide.
  Catches v4 slides 4 / 11 / 12 (36 pt headline over 22-24 pt body, no visual).
- RHYTHM: one layout repeats on too many consecutive or total content slides.
  The layout is derived from geometry, not self-reported, e.g. `art-C/text-C`.
  Catches v4 (art-C/text-C on 7 of 11, slides 5-8 in a row) and v3
  (art-R/text-L on 6 of 11, the left-text/right-image pattern).

What it cannot judge: whether artwork is 3D, on-topic or well composed.
"""
from __future__ import annotations

import json
import re
import zipfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET

from .schema import PresentationCfg

A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"

# Layout-fingerprint geometry (fractions of slide width/height). These define
# the fingerprint, they are not pass/fail limits — those live in thresholds.
COLUMN_EDGES = (0.4, 0.6)   # x < 0.4 = L, 0.4..0.6 = C, > 0.6 = R
TITLE_BAND = 0.22           # text centred above this is headline/subtitle
FOOTER_BAND = 0.93          # text centred below this is footer/page number


@dataclass
class Visual:
    kind: str     # "art" (picture or group containing one) | "chart" (graphicFrame)
    area: float   # fraction of slide
    cx: float     # centre x, fraction of slide width


@dataclass
class TextBox:
    chars: int
    max_pt: float | None
    cx: float
    cy: float


@dataclass
class SlideStats:
    number: int
    body_pt: float | None = None
    max_pt: float | None = None
    visuals: list[Visual] = field(default_factory=list)
    texts: list[TextBox] = field(default_factory=list)


@dataclass
class Finding:
    rule: str
    slide: int | None
    message: str
    severity: str = "ERROR"

    def format(self) -> str:
        where = f"slide {self.slide}" if self.slide else "deck"
        return f"{self.severity} [{self.rule}] {where}: {self.message}"


def _column(x: float) -> str:
    return "L" if x < COLUMN_EDGES[0] else "R" if x > COLUMN_EDGES[1] else "C"


def _box(el: ET.Element, w: int, h: int) -> tuple[float, float, float, float] | None:
    """First xfrm under el as (centre x, centre y, area) fractions; None if absent."""
    for x in el.iter():
        if x.tag in (A + "xfrm", P + "xfrm"):
            off, ext = x.find(A + "off"), x.find(A + "ext")
            if off is not None and ext is not None and ext.get("cx"):
                ox, oy = int(off.get("x")) / w, int(off.get("y")) / h
                ex, ey = int(ext.get("cx")) / w, int(ext.get("cy")) / h
                return ox + ex / 2, oy + ey / 2, ex * ey
    return None


def _runs(el: ET.Element) -> list[tuple[float, int]]:
    out = []
    for run in el.iter(A + "r"):
        rpr, t = run.find(A + "rPr"), run.find(A + "t")
        text = re.sub(r"\s", "", (t.text or "") if t is not None else "")
        if rpr is not None and rpr.get("sz") and text:
            out.append((int(rpr.get("sz")) / 100, len(text)))
    return out


def _slide_paths(z: zipfile.ZipFile) -> list[str]:
    """Slide part names in presentation order (not zip order)."""
    pres = ET.fromstring(z.read("ppt/presentation.xml"))
    rels = ET.fromstring(z.read("ppt/_rels/presentation.xml.rels"))
    target = {r.get("Id"): r.get("Target") for r in rels.iter(REL + "Relationship")}
    return ["ppt/" + target[s.get(R + "id")].lstrip("/").removeprefix("ppt/")
            for s in pres.iter(P + "sldId")]


def read_deck(path: Path) -> list[SlideStats]:
    with zipfile.ZipFile(path) as z:
        size = ET.fromstring(z.read("ppt/presentation.xml")).find(P + "sldSz")
        w, h = int(size.get("cx")), int(size.get("cy"))
        stats = []
        for n, part in enumerate(_slide_paths(z), 1):
            tree = ET.fromstring(z.read(part)).find(f"{P}cSld/{P}spTree")
            s = SlideStats(n)
            chars: Counter[float] = Counter()
            for el in tree:
                tag = el.tag.removeprefix(P)
                box = _box(el, w, h)
                if tag == "pic" or (tag == "grpSp" and el.find(f".//{P}pic") is not None):
                    if box:
                        s.visuals.append(Visual("art", box[2], box[0]))
                    continue
                if tag == "graphicFrame":
                    if box:
                        s.visuals.append(Visual("chart", box[2], box[0]))
                    continue
                runs = _runs(el)
                for pt, c in runs:
                    chars[pt] += c
                if runs and box:
                    s.texts.append(TextBox(sum(c for _, c in runs), max(pt for pt, _ in runs),
                                           box[0], box[1]))
            if chars:
                s.body_pt = chars.most_common(1)[0][0]
                s.max_pt = max(chars)
            stats.append(s)
    return stats


def _artwork(s: SlideStats, cfg: PresentationCfg) -> list[Visual]:
    return [v for v in s.visuals if v.kind == "art" and v.area < cfg.background_min_area]


def _candidates(s: SlideStats, cfg: PresentationCfg) -> list[Visual]:
    return _artwork(s, cfg) + [v for v in s.visuals if v.kind == "chart"]


def _focal(s: SlideStats, cfg: PresentationCfg) -> tuple[str, float] | None:
    """(kind, centre x) of the dominant element, or None when the slide has none."""
    big = max(_candidates(s, cfg), key=lambda v: v.area, default=None)
    if big and big.area >= cfg.focal_visual_min_area:
        return big.kind, big.cx
    if s.body_pt and s.max_pt and s.max_pt >= cfg.focal_text_ratio * s.body_pt:
        # Placeholder text may inherit its position from the layout (no xfrm); treat as centred.
        box = next((t for t in s.texts if t.max_pt == s.max_pt), None)
        return "type", box.cx if box else 0.5
    return None


def layout_of(s: SlideStats, cfg: PresentationCfg) -> str:
    """Derived layout fingerprint: focal kind + column, body-text column."""
    focal = _focal(s, cfg)
    head = f"{focal[0]}-{_column(focal[1])}" if focal else "text"
    body = [t for t in s.texts if TITLE_BAND <= t.cy <= FOOTER_BAND and t.max_pt != s.max_pt]
    total = sum(t.chars for t in body)
    if not total:
        return f"{head}/none"
    return f"{head}/text-{_column(sum(t.cx * t.chars for t in body) / total)}"


def lint_slides(slides: list[SlideStats], cfg: PresentationCfg,
                exempt: set[int] = frozenset()) -> list[Finding]:
    findings: list[Finding] = []

    if not any(_artwork(s, cfg) for s in slides):
        findings.append(Finding("DECK-ART", None,
                                "no artwork pictures in the deck; the shared style requires 3D artwork"))
    elif slides and not _artwork(slides[0], cfg) and 1 not in exempt:
        findings.append(Finding("DECK-ART", 1, "cover has no artwork picture"))

    for s in slides:
        if s.number in exempt or _focal(s, cfg):
            continue
        visual = max((v.area for v in _candidates(s, cfg)), default=0.0)
        text = (f"largest text {s.max_pt:g} pt = {s.max_pt / s.body_pt:.1f}x body {s.body_pt:g} pt"
                if s.body_pt else "no sized text")
        findings.append(Finding(
            "FOCAL", s.number,
            f"no dominant element: {text} (need {cfg.focal_text_ratio:g}x), "
            f"largest visual {visual:.0%} of slide (need {cfg.focal_visual_min_area:.0%})"))

    findings += _rhythm(slides, cfg, exempt)
    return findings


def _rhythm(slides: list[SlideStats], cfg: PresentationCfg, exempt: set[int]) -> list[Finding]:
    findings: list[Finding] = []
    content = [(s.number, layout_of(s, cfg)) for s in slides[1:] if s.number not in exempt]

    run: list[int] = []
    prev = None
    for number, layout in content + [(None, None)]:
        if layout == prev and run and number == run[-1] + 1:
            run.append(number)
            continue
        if len(run) > cfg.rhythm_max_run:
            findings.append(Finding("RHYTHM", run[0],
                                    f"slides {run[0]}-{run[-1]} repeat layout `{prev}` "
                                    f"{len(run)} times in a row (max {cfg.rhythm_max_run})"))
        run, prev = ([number], layout) if number else ([], None)

    if len(content) >= cfg.rhythm_min_content_slides:
        counts = Counter(layout for _, layout in content)
        for layout, k in counts.most_common():
            if k / len(content) > cfg.rhythm_max_share:
                where = ", ".join(str(n) for n, l in content if l == layout)
                findings.append(Finding("RHYTHM", None,
                                        f"layout `{layout}` on {k} of {len(content)} content slides "
                                        f"({where}); max {cfg.rhythm_max_share:.0%}"))
    return findings


def lint_deck(path: Path, cfg: PresentationCfg, exempt: set[int] = frozenset()) -> list[Finding]:
    return lint_slides(read_deck(path), cfg, exempt)


def sidecar_exempt(deck: Path) -> set[int]:
    """Slides exempted in the deck's production notes.

    Looks for production.json beside the deck, then one level up (decks usually
    live in <task>/output/). Shape: {"deck_lint": {"exempt": [12], "reason": "..."}}.
    An exemption without a non-empty reason is ignored, so it stays reviewable.
    """
    for candidate in (deck.parent / "production.json", deck.parent.parent / "production.json"):
        if not candidate.is_file():
            continue
        try:
            entry = json.loads(candidate.read_text(encoding="utf-8")).get("deck_lint") or {}
        except (json.JSONDecodeError, AttributeError):
            return set()
        if str(entry.get("reason", "")).strip():
            return {int(n) for n in entry.get("exempt", [])}
        return set()
    return set()
