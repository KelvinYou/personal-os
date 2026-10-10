#!/usr/bin/env python3
# flow: travel
"""Build/check standalone itinerary HTML from travel_render schema-1 Markdown."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / '.agents' / 'skills' / 'travel-plan'
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(SKILL / 'scripts'))

from lib.travel import lint_text
from lib.travel.markdown import SourceError, parse
from lib.travel.render import render
from build_share import finalize
from validate_share import validate


def build(source: Path, output: Path | None = None, *, check: bool = False,
          nojs_preview: Path | None = None) -> int:
    source = Path(source)
    output = output or source.with_name(source.stem + '-itinerary.html')
    if source.suffix.lower() != '.md': raise SourceError(1, 'input must be Markdown')
    outputs = [output] + ([nojs_preview] if nojs_preview else [])
    resolved = [p.resolve() for p in outputs]
    if source.resolve() in resolved or len(set(resolved)) != len(resolved):
        raise ValueError('source, itinerary and preview paths must be distinct')
    if any(p.suffix.lower() != '.html' for p in outputs): raise ValueError('all generated outputs must end in .html')
    if any(not p.parent.is_dir() for p in outputs): raise ValueError('output directories must already exist')
    text = source.read_text(encoding='utf-8'); plan = parse(text)
    findings = lint_text(text)
    for finding in findings: print(f'[Status: {"Critical" if finding.severity == "ERROR" else "Warning"}] {source.name}:{finding.format()}')
    if any(f.severity == 'ERROR' for f in findings): return 1
    digest = hashlib.sha256(text.encode()).hexdigest()
    candidates = {output: finalize(render(plan, SKILL, source.name, digest))}
    with tempfile.TemporaryDirectory(prefix='travel-render-') as temp:
        for i, (path, content) in enumerate(candidates.items()):
            candidate = Path(temp) / f'{i}-{path.name}'; candidate.write_text(content, encoding='utf-8')
            if validate(candidate, len(plan.days), checklists=True, ui=True): return 1
    if nojs_preview:
        import re
        candidates[nojs_preview] = re.sub(r'<script\b[^>]*>.*?</script>', '', candidates[output], flags=re.S | re.I)
    if check:
        stale = [p for p, content in candidates.items() if not p.exists() or p.read_text(encoding='utf-8') != content]
        for p in stale: print(f'[Status: Warning] Generated page is missing/stale: {p}')
        if stale: return 1
        print(f'[Status: OK] {source.name}: generated HTML matches source, renderer and canonical assets')
        return 0
    # Every page is validated before any destination is changed; replace each file atomically.
    staged = []
    try:
        for path, content in candidates.items():
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, prefix='.travel-build-', delete=False) as f:
                f.write(content); staged.append((Path(f.name), path))
        for temp_path, path in staged: temp_path.replace(path)
    finally:
        for temp_path, _path in staged: temp_path.unlink(missing_ok=True)
    for p in candidates: print(f'[Status: OK] Generated {p}')
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--nojs-preview', type=Path)
    parser.add_argument('--check', action='store_true', help='compare generated outputs without writing')
    args = parser.parse_args(argv)
    try:
        return build(args.source, args.output, check=args.check, nojs_preview=args.nojs_preview)
    except (SourceError, ValueError, OSError) as exc:
        print(f'[Status: Critical] {args.source}:{exc}', file=sys.stderr); return 1


if __name__ == '__main__': sys.exit(main())
