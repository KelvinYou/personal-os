#!/usr/bin/env python3
# flow: docs-check
"""Claude Code Stop hook: no deck is delivered while `make deck-lint` fails.

Reads the hook JSON on stdin. Lints every .pptx in the repo modified since this
session's transcript was created. Project hook (.claude/settings.json) scans
personal-os; `--global` (~/.claude/settings.json) scans the session's project
instead, skipping personal-os so the two never double-report. Thresholds always
come from personal-os data/config/thresholds.yaml. On findings, returns {"decision": "block"} so
the agent must fix the deck, or explicitly report it as an undelivered draft.
`stop_hook_active` (the agent is already continuing because of this hook) lets
the stop through, so the hook can never loop. Always exits 0.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from lib.config import load_thresholds  # noqa: E402
from lib.deck import lint_deck, sidecar_exempt  # noqa: E402

PRUNE = {".git", "node_modules", ".next", ".venv", "venv", "repos", "__pycache__",
         "dist", "build", "target", ".cache", ".gradle", "Pods"}
WALK_BUDGET_SECONDS = 5.0  # a Stop hook must stay fast in large monorepos


def changed_decks(root: Path, since: float) -> list[Path]:
    out = []
    deadline = time.monotonic() + WALK_BUDGET_SECONDS
    for dirpath, dirnames, filenames in os.walk(root):
        if time.monotonic() > deadline:
            break
        dirnames[:] = [d for d in dirnames if d not in PRUNE]
        for name in filenames:
            if name.endswith(".pptx") and not name.startswith("~$"):
                p = Path(dirpath) / name
                if p.stat().st_mtime >= since:
                    out.append(p)
    return sorted(out)


def session_start(transcript: str | None) -> float | None:
    if not transcript or not Path(transcript).is_file():
        return None
    st = Path(transcript).stat()
    return getattr(st, "st_birthtime", st.st_ctime)


def scan_root(event: dict, global_mode: bool) -> Path | None:
    """Repo to scan. --global (user settings): the session's project, except
    personal-os itself, whose project-level hook already covers it."""
    if not global_mode:
        return ROOT
    project = os.environ.get("CLAUDE_PROJECT_DIR") or event.get("cwd")
    if not project:
        return None
    root = Path(project).resolve()
    return None if root == ROOT or root == Path.home() else root


def main(argv: list[str]) -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    if event.get("stop_hook_active"):
        return 0
    since = session_start(event.get("transcript_path"))
    root = scan_root(event, "--global" in argv)
    if since is None or root is None:
        return 0
    decks = changed_decks(root, since)
    if not decks:
        return 0
    cfg = load_thresholds().presentation
    if cfg is None:
        return 0

    report = []
    for deck in decks:
        findings = lint_deck(deck, cfg, sidecar_exempt(deck))
        if findings:
            report.append(str(deck.relative_to(root)))
            report += [f"  {f.format()}" for f in findings]
    if report:
        reason = ("deck-lint failed on decks changed this session "
                  "(docs/presentation-guide.md § Visual acceptance):\n" + "\n".join(report) +
                  f"\n\nFix the slides and re-run `{sys.executable} {ROOT / 'scripts/deck_lint.py'} DECK.pptx`. "
                  "If you stop without fixing, "
                  "report the deck as a draft with these findings, not as delivered. Appendix inventories "
                  'may be exempted via {"deck_lint": {"exempt": [n], "reason": "..."}} in production.json.')
        print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
