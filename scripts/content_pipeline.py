#!/usr/bin/env python3
"""Run queued Content Lab packages through a headless Claude Code agent, one at a time."""
# flow: office
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.content_pipeline import run_queue  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
POSTS = ROOT / "data/posts"
LOGS = ROOT / "data/runtime/content-pipeline"


def allowed_tools(post_id: str) -> list[str]:
    """Everything else is denied without asking (dontAsk); writes stay inside the one post folder."""
    folder = f"data/posts/{post_id}"
    return ["Read", "Glob", "Grep", "WebSearch", "WebFetch", "Skill",
            f"Edit({folder}/**)", f"Write({folder}/**)",
            f"Bash(codex exec -s workspace-write -C {folder}:*)", "Bash(printf:*)", "Bash(sips:*)", "Bash(mkdir:*)", "Bash(ls:*)",
            "Bash(cp:*)", "Bash(mv:*)", "Bash(make posts-check)", "Bash(file:*)",
            # Exact chart pages for research posts; post_chart.py refuses an OUT outside this folder.
            f"Bash(make post-chart SPEC={folder}/:*)"]


def config():
    from lib.config import load_thresholds
    office = load_thresholds().office
    return office.content_pipeline if office and office.content_pipeline else None


def claude_agent(cfg):
    def agent(post_id: str, prompt: str, log: Path) -> tuple[bool, str]:
        # Project settings only: the owner's local settings carry blanket Bash/Write/Edit allows that
        # would override this run's allowlist (smoke test 2026-11-09 wrote outside the post folder).
        cmd = ["claude", "-p", prompt, "--setting-sources", "project", "--permission-mode", "dontAsk", "--output-format", "json",
               "--allowedTools", *allowed_tools(post_id)]
        if cfg.model:
            cmd += ["--model", cfg.model]
        if cfg.max_budget_usd:
            cmd += ["--max-budget-usd", str(cfg.max_budget_usd)]
        with open(log, "w", encoding="utf-8") as out:
            try:
                done = subprocess.run(cmd, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=out,
                                      text=True, timeout=cfg.timeout_seconds)
            except subprocess.TimeoutExpired:
                return False, f"timed out after {cfg.timeout_seconds} s"
            out.write(done.stdout)
        try:
            result = json.loads(done.stdout)
            return done.returncode == 0 and not result.get("is_error"), str(result.get("result", ""))[-1500:]
        except (json.JSONDecodeError, AttributeError):
            return False, f"exit {done.returncode}; see log {log.name}"
    return agent


def push(kind: str) -> None:
    from lib.config import load_thresholds
    from lib.office.push import deliver
    office = load_thresholds().office
    if office and office.push and office.push.enabled:
        deliver(office.push, kind)


def spawn_detached() -> None:
    """Start a runner without waiting; a second runner exits at once on the lock."""
    subprocess.Popen([sys.executable, str(Path(__file__).resolve())], cwd=ROOT, start_new_session=True,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()
    cfg = config()
    if cfg is None or not cfg.enabled:
        print("[Status: Warning] office.content_pipeline is not enabled in data/config/thresholds.yaml.")
        return 1
    os.environ.pop("CLAUDECODE", None)  # a nested launch must not inherit the parent session's marker
    done = run_queue(POSTS, LOGS, claude_agent(cfg), push=push)
    if done is None:
        print("[Status: OK] Another content run is active; it will drain the queue.")
    else:
        print(f"[Status: OK] {len(done)} package(s) processed: {', '.join(done) or 'queue empty'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
