"""Synthetic-only contracts for deterministic travel Markdown rendering."""
from contextlib import redirect_stdout
import io
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from travel_build import build, SKILL
from lib.travel.markdown import SourceError, inline, parse
from lib.travel.render import render
from lib.travel.icons import svg_markers, EMOJI

FIXTURE = ROOT / 'tests/fixtures/travel_render.md'

class TravelRenderTests(unittest.TestCase):
    def setUp(self): self.source = FIXTURE.read_text()

    def test_preserves_content_states_history_and_anchors(self):
        html = render(parse(self.source), SKILL, 'fixture.md', 'hash')
        for text in ['id="day-1"', 'id="day-2"', 'id="stays"', 'status selected',
                     'id="history"', 'id="sources"', '首次编写', 'https://example.com/evidence',
                     '2030-02-01', '重要提醒', '待确认 / 注意', 'href="#day-1"']:
            self.assertIn(text, html)
        self.assertNotIn('同上', html)
        self.assertNotIn('酒店清单.html', html)

    def test_lucide_replaces_visible_emoji_preserves_urls_and_assets(self):
        html = render(parse(self.source), SKILL, 'fixture.md', 'hash')
        self.assertNotRegex(html, EMOJI)
        self.assertIn('class="ui-icon"', html)
        self.assertIn('<svg', html)
        snippet = '<a href="https://example.com/✅">✅ 已核验 ⚠️ 注意 ❓ 待确认 🚨 重要</a><script>const x="✅";</script>'
        result = svg_markers(snippet, SKILL)
        self.assertIn('href="https://example.com/✅"', result)
        self.assertIn('const x="✅";', result)
        self.assertEqual(result.count('<svg'), 4)
        self.assertIn('已核验', result)

    def test_red_eye_departure_row_covers_calendar_without_extra_hotel(self):
        source=self.source.replace('2030-03-02', '2030-03-03')
        source=source.replace('| 2 | 3/2 | 离境 | — | 地铁 |', '| 2 | 3/2 | 离境 | — | 地铁 |\n| — | 3/3 | 凌晨离境 | — | 航班 |')
        plan=parse(source)
        self.assertEqual(len(plan.days), 2)
        self.assertEqual(plan.nights, 1)
        html=render(plan, SKILL, 'fixture.md', 'hash')
        self.assertIn('凌晨离境', html)
        self.assertNotIn('id="day-3"', html)

    def test_supplementary_day_tables_and_subheadings_preserved(self):
        source=self.source.replace('> **定位：轻量散步**', '> **定位：轻量散步。** 附带说明')
        source=source.replace('### Day 2（3/2）', '#### 交通备选\n\n| 方案 | 说明 |\n|---|---|\n| 地铁 | 备选说明<br>保留第二行 |\n\n### Day 2（3/2）')
        html=render(parse(source), SKILL, 'fixture.md', 'hash')
        self.assertIn('轻量散步。 附带说明', html)
        self.assertIn('交通备选', html)
        self.assertIn('备选说明<br>保留第二行', html)
        self.assertEqual(html.count('class="daynum"'), 2)

    def test_empty_timeline_fields_do_not_show_placeholder_badges(self):
        html=render(parse(self.source), SKILL, 'fixture.md', 'hash')
        self.assertNotIn('<span class="tag">—</span>', html)
        self.assertIn('<span class="tag">免费</span>', html)
        self.assertIn('入口待核', html)
        source=self.source.replace('| 10:00–11:00 | 休息 | 同上 | — | 自由休息 |', '| 10:00–11:00 | 休息 | — | 0 | — |')
        html=render(parse(source), SKILL, 'fixture.md', 'hash')
        self.assertIn('<span class="tag">0</span>', html)
        self.assertNotIn('<p class="sub">—</p>', html)
        self.assertNotIn('<span class="meta">—</span>', html)

    def test_pending_status_never_inferred_from_prose(self):
        html = render(parse(self.source.replace('| 已选 |', '| 待确认 |')), SKILL, 'fixture.md', 'hash')
        self.assertIn('status pending', html)
        with self.assertRaisesRegex(SourceError, 'stay 状态'):
            parse(self.source.replace('| 已选 |', '| 已付？ |'))

    def test_build_check_deterministic_and_stale_without_mutation(self):
        with tempfile.TemporaryDirectory() as folder, redirect_stdout(io.StringIO()):
            source = Path(folder)/'fixture.md'; source.write_text(self.source)
            output = Path(folder)/'fixture-itinerary.html'
            self.assertEqual(build(source), 0)
            first = output.read_bytes()
            self.assertEqual(build(source, check=True), 0)
            self.assertEqual(build(source), 0)
            self.assertEqual(output.read_bytes(), first)
            self.assertEqual(source.read_text(), self.source)
            source.write_text(self.source.replace('首次编写', '调整记录'))
            self.assertEqual(build(source, check=True), 1)
            self.assertEqual(output.read_bytes(), first)
            self.assertEqual(list(Path(folder).glob('*html')), [output])

    def test_failure_does_not_replace_page(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder)/'fixture.md'; output=Path(folder)/'fixture-itinerary.html'
            source.write_text(self.source.replace('https://example.com/evidence','javascript:alert(1)'))
            output.write_text('retained page')
            with self.assertRaisesRegex(SourceError, 'L'):
                build(source)
            self.assertEqual(output.read_text(), 'retained page')

    def test_invalid_source_contracts(self):
        mutations = [
            self.source.replace('schema: 1','schema: 2'),
            self.source.replace('schema: 1','schema: 1\n  schema: 1'),
            self.source.replace('2030-03-02','2030-03-03'),
            self.source.replace('language: zh-CN','unknown: true'),
            self.source.replace('### Day 2（3/2）','### Day 3（3/2）'),
            self.source.replace('| 2 | 3/2 |','| 2 | 3/1 |'),
            self.source.replace('住宿 1 晚','住宿 2 晚'),
            self.source.replace('| 09:00–10:00 | 出发 |','| 出发 |'),
            self.source.replace('> **定位：轻量散步**','无定位'),
            self.source.replace('| v1 | 2030-02-01 | 首次编写 |','| v1 | 首次编写 |'),
            '# legacy unnormalized source',
        ]
        for source in mutations:
            with self.subTest(source=source[:50]), self.assertRaises(SourceError): parse(source)

    def test_unbound_map_rejected(self):
        source=self.source.replace('[高德](https://uri.amap.com/search?keyword=测试公园) · [G](https://www.google.com/maps/search/?api=1&query=测试公园)', '同上')
        with self.assertRaisesRegex(SourceError,'no preceding'):
            render(parse(source), SKILL, 'fixture.md', 'hash')

    def test_safe_inline_balanced_urls_and_escaping(self):
        self.assertIn('https://example.com/a(b)', inline('[link](https://example.com/a(b))'))
        self.assertIn('&amp;', inline('A & B'))
        with self.assertRaises(SourceError): inline('<script>alert(1)</script>')
        with self.assertRaises(SourceError): inline('[link](javascript:alert(1))')

    def test_source_cannot_be_output_or_preview(self):
        with self.assertRaises(ValueError): build(FIXTURE, FIXTURE)
        with self.assertRaises(ValueError): build(FIXTURE, nojs_preview=FIXTURE)

if __name__ == '__main__': unittest.main()
