#!/usr/bin/env python3
# flow: office
"""Private office task board. JSON actions on stdin; no arbitrary commands."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from lib.config import ROOT, load_thresholds
from lib.office.collaboration import Board, Conflict


def configured():
    office = load_thresholds().office
    cfg = office.collaboration if office else None
    if not cfg or not cfg.enabled:
        raise ValueError("collaboration_not_enabled")
    private = ROOT / "data"
    folder = private / "office"
    if not private.is_dir() or not folder.resolve().is_relative_to(private.resolve()):
        raise ValueError("private_storage_unavailable")
    return Board(folder / "collaboration.sqlite3", cfg.lease_seconds), cfg, office


def listeners():
    """Observed loopback listeners; ownership is not attributed to a session."""
    try:
        result = subprocess.run(["lsof", "-nP", "-iTCP", "-sTCP:LISTEN", "-Fpcn"], capture_output=True, text=True, timeout=3)
        rows, pid, command = [], None, None
        for line in result.stdout.splitlines():
            if line.startswith("p"):
                pid = line[1:]
            elif line.startswith("c"):
                command = line[1:]
            elif line.startswith("n") and ("127.0.0.1:" in line or "[::1]:" in line):
                port = line.rsplit(":", 1)[-1]
                if port.isdigit():
                    rows.append({"port": int(port), "pid": pid, "process": command, "session_id": None})
        return {"available": result.returncode == 0, "listeners": rows}
    except (OSError, subprocess.TimeoutExpired):
        return {"available": False, "listeners": []}


def snapshot(board, cfg, office):
    value = board.snapshot()
    # A dead runner is evidence of interruption, not evidence of completed work.
    for task in value["tasks"]:
        if task["managed"] and task["status"] == "running" and task["runner_pid"]:
            board.recover_lost(task["id"], task["runner_pid"])
    return {**board.snapshot(), "poll_interval_ms": office.poll_interval_ms,
            "runtime_available": bool(shutil.which("codex")), "execution_mode": "read-only",
            "max_parallel_teams": cfg.max_parallel_teams, "lease_seconds": cfg.lease_seconds, **listeners()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["snapshot", "apply", "run"], nargs="?", default="snapshot")
    parser.add_argument("task_id", nargs="?")
    args = parser.parse_args()
    try:
        board, cfg, office = configured()
        if args.operation == "snapshot":
            value = snapshot(board, cfg, office)
        elif args.operation == "run":
            from lib.office.team import run_team
            binary = shutil.which("codex")
            if not binary:
                board.update(args.task_id, status="blocked", result="codex_not_found")
            else:
                run_team(board, args.task_id, ROOT, binary, cfg.turn_timeout_seconds, cfg.max_parallel_teams)
            return 0
        else:
            raw = sys.stdin.read(65537)
            if len(raw) > 65536:
                raise ValueError("payload_too_large")
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError("invalid_payload")
            # Public action allowlist; runner methods are never remotely callable.
            if payload.get("action") not in {"create", "claim", "renew", "handoff", "finish", "resource", "release", "team", "cancel"}:
                raise ValueError("unknown_action")
            value = board.apply(payload)
            if payload["action"] == "team" and value["status"] == "queued":
                # Idempotent BEGIN IMMEDIATE in the runner prevents double dispatch.
                try:
                    subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "run", value["id"]],
                                     cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL, start_new_session=True)
                except OSError:
                    board.update(value["id"], status="blocked", result="runner_launch_failed")
                    raise
        print(json.dumps(value, separators=(",", ":")))
        return 0
    except Conflict as error:
        print(json.dumps({"error": {"code": str(error), "status": 409}}))
        return 2
    except (ValueError, TypeError, KeyError, OSError) as error:
        code = str(error) if str(error) in {"collaboration_not_enabled", "unknown_action", "task_not_found", "payload_too_large"} or str(error).startswith("invalid_") else "collaboration_unavailable"
        print(json.dumps({"error": {"code": code, "status": 503 if code in {"collaboration_not_enabled", "collaboration_unavailable"} else 400}}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
