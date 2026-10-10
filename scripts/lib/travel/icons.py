"""Replace visible emoji markers with bundled Lucide SVG, preserving URLs/assets."""
from html.parser import HTMLParser
from pathlib import Path
import re

# Common emoji ranges, variation selectors, joined sequences and keycap markers.
EMOJI = re.compile(r'(?:[0-9#*]\ufe0f?\u20e3|[\U0001f000-\U0001faff\u2300-\u23ff\u2600-\u27bf\u2b50\u2b55\u2610\u2611](?:[\ufe0e\ufe0f\U0001f3fb-\U0001f3ff]|\u200d[\U0001f000-\U0001faff\u2600-\u27bf])*)')
MARKERS = {
    '✅': ('CircleCheck', '已核验'), '☑': ('CircleCheck', '已勾选'),
    '☐': ('ClipboardCheck', '未勾选'), '❓': ('Info', '待确认'),
    '⚠': ('TriangleAlert', '注意'), '🚨': ('TriangleAlert', '重要提醒'),
    '🗺': ('Map', '地图'), '📍': ('Map', '地点'),
    '🍜': ('Utensils', '美食'), '🍽': ('Utensils', '用餐'),
    '🏨': ('BedDouble', '住宿'), '🎒': ('Backpack', '行李'),
    '💰': ('Wallet', '预算'), '📅': ('CalendarDays', '日期'),
}


def svg_markers(html: str, skill: Path) -> str:
    class Convert(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=False)
            self.parts = []; self.raw = None
        def handle_starttag(self, tag, attrs):
            self.parts.append(self.get_starttag_text())
            if tag in {'script', 'style', 'title'}: self.raw = tag
        def handle_startendtag(self, tag, attrs): self.parts.append(self.get_starttag_text())
        def handle_endtag(self, tag):
            self.parts.append(f'</{tag}>')
            if tag == self.raw: self.raw = None
        def handle_data(self, data):
            if self.raw == 'title':
                self.parts.append(EMOJI.sub('', data)); return
            if self.raw: self.parts.append(data); return
            def replace(match):
                key = match[0].replace('\ufe0f', '').replace('\ufe0e', '')
                name, label = MARKERS.get(key, ('Info', '提示'))
                icon = (skill / 'assets/icons' / (name + '.svg')).read_text().strip()
                return '<span title="' + label + '">' + icon + '</span>'
            self.parts.append(EMOJI.sub(replace, data))
        def handle_entityref(self, name): self.parts.append(f'&{name};')
        def handle_charref(self, name):
            value = int(name[1:], 16) if name.lower().startswith('x') else int(name)
            char = chr(value)
            if EMOJI.search(char): self.handle_data(char)
            else: self.parts.append(f'&#{name};')
        def handle_comment(self, text): self.parts.append('<!--' + text + '-->')
        def handle_decl(self, text): self.parts.append('<!' + text + '>')
    parser = Convert(); parser.feed(html); parser.close()
    return ''.join(parser.parts)
