"""Render parsed travel Markdown into the existing standalone travel components."""
from __future__ import annotations

from datetime import timedelta
from html import escape
from pathlib import Path
import re

from .icons import svg_markers
from .markdown import Block, Plan, SourceError, date_in, inline, plain


def severity(text: str) -> str:
    if '🚨' in text or '🔴' in text: return 'alert'
    if '⚠️' in text or '❓' in text or '待确认' in text: return 'warning'
    return 'info'


def notice(text: str, line: int, title: str = '') -> str:
    kind = severity(text)
    label = title or {'alert': '重要提醒', 'warning': '注意 / 待确认', 'info': '说明'}[kind]
    return f'<div class="notice {kind}"><div class="notice-copy"><span class="notice-title">{escape(label)}</span><p>{inline(text, line).replace(chr(10), "<br>")}</p></div></div>'


def table(block: Block) -> str:
    headers, *rows = block.rows
    return '<div class="scroll"><table><thead><tr>' + ''.join(f'<th>{inline(x, block.line)}</th>' for x in headers) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join(f'<td>{inline(x, block.line)}</td>' for x in row) + '</tr>' for row in rows) + '</tbody></table></div>'


def generic(blocks: list[Block], omit: Block | None = None) -> str:
    out = []
    for b in blocks:
        if b is omit: continue
        if b.kind == 'heading': out.append(f'<h3>{inline(b.text, b.line)}</h3>')
        elif b.kind == 'table': out.append(table(b))
        elif b.kind == 'quote': out.append(notice(b.text, b.line))
        elif b.kind == 'item':
            text = re.sub(r'^\[([ xX])\]\s*', lambda m: '☑ ' if m[1].lower() == 'x' else '☐ ', b.text)
            if severity(text) in {'alert', 'warning'}: out.append(notice(text, b.line))
            else: out.append(f'<ul class="plain"><li>{inline(text, b.line)}</li></ul>')
        elif severity(b.text) in {'alert', 'warning'}: out.append(notice(b.text, b.line))
        else: out.append('<p>' + inline(b.text, b.line).replace('\n', '<br>') + '</p>')
    return ''.join(out)


def heading(title: str) -> str:
    return f'<div class="section-head"><h2>{escape(title)}</h2></div>'


def priority(plan: Plan) -> str:
    items = []
    for b in plan.intro:
        if b.kind == 'quote':
            for line in b.text.splitlines():
                m = re.match(r'\d+\.\s+(.+)', line)
                if m: items.append((m[1], b.line))
    if not items: return ''
    cards = ''.join('<article class="action-card">' + notice(t, line, '🚨 重要' if severity(t) == 'alert' else '⚠ 待确认' if severity(t) == 'warning' else '准备') + '</article>' for t, line in items)
    return '<section class="priority" id="before">' + heading('先确认，再出发') + '<div class="action-grid">' + cards + '</div></section>'


def stay_cards(plan: Plan) -> str:
    cards = []
    for dates, name, status, context, pending in plan.stays.rows[1:]:
        style = 'selected' if status in {'已选', '已预订'} else 'pending'
        name_parts = name.split('，', 1)
        details = '<p class="hotel-meta">' + inline(name_parts[1], plan.stays.line) + '</p>' if len(name_parts) > 1 else ''
        cards.append('<article class="hotel"><span class="status ' + style + '">' + escape(status) + '</span><p class="hotel-meta">' + inline(dates, plan.stays.line) + '</p><h3>' + inline(name_parts[0], plan.stays.line) + '</h3>' + details + '<p>' + inline(context, plan.stays.line) + '</p>' + notice(pending, plan.stays.line, '下单 / 入住前确认') + '</article>')

    return '<div class="grid">' + ''.join(cards) + '</div>'


def overview(plan: Plan) -> str:
    items = []
    for n, dates, title, lodging, transport in plan.overview.rows[1:]:
        if n == '—':
            items.append('<div class="panel"><p>' + ' · '.join(inline(x, plan.overview.line) for x in [dates, title, lodging, transport]) + '</p></div>')
            continue
        items.append(f'<a href="#day-{n}"><span class="label"><b>{inline(dates, plan.overview.line)}</b><span>Day {n}</span></span><h3>{inline(title, plan.overview.line)}</h3><p>{inline(lodging, plan.overview.line)} · {inline(transport, plan.overview.line)}</p></a>')
    # Anchor cards must not contain nested links from overview cell Markdown.
    # Render rich overview cells separately if they contain links rather than silently dropping them.
    if any('[' in cell for row in plan.overview.rows[1:] for cell in row):
        raise SourceError(plan.overview.line, 'overview cards cannot contain inline links; keep maps in day rows')
    return '<div class="overview">' + ''.join(items) + '</div>' + generic(plan.sections['0'], plan.overview)


def map_links(text: str, line: int) -> list[str]:
    html = inline(text, line)
    return re.findall(r'<a href="(?:https?://(?:uri\.amap\.com|www\.google\.com/maps|maps\.google\.com|map\.baidu\.com)[^"]*)">.*?</a>', html)


