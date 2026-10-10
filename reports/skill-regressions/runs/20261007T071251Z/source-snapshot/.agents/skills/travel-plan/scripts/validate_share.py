#!/usr/bin/env python3
"""Validate standalone travel HTML against the skill's canonical UI assets."""
import argparse
from html.parser import HTMLParser
from pathlib import Path
import re

class Document(HTMLParser):
    VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}
    def __init__(self):
        super().__init__()
        self.stack, self.errors = [], []
        self.classes, self.ids, self.anchors = set(), set(), []
        self.days = 0
        self.nav_depth = 0
        self.nav_anchors = set()
        self.sections = {}
        self.checklist_stack = []
        self.root_attrs = {}
        self.color_scheme = None
        self.controls = {}
        self.appearance_open = False
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'html':
            self.root_attrs = attrs
        if tag == 'meta' and attrs.get('name') == 'color-scheme':
            self.color_scheme = attrs.get('content')
        if attrs.get('id') in ('theme', 'clarity', 'print'):
            self.controls[attrs['id']] = (tag, attrs, 'label' in self.stack)
        if tag == 'details' and 'appearance' in attrs.get('class', '').split():
            self.appearance_open = 'open' in attrs
        if tag not in self.VOID:
            self.stack.append(tag)
        if tag == 'nav':
            self.nav_depth += 1
        if tag == 'section':
            section_id = attrs.get('id')
            self.checklist_stack.append(section_id)
            if section_id in ('places', 'food'):
                self.sections[section_id] = 0
        classes = set(attrs.get('class', '').split())
        if 'practical-card' in classes and self.checklist_stack:
            section_id = self.checklist_stack[-1]
            if section_id in self.sections:
                self.sections[section_id] += 1
        self.classes.update(classes)
        self.days += 'daynum' in classes
        if 'id' in attrs:
            if attrs['id'] in self.ids:
                self.errors.append(f"duplicate id: {attrs['id']}")
            self.ids.add(attrs['id'])
        if tag == 'a' and attrs.get('href', '').startswith('#'):
            self.anchors.append(attrs['href'][1:])
            if self.nav_depth:
                self.nav_anchors.add(attrs['href'][1:])
        if tag == 'script' and attrs.get('src'):
            self.errors.append('external script: inline the canonical asset')
        if tag == 'link' and attrs.get('rel') == 'stylesheet':
            self.errors.append('external stylesheet: inline the canonical asset')
    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.handle_endtag(tag)
    def handle_endtag(self, tag):
        if tag == 'nav':
            self.nav_depth = max(0, self.nav_depth - 1)
        if tag == 'section' and self.checklist_stack:
            self.checklist_stack.pop()
        if not self.stack or self.stack[-1] != tag:
            self.errors.append(f'unmatched </{tag}> at line {self.getpos()[0]}')
        else:
            self.stack.pop()

def validate(path, days, checklists=False, ui=False):
    skill = Path(__file__).resolve().parents[1]
    css = (skill / 'assets/share.css').read_text(encoding='utf-8').strip()
    js = (skill / 'assets/share.js').read_text(encoding='utf-8').strip()
    text = path.read_text(encoding='utf-8')
    doc = Document()
    doc.feed(text)
    errors = doc.errors
    if doc.stack:
        errors.append('unclosed tags: ' + ', '.join(doc.stack))
    styles = re.findall(r'<style\b[^>]*>(.*?)</style>', text, re.S | re.I)
    scripts = re.findall(r'<script\b[^>]*>(.*?)</script>', text, re.S | re.I)
    if len(styles) != 1 or styles[0].strip() != css:
        errors.append('stylesheet differs from assets/share.css')
    if len(scripts) != 1 or scripts[0].strip() != js:
        errors.append('script differs from assets/share.js')
    defined = set(re.findall(r'\.([a-zA-Z][\w-]*)', css))
    missing = doc.classes - defined
    if missing:
        errors.append('undefined classes: ' + ', '.join(sorted(missing)))
    for anchor in doc.anchors:
        if anchor and anchor not in doc.ids:
            errors.append('missing anchor target: #' + anchor)
    if re.search(r'\{\{[A-Z_]+\}\}', text):
        errors.append('unresolved template placeholders')
    if doc.days != days:
        errors.append(f'expected {days} days, found {doc.days}')
    if checklists:
        for section_id in ('places', 'food'):
            if section_id not in doc.sections:
                errors.append('missing checklist section: #' + section_id)
            elif doc.sections[section_id] == 0:
                errors.append('checklist has no city cards: #' + section_id)
            if section_id not in doc.nav_anchors:
                errors.append('missing checklist navigation: #' + section_id)
    if ui:
        if doc.root_attrs.get('data-theme') != 'light' or doc.color_scheme != 'light':
            errors.append('UI must start in explicit light appearance')
        if doc.root_attrs.get('data-material') != 'glass':
            errors.append('UI must start with glass material')
        if 'appearance' not in doc.classes or doc.appearance_open:
            errors.append('appearance menu must exist and start closed')
        for control_id in ('theme', 'clarity'):
            tag, attrs, labelled = doc.controls.get(control_id, (None, {}, False))
            if (tag != 'input' or attrs.get('type') != 'checkbox' or not labelled
                    or 'checked' in attrs or 'js-only' in attrs.get('class', '').split()):
                errors.append('expected unchecked native labelled checkbox: #' + control_id)
        tag, attrs, _ = doc.controls.get('print', (None, {}, False))
        if tag != 'button' or 'js-only' not in attrs.get('class', '').split():
            errors.append('printing must be a script-only button')
        if not {'appearance-help', 'appearance-preview'}.issubset(doc.classes):
            errors.append('missing restricted-preview explanation or native printing hint')
    if errors:
        for error in errors:
            print('[Status: Critical] ' + error)
        return 1
    print(f'[Status: OK] {path.name}: balanced HTML, canonical assets, classes, anchors; {days} days')
    return 0

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('html', type=Path)
    parser.add_argument('--days', type=int, required=True)
    parser.add_argument('--checklists', action='store_true',
                        help='require places/food sections, city cards and navigation for a complete itinerary')
    parser.add_argument('--ui', action='store_true',
                        help='require white/glass defaults and native preview-safe display controls')
    args = parser.parse_args()
    if args.days < 0:
        parser.error('--days must be nonnegative')
    if args.checklists and args.days == 0:
        parser.error('--checklists requires an itinerary with at least one day')
    raise SystemExit(validate(args.html, args.days, args.checklists, args.ui))
