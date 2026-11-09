"""Tests for scripts/lib/deck.py.

Fixtures are synthetic minimal PPTX files reproducing the *shape* of two real
defects (tests never read data/artifacts/, which is private):
- 2026-11-06 deck: 12 text-and-shape slides, zero pictures  -> DECK-ART
- 2026-11-06 v4 deck slide 4: 36 pt headline over 22 pt body, no visual -> FOCAL
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import deck_hook  # noqa: E402
from lib.deck import layout_of, lint_deck, read_deck, sidecar_exempt  # noqa: E402
from lib.schema import PresentationCfg  # noqa: E402

CFG = PresentationCfg(focal_text_ratio=3.0, focal_visual_min_area=0.25, background_min_area=0.95,
                      body_min_pt=18,
                      rhythm_max_run=2, rhythm_max_share=0.34, rhythm_min_content_slides=6)
W, H = 12192000, 6858000
NS = ('xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
      'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"')


def _xfrm(cx: float, cy: float, w: float, h: float) -> str:
    """xfrm from centre and size, all as slide fractions."""
    return (f'<a:xfrm><a:off x="{int(W * (cx - w / 2))}" y="{int(H * (cy - h / 2))}"/>'
            f'<a:ext cx="{int(W * w)}" cy="{int(H * h)}"/></a:xfrm>')


def text(pt: float, s: str, at: tuple[float, float] | None = None) -> str:
    sppr = f"<p:spPr>{_xfrm(*at, 0.2, 0.1)}</p:spPr>" if at else ""
    return (f'<p:sp>{sppr}<p:txBody><a:p><a:r><a:rPr sz="{int(pt * 100)}"/>'
            f'<a:t>{s}</a:t></a:r></a:p></p:txBody></p:sp>')


def pic(frac: float, cx: float | None = None) -> str:
    if cx is None:
        return (f'<p:pic><p:spPr><a:xfrm><a:off x="0" y="0"/>'
                f'<a:ext cx="{int(W * frac)}" cy="{H}"/></a:xfrm></p:spPr></p:pic>')
    return f'<p:pic><p:spPr>{_xfrm(cx, 0.5, frac / 0.6, 0.6)}</p:spPr></p:pic>'


TITLE = (0.5, 0.14)


def art_slide(art_x: float, text_x: float) -> str:
    """Headline on top, 30% artwork at art_x, body text centred at text_x."""
    return text(36, "标题", TITLE) + pic(0.3, art_x) + text(22, "说明文字" * 5, (text_x, 0.8))


def chart(frac: float) -> str:
    return (f'<p:graphicFrame><p:xfrm><a:off x="0" y="0"/>'
            f'<a:ext cx="{int(W * frac)}" cy="{H}"/></p:xfrm></p:graphicFrame>')


def build(path: Path, slides: list[str]) -> Path:
    # Store slides out of zip order vs presentation order to prove ordering follows sldIdLst.
    ids = "".join(f'<p:sldId id="{256 + i}" r:id="rId{i + 1}"/>' for i in range(len(slides)))
    rels = "".join(
        f'<Relationship Id="rId{i + 1}" Target="slides/slide{i + 1}.xml" '
        f'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide"/>'
        for i in range(len(slides)))
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("ppt/presentation.xml",
                   f'<p:presentation {NS}><p:sldIdLst>{ids}</p:sldIdLst>'
                   f'<p:sldSz cx="{W}" cy="{H}"/></p:presentation>')
        z.writestr("ppt/_rels/presentation.xml.rels",
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   f'{rels}</Relationships>')
        for i in reversed(range(len(slides))):
            z.writestr(f"ppt/slides/slide{i + 1}.xml",
                       f'<p:sld {NS}><p:cSld><p:spTree>{slides[i]}</p:spTree></p:cSld></p:sld>')
    return path


def build_template(path: Path) -> Path:
    """One slide whose title/body placeholders carry neither position nor size:
    position comes from the layout, size from the master's txStyles (template decks)."""
    rel_ns = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

    def ph(kind: str | None, idx: str | None, inner: str = "", sppr: str = "") -> str:
        attrs = (f' type="{kind}"' if kind else "") + (f' idx="{idx}"' if idx else "")
        return (f'<p:sp><p:nvSpPr><p:cNvPr id="2" name="ph"/><p:cNvSpPr/><p:nvPr><p:ph{attrs}/></p:nvPr></p:nvSpPr>'
                f'<p:spPr>{sppr}</p:spPr>{inner}</p:sp>')

    def body(s: str) -> str:
        return f'<p:txBody><a:bodyPr/><a:p><a:r><a:rPr/><a:t>{s}</a:t></a:r></a:p></p:txBody>'

    def rels(target: str, kind: str) -> str:
        return ('<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                f'<Relationship Id="rId1" Target="{target}" Type="{rel_ns}/{kind}"/></Relationships>')

    slide = (ph("title", None, body("模板标题")) + ph(None, "1", body("模板正文" * 10)) + pic(0.3, 0.75))
    layout = (ph("title", None, sppr=_xfrm(0.5, 0.12, 0.8, 0.1))
              + ph(None, "1", sppr=_xfrm(0.25, 0.6, 0.4, 0.5)))
    master = (f'<p:sldMaster {NS}><p:cSld><p:spTree/></p:cSld><p:txStyles>'
              '<p:titleStyle><a:lvl1pPr><a:defRPr sz="4400"/></a:lvl1pPr></p:titleStyle>'
              '<p:bodyStyle><a:lvl1pPr><a:defRPr sz="2000"/></a:lvl1pPr></p:bodyStyle>'
              '</p:txStyles></p:sldMaster>')
    build(path, [slide])
    with zipfile.ZipFile(path, "a") as z:
        z.writestr("ppt/slides/_rels/slide1.xml.rels", rels("../slideLayouts/slideLayout1.xml", "slideLayout"))
        z.writestr("ppt/slideLayouts/slideLayout1.xml",
                   f'<p:sldLayout {NS}><p:cSld><p:spTree>{layout}</p:spTree></p:cSld></p:sldLayout>')
        z.writestr("ppt/slideLayouts/_rels/slideLayout1.xml.rels",
                   rels("../slideMasters/slideMaster1.xml", "slideMaster"))
        z.writestr("ppt/slideMasters/slideMaster1.xml", master)
    return path


class DeckLintTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def lint(self, slides, exempt=frozenset()):
        return [(f.rule, f.slide) for f in lint_deck(build(self.tmp / "d.pptx", slides), CFG, exempt)]

    def test_zero_picture_deck_fails_deck_art(self):
        # Shape of the 2026-11-06 first deck.
        slides = [text(56, "封面") + text(22, "副标题")] + [text(36, "标题") + text(18, "正文内容" * 5)] * 11
        self.assertIn(("DECK-ART", None), self.lint(slides))

    def test_cover_without_artwork_fails(self):
        self.assertIn(("DECK-ART", 1), self.lint([text(56, "封面"), pic(0.4) + text(36, "标题")]))

    def test_v4_text_inventory_slide_fails_focal(self):
        # Shape of v4 slide 4: 36 pt headline, 22 pt two-column inventory, no visual.
        inventory = text(36, "8 个 Suite 均为部分覆盖") + text(22, "fee-schedule 只读检查" * 8)
        found = self.lint([pic(0.33) + text(56, "封面"), inventory])
        self.assertEqual(found, [("FOCAL", 2)])

    def test_big_number_passes(self):
        # v4 slide 9: 78 pt "9" over 22 pt body.
        self.assertEqual(self.lint([pic(0.33), text(36, "标题") + text(78, "9") + text(22, "说明" * 10)]), [])

    def test_artwork_or_chart_passes(self):
        self.assertEqual(self.lint([pic(0.33), text(36, "标题") + chart(0.32)]), [])

    def test_background_picture_is_not_artwork(self):
        found = self.lint([pic(1.0) + text(56, "封面")])
        self.assertIn(("DECK-ART", None), found)

    def test_exempt_slide_skips_focal(self):
        inventory = text(36, "附录") + text(22, "清单" * 20)
        self.assertEqual(self.lint([pic(0.33), inventory], exempt={2}), [])

    def test_layout_fingerprint_is_derived_from_geometry(self):
        s = read_deck(build(self.tmp / "d.pptx", [art_slide(0.75, 0.25)]))[0]
        self.assertEqual(layout_of(s, CFG), "art-R/text-L")
        s = read_deck(build(self.tmp / "d.pptx", [text(36, "标题", TITLE) + text(22, "清单" * 20, (0.5, 0.5))]))[0]
        self.assertEqual(layout_of(s, CFG), "text/text-C")

    def test_v4_centered_cluster_repetition_fails_rhythm(self):
        # Shape of v4: centred artwork + centred captions on most content slides.
        cover = art_slide(0.75, 0.25)
        found = self.lint([cover] + [art_slide(0.5, 0.5)] * 4 + [art_slide(0.25, 0.75), art_slide(0.75, 0.25)])
        self.assertIn(("RHYTHM", 2), found)      # slides 2-5 in a row
        self.assertIn(("RHYTHM", None), found)   # 4 of 6 content slides > 34%

    def test_v3_left_text_right_image_dominance_fails_share(self):
        # Shape of v3: text-left / art-right on half the deck, never 3 in a row.
        a, b, c = art_slide(0.75, 0.25), art_slide(0.25, 0.75), art_slide(0.5, 0.5)
        found = self.lint([a, a, b, a, c, a, b])
        self.assertEqual(found, [("RHYTHM", None)])

    def test_varied_layouts_pass_rhythm(self):
        a, b, c = art_slide(0.75, 0.25), art_slide(0.25, 0.75), art_slide(0.5, 0.5)
        self.assertEqual(self.lint([a, b, c, a, b, c, a]), [])

    def test_exempt_slide_breaks_a_run(self):
        a, b, c = art_slide(0.75, 0.25), art_slide(0.25, 0.75), art_slide(0.5, 0.5)
        self.assertNotIn(("RHYTHM", 2), self.lint([a, c, c, b, c], exempt={4}))
        self.assertIn(("RHYTHM", 2), self.lint([a, c, c, c]))

    def test_sidecar_exempt_requires_reason(self):
        out = self.tmp / "task" / "output"
        out.mkdir(parents=True)
        deck = build(out / "d.pptx", [art_slide(0.75, 0.25)])
        side = self.tmp / "task" / "production.json"
        side.write_text(json.dumps({"deck_lint": {"exempt": [12]}}))
        self.assertEqual(sidecar_exempt(deck), set())
        side.write_text(json.dumps({"deck_lint": {"exempt": [12], "reason": "closing actions"}}))
        self.assertEqual(sidecar_exempt(deck), {12})

    def test_hook_finds_only_decks_changed_since_session_start(self):
        old = build(self.tmp / "old.pptx", [art_slide(0.75, 0.25)])
        os.utime(old, (1000, 1000))
        (self.tmp / "node_modules").mkdir()
        build(self.tmp / "node_modules" / "skip.pptx", [art_slide(0.75, 0.25)])
        new = build(self.tmp / "new.pptx", [art_slide(0.75, 0.25)])
        self.assertEqual(deck_hook.changed_decks(self.tmp, 2000), [new])

    def test_global_mode_scans_session_project_but_skips_personal_os(self):
        env = os.environ.pop("CLAUDE_PROJECT_DIR", None)
        try:
            self.assertEqual(deck_hook.scan_root({"cwd": str(self.tmp)}, True), self.tmp.resolve())
            self.assertIsNone(deck_hook.scan_root({"cwd": str(ROOT)}, True))
            self.assertEqual(deck_hook.scan_root({"cwd": str(self.tmp)}, False), deck_hook.ROOT)
        finally:
            if env is not None:
                os.environ["CLAUDE_PROJECT_DIR"] = env

    def test_template_placeholders_inherit_position_and_size(self):
        s = read_deck(build_template(self.tmp / "t.pptx"))[0]
        self.assertEqual((s.body_pt, s.max_pt), (20, 44))          # from master txStyles
        self.assertEqual(layout_of(s, CFG), "art-R/text-L")         # body position from layout

    def test_small_body_text_fails_body_floor(self):
        # Shape of the 2026-11 nutrition handbook: 32 pt headline over 12.5 pt body.
        small = pic(0.33) + text(32, "标题") + text(12.5, "营养说明" * 20)
        self.assertIn(("BODY", 1), self.lint([small]))
        self.assertNotIn(("BODY", 1), self.lint([small], exempt={1}))
        ok = pic(0.33) + text(36, "标题") + text(22, "说明" * 20)
        self.assertEqual(self.lint([ok]), [])

    def test_footer_does_not_count_as_body(self):
        # v3 cover: a long 10.5 pt footer must not become the "body" size.
        cover = (pic(0.33) + text(40, "封面", (0.3, 0.4)) + text(20, "副标题文字" * 3, (0.3, 0.6))
                 + text(10.5, "dtc-e2e-tests source footer" * 2, (0.4, 0.96)))
        self.assertEqual(read_deck(build(self.tmp / "d.pptx", [cover]))[0].body_pt, 20)

    def test_body_is_size_with_most_characters(self):
        s = read_deck(build(self.tmp / "d.pptx", [text(36, "短标题") + text(18, "页码") + text(22, "正文" * 30)]))[0]
        self.assertEqual((s.body_pt, s.max_pt), (22, 36))


if __name__ == "__main__":
    unittest.main()