def render_days(plan: Plan) -> str:
    result = []
    prelude = []
    for b in plan.sections['4']:
        if b.kind == 'heading': break
        prelude.append(b)
    result.append(generic(prelude))
    for number, day_heading, body in plan.days:
        purpose = next(b for b in body if b.kind == 'quote' and '定位' in b.text)
        parts = purpose.text.splitlines()
        purpose_line = next(x for x in parts if '定位' in x)
        purpose_text = re.sub(r'^\*\*定位[：:]\s*(.*?)\*\*(.*)$', r'\1\2', purpose_line)
        title = re.sub(r'^Day\s+\d+\s*[（(].*?[）)]\s*', '', day_heading.text)
        day_date = date_in(day_heading.text, plan.start.year, day_heading.line)
        out = [f'<article class="day" id="day-{number}"><div class="dayhead"><span class="daynum">DAY {number:02d}</span><div><span class="daydate">{day_date:%m/%d}</span><h3 class="daytitle">{inline(title, day_heading.line)}</h3></div></div><p class="daylede">{inline(purpose_text, purpose.line)}</p>']
        additional = [x for x in parts if x != purpose_line]
        if additional: out.append(notice('\n'.join(additional), purpose.line))
        last_maps = []
        for b in body:
            if b is purpose: continue
            if b.kind != 'table':
                fallback = re.match(r'\*\*(.+?备选.*?)\*\*[:：]?(.*)', b.text, re.S)
                if fallback:
                    # Explicit blocking risks remain visible; ordinary alternatives can collapse.
                    if severity(b.text) in {'alert', 'warning'}: out.append(generic([b]))
                    else: out.append('<details class="note"><summary>' + inline(fallback[1], b.line) + '</summary><p>' + inline(fallback[2], b.line) + '</p></details>')
                else: out.append(generic([b]))
                continue
            if b.rows[0] != ['时间', '安排', '地图', '门票', '备注']:
                out.append(table(b)); continue
            out.append('<ul class="sched">')
            for time, activity, maps, ticket, notes in b.rows[1:]:
                current_maps = map_links(activity, b.line) + map_links(maps, b.line)
                if current_maps: last_maps = list(dict.fromkeys(current_maps))
                if maps == '同上' and not last_maps:
                    raise SourceError(b.line, '同上 map has no preceding/current explicit map link')
                links = (' · '.join(last_maps) if maps == '同上' else inline(maps, b.line))
                label = ('🚨 重要提醒' if severity(notes + ticket) == 'alert' else '⚠ 待确认 / 注意' if severity(notes + ticket) == 'warning' else '')
                risk = '<span class="risk-label">' + label + '</span>' if label else ''
                placeholders = {'', '—', '–', '-'}
                maps_html = '<p class="sub">' + links + '</p>' if plain(maps, b.line).strip() not in placeholders else ''
                ticket_html = '<span class="tag' + (' warn' if severity(ticket) == 'warning' else '') + '">' + inline(ticket, b.line) + '</span>' if plain(ticket, b.line).strip() not in placeholders else ''
                notes_html = '<span class="meta">' + inline(notes, b.line) + '</span>' if plain(notes, b.line).strip() not in placeholders else ''
                out.append('<li><span class="time"><strong>' + inline(time, b.line) + '</strong></span><div class="what"><strong>' + inline(activity, b.line) + '</strong>' + maps_html + ticket_html + risk + notes_html + '</div></li>')
            out.append('</ul>')
        out.append('</article>'); result.append(''.join(out))
    return ''.join(result)


def dates_linked(text: str, plan: Plan, line: int) -> str:
    found = set()
    for m in re.finditer(r'(\d{1,2})/(\d{1,2})(?:[–—-](?:(\d{1,2})/)?(\d{1,2}))?', plain(text, line)):
        start = date_in(m[0], plan.start.year, line)
        end = start
        if m[4]:
            try: end = start.replace(month=int(m[3] or m[1]), day=int(m[4]))
            except ValueError as exc: raise SourceError(line, str(exc)) from exc
        if end < start: raise SourceError(line, 'checklist date range is reversed')
        while start <= end:
            found.add(start); start += timedelta(days=1)
    links = []
    day_dates = {date_in(h.text, plan.start.year, h.line): n for n, h, _ in plan.days}
    for d in sorted(found):
        if d not in day_dates: raise SourceError(line, f'checklist date {d:%m/%d} has no daily route')
        links.append(f'<a href="#day-{day_dates[d]}">{d:%m/%d} · 查看当天 ↗</a>')
    return inline(text, line) + ('<br>' + ' · '.join(links) if links else '')


