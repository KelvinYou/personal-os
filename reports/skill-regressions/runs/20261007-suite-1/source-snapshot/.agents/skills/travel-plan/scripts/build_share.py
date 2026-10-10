#!/usr/bin/env python3
"""Finalize authored travel HTML with canonical UI, then validate before saving."""
import argparse
from pathlib import Path
import re
import tempfile

from validate_share import validate

SKILL = Path(__file__).resolve().parents[1]
APPEARANCE = re.compile(r'<details\b[^>]*class="appearance"[^>]*>.*?</details>', re.S | re.I)


def controls(language):
    template = (SKILL / 'templates/share.html').read_text(encoding='utf-8')
    menus = APPEARANCE.findall(template)
    if len(menus) != 1:
        raise ValueError('Canonical template must contain exactly one appearance menu')
    menu = menus[0]
    if language.startswith('zh'):
        translations = {
            'Display options': '显示选项',
            'Dark appearance': '深色外观',
            'Reduce glass': '减少玻璃',
            '>Print<': '>打印<',
            'Appearance controls are unavailable in this preview. Save the file and open it in a browser; the itinerary remains readable.': '此预览不支持外观切换。请保存文件后用浏览器打开；行程内容仍可正常阅读。',
            'Use the checkboxes to change appearance. For printing, use the system share menu or open in a browser.': '可直接勾选切换外观。打印请使用系统共享菜单，或在浏览器中打开。',
        }
        for source, target in translations.items():
            menu = menu.replace(source, target)
    elif not language.startswith('en'):
        raise ValueError('Control labels support en/zh; add a canonical translation for this language before building')
    return menu


def finalize(text):
    """Replace only the UI shell; leave main trip content and its links intact."""
    roots = re.findall(r'<html\b[^>]*>', text, re.I)
    if len(roots) != 1:
        raise ValueError('Expected exactly one html element')
    language = re.search(r'\blang=["\']([^"\']+)', roots[0], re.I)
    if not language:
        raise ValueError('Set the page language before building')
    root = re.sub(r'\sdata-(?:theme|material)=["\'][^"\']*["\']', '', roots[0], flags=re.I)
    root = root[:-1] + ' data-theme="light" data-material="glass">'
    text = text.replace(roots[0], root, 1)
    meta = r'<meta\b(?=[^>]*\bname=["\']color-scheme["\'])[^>]*>'
    count = len(re.findall(meta, text, re.I))
    if count > 1:
        raise ValueError('Expected at most one color-scheme meta element')
    if count:
        text = re.sub(meta, '<meta name="color-scheme" content="light">', text, count=1, flags=re.I)
    else:
        text = re.sub(r'<head\b[^>]*>', lambda m: m[0] + '\n<meta name="color-scheme" content="light">', text, count=1, flags=re.I)
    for tag, asset in [('style', 'share.css'), ('script', 'share.js')]:
        pattern = rf'<{tag}\b[^>]*>.*?</{tag}>'
        if len(re.findall(pattern, text, re.S | re.I)) != 1:
            raise ValueError(f'Expected exactly one {tag} block; consolidate custom assets before building')
        content = (SKILL / 'assets' / asset).read_text(encoding='utf-8')
        text = re.sub(pattern, lambda m: f'<{tag}>{content}</{tag}>', text, count=1, flags=re.S | re.I)
    if len(APPEARANCE.findall(text)) != 1:
        raise ValueError('Expected exactly one appearance menu; start from templates/share.html')
    return APPEARANCE.sub(lambda m: controls(language[1].lower()), text, count=1)


def build(source, output, days, checklists=False, nojs_preview=None):
    if days < 0 or (checklists and days == 0):
        raise ValueError('Days must be nonnegative; checklists require at least one day')
    if nojs_preview and nojs_preview.resolve() in (source.resolve(), output.resolve()):
        raise ValueError('No-script preview must not overwrite the source or deliverable')
    if not output.parent.is_dir() or (nojs_preview and not nojs_preview.parent.is_dir()):
        raise ValueError('Output directories must already exist')
    text = finalize(source.read_text(encoding='utf-8'))
    with tempfile.TemporaryDirectory(prefix='travel-share-') as temp:
        candidate = Path(temp) / output.name
        candidate.write_text(text, encoding='utf-8')
        if validate(candidate, days, checklists, ui=True):
            return 1
    # No destination is modified until the final authored page passes validation.
    if nojs_preview:
        preview = re.sub(r'<script\b[^>]*>.*?</script>', '', text, flags=re.S | re.I)
        nojs_preview.write_text(preview, encoding='utf-8')
    output.write_text(text, encoding='utf-8')
    print(f'[Status: OK] Saved {output}')
    if nojs_preview:
        print(f'[Status: OK] Script-disabled visual preview: {nojs_preview}')
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('html', type=Path, help='authored HTML; this script does not invent trip content')
    parser.add_argument('--output', type=Path, required=True, help='deliverable path; may equal input')
    parser.add_argument('--days', type=int, required=True)
    parser.add_argument('--checklists', action='store_true')
    parser.add_argument('--nojs-preview', type=Path, help='optional separate preview with script removed')
    args = parser.parse_args()
    try:
        return build(args.html, args.output, args.days, args.checklists, args.nojs_preview)
    except (OSError, ValueError) as error:
        parser.exit(1, f'[Status: Critical] {error}\n')


if __name__ == '__main__':
    raise SystemExit(main())
