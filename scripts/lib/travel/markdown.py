"""Strict, escaped Markdown subset for reproducible travel pages (schema 1)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from html import escape
from html.parser import HTMLParser
import re
from urllib.parse import urlsplit

import yaml

class UniqueLoader(yaml.SafeLoader):
    pass

def unique_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise SourceError(key_node.start_mark.line + 2, f'duplicate metadata key {key}')
        result[key] = loader.construct_object(value_node, deep=deep)
    return result

UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


class SourceError(ValueError):
    def __init__(self, line: int, message: str):
        super().__init__(f'L{line}: {message}')


@dataclass
class Block:
    kind: str
    text: str
    line: int
    level: int = 0
    rows: list[list[str]] = field(default_factory=list)


@dataclass
class Plan:
    title: str
    language: str
    start: date
    end: date
    nights: int
    intro: list[Block]
    sections: dict[str, list[Block]]
    headings: dict[str, str]
    overview: Block
    days: list[tuple[int, Block, list[Block]]]
    stays: Block


def safe_url(url: str, line: int) -> str:
    if re.search(r'[\x00-\x20\x7f]', url):
        raise SourceError(line, 'link contains whitespace/control characters; URL-encode them')
    scheme = urlsplit(url).scheme.lower()
    if not (scheme in {'https', 'http', 'tel', 'mailto'} or url.startswith('#')):
        raise SourceError(line, 'links must use http(s), tel, mailto or a local anchor')
    return escape(url, quote=True)


def inline(text: str, line: int = 1) -> str:
    """No raw HTML. Balanced link destinations allow parentheses in map URLs."""
    out, i = [], 0
    while i < len(text):
        if text[i] == '\\' and i + 1 < len(text):
            out.append(escape(text[i + 1])); i += 2; continue
        if text.startswith('![', i):
            raise SourceError(line, 'images are not supported in schema 1')
        marker = next((m for m in ('**', '~~', '`') if text.startswith(m, i)), None)
        if marker:
            end = text.find(marker, i + len(marker))
            if end < 0:
                raise SourceError(line, f'unclosed inline delimiter {marker}')
            body = text[i + len(marker):end]
            tag = {'**': 'strong', '~~': 'del', '`': 'code'}[marker]
            out.append(f'<{tag}>' + (escape(body) if marker == '`' else inline(body, line)) + f'</{tag}>')
            i = end + len(marker); continue
        if text[i] == '[':
            label_end = text.find(']', i + 1)
            if label_end >= 0 and text[label_end + 1:label_end + 2] == '(':
                j, depth = label_end + 2, 1
                while j < len(text) and depth:
                    if text[j] == '(' : depth += 1
                    elif text[j] == ')' : depth -= 1
                    j += 1
                if depth:
                    raise SourceError(line, 'unclosed link destination')
                dest = text[label_end + 2:j - 1]
                out.append(f'<a href="{safe_url(dest, line)}">{inline(text[i + 1:label_end], line)}</a>')
                i = j; continue
            if label_end >= 0 and text[label_end + 1:label_end + 2] == '[':
                raise SourceError(line, 'reference links are not supported; use inline links')
        if text.startswith('<br>', i) or text.startswith('<br/>', i) or text.startswith('<br />', i):
            stop = text.index('>', i) + 1
            out.append('<br>'); i = stop; continue
        if text[i] == '<':
            end = text.find('>', i)
            if end >= 0 and text[i + 1:end].startswith(('https://', 'http://')):
                dest = text[i + 1:end]
                out.append(f'<a href="{safe_url(dest, line)}">{escape(dest)}</a>'); i = end + 1; continue
            raise SourceError(line, 'raw HTML is not supported; use Markdown')
        out.append(escape(text[i])); i += 1
    return ''.join(out)


class Text(HTMLParser):
    def __init__(self): super().__init__(); self.parts = []
    def handle_data(self, data): self.parts.append(data)


def plain(text: str, line: int = 1) -> str:
    parser = Text(); parser.feed(inline(text, line)); return ''.join(parser.parts)


def split_row(text: str) -> list[str]:
    # Escaped pipes are literal cell content, not column separators.
    return re.split(r'(?<!\\)\|', text.strip().strip('|'))


def blocks(lines: list[str], start: int = 0) -> list[Block]:
    result, i = [], 0
    while i < len(lines):
        text, line = lines[i].strip(), start + i + 1
        if not text or re.fullmatch(r'-{3,}|\*{3,}', text): i += 1; continue
        if text.startswith('```') or text.startswith('~~~'):
            raise SourceError(line, 'fenced code is not supported in travel-render schema 1')
        heading = re.fullmatch(r'(#{1,6})\s+(.+)', text)
        if heading:
            result.append(Block('heading', heading[2], line, len(heading[1]))); i += 1; continue
        if text.startswith('|'):
            headers = [c.strip() for c in split_row(text)]
            if i + 1 >= len(lines) or not all(re.fullmatch(r':?-{3,}:?', c.strip()) for c in split_row(lines[i + 1])):
                raise SourceError(line, 'table must have a Markdown separator row')
            if len(split_row(lines[i + 1])) != len(headers):
                raise SourceError(line + 1, 'table separator column count differs from header')
            rows, j = [headers], i + 2
            while j < len(lines) and lines[j].strip().startswith('|'):
                row = [c.strip() for c in split_row(lines[j])]
                if len(row) != len(headers):
                    raise SourceError(start + j + 1, f'table expects {len(headers)} columns, found {len(row)}')
                rows.append(row); j += 1
            result.append(Block('table', '', line, rows=rows)); i = j; continue
        if text.startswith('>'):
            parts, j = [], i
            while j < len(lines) and lines[j].strip().startswith('>'):
                parts.append(re.sub(r'^>\s?', '', lines[j].strip())); j += 1
            result.append(Block('quote', '\n'.join(parts), line)); i = j; continue
        item = re.fullmatch(r'(?:[-*+] |\d+\. )(.+)', text)
        if item:
            result.append(Block('item', item[1], line)); i += 1; continue
        parts, j = [text], i + 1
        while j < len(lines) and lines[j].strip() and not re.match(r'^(?:#|>|\||[-*+] |\d+\. |---|```)', lines[j].strip()):
            parts.append(lines[j].strip()); j += 1
        result.append(Block('paragraph', '\n'.join(parts), line)); i = j
    return result


def date_in(text: str, year: int, line: int) -> date:
    match = re.search(r'(?<!\d)(\d{1,2})/(\d{1,2})(?!\d)', plain(text, line))
    if not match: raise SourceError(line, 'expected an explicit M/D date')
    try: return date(year, int(match[1]), int(match[2]))
    except ValueError as exc: raise SourceError(line, str(exc)) from exc


def parse(source: str) -> Plan:
    lines = source.splitlines()
    if not lines or lines[0] != '---':
        raise SourceError(1, 'missing travel_render frontmatter; normalize this legacy source before building')
    try: end = lines.index('---', 1)
    except ValueError: raise SourceError(1, 'frontmatter is not closed')
    try: meta = yaml.load('\n'.join(lines[1:end]), Loader=UniqueLoader)
    except yaml.YAMLError as exc: raise SourceError(1, f'invalid frontmatter: {exc}') from exc
    if not isinstance(meta, dict) or set(meta) != {'travel_render'} or not isinstance(meta['travel_render'], dict):
        raise SourceError(1, 'frontmatter must contain only travel_render metadata')
    config = meta['travel_render']
    if set(config) - {'schema', 'language', 'title'}:
        raise SourceError(1, 'unknown travel_render field; supported fields: schema, language, title')
    if type(config.get('schema')) is not int or config['schema'] != 1:
        raise SourceError(1, 'travel_render.schema must be integer 1')
    language = config.get('language', 'zh-CN')
    if language not in {'zh-CN', 'en'}:
        raise SourceError(1, 'language must be zh-CN or en')
    if 'title' in config and (not isinstance(config['title'], str) or not config['title'].strip()):
        raise SourceError(1, 'display title must be a nonempty string')
    content = blocks(lines[end + 1:], end + 1)
    if not content or content[0].kind != 'heading' or content[0].level != 1:
        raise SourceError(end + 2, 'expected one H1 trip title with YYYY-MM-DD → YYYY-MM-DD dates')
    heading = content.pop(0)
    dates = re.findall(r'\d{4}-\d{2}-\d{2}', heading.text)
    if len(dates) != 2: raise SourceError(heading.line, 'trip title must contain exactly two ISO dates')
    try: start_date, end_date = map(date.fromisoformat, dates)
    except ValueError as exc: raise SourceError(heading.line, str(exc)) from exc
    if start_date > end_date: raise SourceError(heading.line, 'trip date range is reversed')
    sections, headings, intro, current = {}, {}, [], None
    for block in content:
        if block.kind == 'heading' and block.level == 1:
            raise SourceError(block.line, 'multiple H1 trip titles')
        if block.kind == 'heading' and block.level == 2:
            match = re.match(r'^(\d+(?:\.\d+)?)(?:\.|\s)\s*(.*)', block.text)
            if not match: raise SourceError(block.line, 'H2 sections must use numbered travel section headings')
            current = match[1]
            if current in sections: raise SourceError(block.line, f'duplicate section {current}')
            if current not in {str(n) for n in range(13)} | {'4.1'}:
                raise SourceError(block.line, f'unsupported section {current}')
            sections[current], headings[current] = [], block.text
        elif current is None: intro.append(block)
        else: sections[current].append(block)
    required = {str(n) for n in range(13)} | {'4.1'}
    if required - sections.keys():
        raise SourceError(heading.line, 'missing sections: ' + ', '.join(sorted(required - sections.keys())))
    overview = next((b for b in sections['0'] if b.kind == 'table'), None)
    expected = ['Day', '日期', '城市/主题', '住宿', '主要交通']
    if overview is None or overview.rows[0] != expected:
        raise SourceError(overview.line if overview else heading.line, 'overview table columns must be ' + ' | '.join(expected))
    night_candidates = re.findall(r'(\d+)\s*晚', ' '.join(b.text for b in sections['0'] if b.kind != 'table'))
    if len(set(night_candidates)) != 1: raise SourceError(overview.line, 'overview must state one unambiguous total night count')
    nights = int(night_candidates[0])
    days, day_heading, body = [], None, []
    for block in sections['4']:
        if block.kind == 'heading' and block.level == 3 and re.match(r'Day\s+\d+\b', block.text):
            match = re.match(r'Day\s+(\d+)\b', block.text)
            if day_heading is not None: days.append((int(re.match(r'Day\s+(\d+)', day_heading.text)[1]), day_heading, body))
            day_heading, body = block, []
        elif day_heading is not None: body.append(block)
    if day_heading is not None: days.append((int(re.match(r'Day\s+(\d+)', day_heading.text)[1]), day_heading, body))
    numbers = [n for n, _h, _b in days]
    if not numbers or numbers != list(range(1, len(days) + 1)):
        raise SourceError(heading.line, 'daily headings must be consecutive Day 1…N')
    overview_rows = {int(r[0]): r for r in overview.rows[1:] if re.fullmatch(r'\d+', r[0])}
    if len(overview_rows) != len(overview.rows) - 1 - sum(r[0] == '—' for r in overview.rows[1:]):
        raise SourceError(overview.line, 'duplicate/invalid overview day identifier')
    if set(overview_rows) != set(numbers): raise SourceError(overview.line, 'overview days do not agree with daily headings')
    daily_dates = []
    for n, h, day_blocks in days:
        d = date_in(h.text, start_date.year, h.line); daily_dates.append(d)
        if date_in(overview_rows[n][1], start_date.year, overview.line) != d:
            raise SourceError(h.line, f'Day {n} date differs from overview')
        tables = [b for b in day_blocks if b.kind == 'table']
        timelines = [b for b in tables if b.rows[0] == ['时间', '安排', '地图', '门票', '备注']]
        if len(timelines) != 1:
            raise SourceError(h.line, 'each day needs one 时间 | 安排 | 地图 | 门票 | 备注 table')
        if not any(b.kind == 'quote' and '定位' in b.text for b in day_blocks):
            raise SourceError(h.line, 'each day needs a quoted 定位 purpose')
    if daily_dates != sorted(set(daily_dates)) or daily_dates[0] != start_date or daily_dates[-1] > end_date:
        raise SourceError(heading.line, 'daily dates must be unique, chronological and within trip range')
    extra_dates = [date_in(r[1], start_date.year, overview.line) for r in overview.rows[1:] if r[0] == '—']
    trip_dates = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]
    if sorted(d for d in daily_dates + extra_dates if start_date <= d <= end_date) != trip_dates:
        raise SourceError(heading.line, 'daily routes must cover every trip date through departure')
    active_stays = False; stay_tables = []
    for b in sections['2']:
        if b.kind == 'heading': active_stays = b.text == '2.1.1 当前住宿（展示表）'
        if active_stays and b.kind == 'table': stay_tables.append(b)
    if len(stay_tables) != 1 or stay_tables[0].rows[0] != ['入住日期', '酒店 / 地址 / 地图', '状态', '位置与衔接', '待确认事项']:
        raise SourceError(heading.line, 'need one 2.1.1 当前住宿（展示表） with the documented five columns')
    stays = stay_tables[0]; stay_nights = 0; occupied = set()
    for r in stays.rows[1:]:
        ds = re.findall(r'(\d{1,2})/(\d{1,2})', plain(r[0], stays.line))
        if len(ds) != 2: raise SourceError(stays.line, 'each stay must contain explicit M/D–M/D dates')
        try: a, b = [date(start_date.year, int(m), int(d)) for m, d in ds]
        except ValueError as exc: raise SourceError(stays.line, str(exc)) from exc
        if b <= a: raise SourceError(stays.line, 'stay checkout must be after checkin')
        covered = {a + timedelta(days=i) for i in range((b - a).days)}
        if occupied & covered: raise SourceError(stays.line, 'current stay date ranges overlap')
        if a < start_date - timedelta(days=1) or b > end_date:
            raise SourceError(stays.line, 'stay dates fall outside the trip/optional prearrival night')
        occupied.update(covered)
        stay_nights += (b - a).days
        if r[2] not in {'已选', '待确认', '已预订'}:
            raise SourceError(stays.line, 'stay 状态 must be 已选, 待确认 or 已预订; no inference from prose')
    if stay_nights != nights: raise SourceError(stays.line, f'stay nights {stay_nights} differ from overview total {nights}')
    for key in ['4.1', '5']:
        if not any(b.kind == 'heading' for b in sections[key]): raise SourceError(heading.line, f'section {key} needs city headings')
        for b in sections[key]:
            if b.kind == 'table' and len(b.rows[0]) != 4 and not (key == '5' and b.rows[0] == ['日期', '主餐优先', '有胃口再补']):
                raise SourceError(b.line, 'checklist tables must have four columns, or the documented meal-summary columns')
    # Validate inline grammar/URLs for every block, including collapsed history.
    for b in intro + [b for seq in sections.values() for b in seq]:
        inline(b.text, b.line)
        for row in b.rows:
            for cell in row: inline(cell, b.line)
    title = config.get('title') or heading.text[:heading.text.index(dates[0])].strip()
    return Plan(title, language, start_date, end_date, nights, intro, sections, headings, overview, days, stays)