def checklist(plan: Plan, key: str) -> str:
    out, active = [], False
    for b in plan.sections[key]:
        if b.kind == 'heading':
            if active: out.append('</article>')
            out.append('<article class="practical-card"><p class="eyebrow">' + inline(b.text, b.line) + '</p>'); active = True
        elif b.kind == 'table':
            if not active: raise SourceError(b.line, 'checklist table requires a preceding city heading')
            if b.rows[0] == ['日期', '主餐优先', '有胃口再补']:
                out.append(table(b)); continue
            out.append('<ul class="plain">')
            for row in b.rows[1:]:
                priority_label, name, third, fourth = row
                assigned, description = (third, fourth) if key == '4.1' else (fourth, third)
                out.append('<li><span class="tag">' + inline(priority_label, b.line) + '</span> <strong>' + inline(name, b.line) + '</strong><p>' + inline(description, b.line) + '</p><p class="sub">安排：' + dates_linked(assigned, plan, b.line) + '</p></li>')
            out.append('</ul>')
        else: out.append(generic([b]))
    if active: out.append('</article>')
    return '<div class="grid">' + ''.join(out) + '</div>'


def supporting(plan: Plan) -> str:
    out = []
    for key, anchor in [('1', 'basics'), ('2', 'preparation'), ('3', 'activities'), ('6', 'risks'), ('7', 'budget'), ('8', 'packing'), ('9', 'contacts'), ('10', 'recheck'), ('11', 'history'), ('12', 'sources')]:
        content = generic([b for b in plan.sections[key] if not (key == '2' and b.kind == 'heading' and b.text == '2.1.1 当前住宿（展示表）')], plan.stays if key == '2' else None)
        if key in {'11', '12'}:
            out.append(f'<section id="{anchor}"><details class="note"><summary>{escape(plan.headings[key])}</summary>{content}</details></section>')
        else: out.append(f'<section id="{anchor}">' + heading(plan.headings[key]) + '<div class="panel">' + content + '</div></section>')
    # All introductory evidence/freshness prose is retained; priority actions also appear above.
    out.append('<section id="verification"><details class="note"><summary>版本与查证范围</summary>' + generic(plan.intro) + '</details></section>')
    return ''.join(out)


def render(plan: Plan, skill: Path, source_name: str, digest: str) -> str:
    version = next((b.text.splitlines()[0] for b in plan.intro if '版本' in b.text), '版本未注明')
    values = {
        'PAGE_TITLE': escape(plan.title), 'SHARE_CSS': '', 'SHARE_JS': '',
        'TRIP_NAME': escape(plan.title), 'DATE_RANGE': f'{plan.start.isoformat()} → {plan.end.isoformat()}',
        'TRIP_LEDE': inline(version), 'DAYS': str(len(plan.days)), 'NIGHTS': str(plan.nights),
        'ROUTE_SUMMARIES': '<p class="sub">' + '行程以当前版本为准；已选酒店不代表已付款。</p>',
        'PRIORITY_ACTIONS': priority(plan),
        'OVERVIEW': overview(plan), 'STAYS': stay_cards(plan),
        'DAYS_CONTENT': render_days(plan),
        'PLACES_CONTENT': checklist(plan, '4.1'),
        'FOOD_CONTENT': checklist(plan, '5'),
        'PRACTICAL_SECTIONS': supporting(plan),
        'FRESHNESS_NOTE': '自动生成 · 来源：' + escape(source_name) + '<br>核验日期与范围见正文；生成时间不代表重新查证。',
    }
    text = (skill / 'templates/share.html').read_text(encoding='utf-8')
    text = re.sub(r'\{\{([A-Z_]+)\}\}', lambda m: values[m[1]], text)
    text = text.replace('lang="en"', f'lang="{plan.language}"', 1)
    if plan.language == 'zh-CN':
        for a, b in [('Skip to itinerary', '跳到行程内容'), ('Trip workspace', '旅行计划'), ('Trip navigation', '行程导航'), ('Overview', '速览'), ('Stays', '住宿'), ('Days', '逐日'), ('Must-visit places', '必去地点'), ('Must-eat food', '必吃美食'), ('At a glance', '一页速览'), ('Where to stay', '住宿安排'), ('Day by day', '逐日行程'), ('Priorities · Along the route · Alternatives', '必去 · 顺路 · 备选'), ('Priorities · Meal alternatives · Small tastes nearby', '必吃 · 餐次备选 · 顺路尝鲜'), ('Back to top', '回到顶部')]:
            # Translate template-only labels, never arbitrary trip prose or source URLs.
            text = re.sub(r'(?<=>)' + re.escape(a) + r'(?=<)', b, text)
        text = text.replace('aria-label="Trip navigation"', 'aria-label="行程导航"')
        text = text.replace(f'{len(plan.days)} days</b>', f'{len(plan.days)} 天</b>').replace(f'{plan.nights} nights</b>', f'{plan.nights} 晚</b>')
    provenance = f'<!-- Generated by scripts/travel_build.py; source={escape(source_name)}; sha256={digest}; travel_render=1. Edit the Markdown source, not this HTML. -->'
    return svg_markers(text.replace('<head>', '<head>\n' + provenance, 1), skill)
