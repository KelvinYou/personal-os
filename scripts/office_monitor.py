#!/usr/bin/env python3
# flow: office
"""On-demand local Codex + Claude Code snapshot. No daemon, hooks, model calls or task execution."""
from __future__ import annotations

import argparse
import json
import sys

from lib.config import ROOT, load_thresholds
from lib.office.monitor import Monitor
from lib.office.sources import claude_projects, codex_sessions


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Machine-readable snapshot")
    args = parser.parse_args()
    try:
        cfg = load_thresholds().office
        if cfg is None: raise ValueError("office_not_configured")
        data = ROOT / "data"
        cache = data / "runtime" / "ai-office"
        if not data.is_dir() or not cache.resolve().is_relative_to(data.resolve()): raise ValueError("private_storage_unavailable")
        result = Monitor(codex_sessions(), ROOT, cache, cfg, claude_projects()).snapshot()
        if args.json:
            print(json.dumps(result, separators=(",", ":")))
        else:
            sources = ", ".join(f"{name} {state}" for name, state in result["source_coverage"].items())
            zones = {zone: sum(s["attention"] == zone for s in result["sessions"]) for zone in ("needs_you", "working", "review", "done")}
            print(f"[Status: {'Warning' if result['warnings'] else 'OK'}] Local records ({sources}): {len(result['sessions'])} workspace sessions; refresh {cfg.poll_interval_ms}ms.")
            print("Attention: " + ", ".join(f"{zone.replace('_', ' ')} {count}" for zone, count in zones.items()))
            if result['warnings']: print("Coverage: " + ", ".join(result['warnings']))
        return 0
    except (OSError, ValueError, TypeError):
        # Fixed diagnostics only. No exception messages containing local paths.
        code = "office_not_configured" if 'cfg' in locals() and cfg is None else "source_unavailable"
        error = {"error": {"code": code, "message": "Local office evidence is unavailable. Check private office configuration and Codex / Claude Code session access."}}
        print(json.dumps(error) if args.json else "[Status: Critical] " + error["error"]["message"])
        return 1


if __name__ == "__main__":
    sys.exit(main())
