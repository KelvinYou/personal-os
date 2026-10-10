"""Regression checks for HTML finalization; fixtures contain no private trip data."""
import contextlib
import io
from pathlib import Path
import re
import tempfile
import unittest

from build_share import SKILL, build, finalize
from validate_share import validate


def fixture():
    card = '<div class="grid"><article class="practical-card"><p class="eyebrow">Fixture city</p><h3>Fixture item</h3><a href="#day-1">Day 1</a></article></div>'
    values = {
        'PAGE_TITLE': 'Fixture', 'SHARE_CSS': '/* old stylesheet */',
        'SHARE_JS': '/* old script */', 'TRIP_NAME': 'Fixture trip',
        'DATE_RANGE': 'Fixture dates', 'TRIP_LEDE': 'Fixture only',
        'DAYS': '1', 'NIGHTS': '0', 'ROUTE_SUMMARIES': '',
        'PRIORITY_ACTIONS': '', 'OVERVIEW': '<a href="#day-1">Day 1</a>',
        'STAYS': '', 'DAYS_CONTENT': '<article class="day" id="day-1"><span class="daynum">Day 1</span><a href="https://example.com/map">Fixture map</a></article>',
        'PLACES_CONTENT': card, 'FOOD_CONTENT': card,
        'PRACTICAL_SECTIONS': '', 'FRESHNESS_NOTE': 'Fixture only',
    }
    text = (SKILL / 'templates/share.html').read_text()
    return re.sub(r'\{\{([A-Z_]+)\}\}', lambda m: values[m[1]], text)


def main_content(text):
    return text[text.index('<main'):text.index('</main>') + 7]


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / 'source.html'
        self.output = Path(self.temp.name) / 'output.html'
        self.preview = Path(self.temp.name) / 'preview.html'

    def test_preserves_content_and_rebuilds_old_menu(self):
        source = fixture().replace('lang="en"', 'lang="zh-CN"')
        source = re.sub(r'<details\b[^>]*class="appearance"[^>]*>.*?</details>', '<details class="appearance" open><summary>Old menu</summary><button id="theme" class="js-only">Old theme</button></details>', source, flags=re.S)
        self.source.write_text(source)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(build(self.source, self.output, 1, True, self.preview), 0)
        output = self.output.read_text()
        self.assertEqual(main_content(source), main_content(output))
        self.assertEqual(main_content(output), main_content(self.preview.read_text()))
        self.assertIn('深色外观', output)
        self.assertNotIn('<script>', self.preview.read_text())
        self.assertEqual(finalize(output), output, 'Repeated finalization must not drift')

    def test_failed_validation_does_not_overwrite_outputs(self):
        source = fixture().replace('id="food"', 'id="missing-food"')
        self.source.write_text(source)
        self.output.write_text('Keep existing deliverable')
        self.preview.write_text('Keep existing preview')
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(build(self.source, self.output, 1, True, self.preview), 1)
        self.assertEqual(self.output.read_text(), 'Keep existing deliverable')
        self.assertEqual(self.preview.read_text(), 'Keep existing preview')

    def test_preview_cannot_replace_source_or_deliverable(self):
        self.source.write_text(fixture())
        for preview in (self.source, self.output):
            with self.assertRaises(ValueError):
                build(self.source, self.output, 1, True, preview)
        self.assertEqual(self.source.read_text(), fixture())

    def test_ambiguous_script_blocks_are_rejected(self):
        with self.assertRaises(ValueError):
            finalize(fixture().replace('</body>', '<script>extra()</script></body>'))

    def test_ui_validator_rejects_legacy_controls_and_wrong_defaults(self):
        good = finalize(fixture())
        variants = [
            good.replace('data-theme="light"', 'data-theme="dark"'),
            good.replace('data-material="glass"', 'data-material="solid"'),
            good.replace('<input id="theme" type="checkbox">', '<button id="theme" class="js-only">Theme</button>'),
            good.replace('<input id="clarity" type="checkbox">', '<input id="clarity" type="checkbox" checked>'),
            good.replace('class="appearance-help"', 'class="sub"'),
        ]
        for text in variants:
            self.output.write_text(text)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(validate(self.output, 1, True, ui=True), 1)

    def test_hotel_mode_omits_sightseeing_and_food(self):
        source = fixture()
        for section in ('days', 'places', 'food'):
            source = re.sub(rf'<section id="{section}">.*?</section>', '', source, flags=re.S)
            source = re.sub(rf'<a href="#{section}">.*?</a>', '', source, flags=re.S)
        source = source.replace('<a href="#day-1">Day 1</a>', '')
        self.source.write_text(source)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(build(self.source, self.output, 0), 0)


if __name__ == '__main__':
    unittest.main()
