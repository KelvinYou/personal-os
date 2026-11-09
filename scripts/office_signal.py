#!/usr/bin/env python3
# flow: office
"""Claude Code hook: exact office wait signals and optional phone push.

Hook mode (stdin payload): append {session_id, kind, at} to private
data/runtime/ai-office/claude-signals.jsonl, then, when `office.push` is
enabled, hand a push to a detached process so the session never waits on the
network. At SessionStart it also starts scripts/finance_push.py detached
(new Finance attention items). Stores and sends no message text, tool input or path. Always exits 0.

  --test-push   send one test push and print the subscribe URL (loud errors)
  --deferred    internal: the detached push worker

See docs/design/office-attention-radar.md §4.1–4.2.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

APPROVAL_TYPES = {"permission_prompt", "elicitation_dialog", "elicitation_url_dialog"}


def push_cfg():
    """The enabled push block, or None. Imported lazily: SessionStart stays stdlib-only."""
    from lib.config import load_thresholds
    office = load_thresholds().office
    return office.push if office and office.push and office.push.enabled else None


def push_kind(payload: object, cfg) -> str | None:
    """Which push a hook payload asks for, if any."""
    if cfg is None or not isinstance(payload, dict) or payload.get("hook_event_name") != "Notification": return None
    kind = payload.get("notification_type")
    if kind in APPROVAL_TYPES: return "approval"
    if kind == "idle_prompt" and cfg.idle_turns: return "idle"
    return None


def spawn(kind: str, transcript: Path | None) -> None:
    args = [sys.executable, str(Path(__file__).resolve()), "--deferred", kind] + ([str(transcript)] if transcript else [])
    subprocess.Popen(args, start_new_session=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)


def spawn_finance() -> None:
    """Finance attention push (scripts/finance_push.py) builds the wealth report, so it runs detached."""
    subprocess.Popen([sys.executable, str(Path(__file__).resolve().parent / "finance_push.py")], cwd=ROOT, start_new_session=True,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)


def hook(raw: str) -> None:
    from lib.office.signals import record
    payload = json.loads(raw or "null")
    data = ROOT / "data"
    if not data.is_dir(): return  # no private checkout: nothing to record into or configure
    record(payload, data / "runtime" / "ai-office")
    if isinstance(payload, dict) and payload.get("hook_event_name") == "SessionStart" and (data / "finance").is_dir():
        spawn_finance()
        return
    if not isinstance(payload, dict) or payload.get("hook_event_name") != "Notification": return
    cfg = push_cfg()
    kind = push_kind(payload, cfg)
    if kind is None: return
    transcript = None
    if kind == "approval":
        from lib.office.push import transcript_path
        from lib.office.sources import claude_projects
        transcript = transcript_path(payload.get("transcript_path"), claude_projects())
        if transcript is None: return  # cannot tell an answered prompt from an open one
    spawn(kind, transcript)


def deferred(kind: str, transcript: str | None) -> None:
    from lib.office.push import deliver, unanswered_approval
    cfg = push_cfg()
    if cfg is None: return
    if kind == "approval" and (transcript is None or not unanswered_approval(cfg, Path(transcript))): return
    deliver(cfg, kind)


def test_push() -> int:
    from lib.office.push import deliver, subscribe_url
    cfg = push_cfg()
    if cfg is None:
        print("[Status: Warning] office.push is not enabled in data/config/thresholds.yaml.")
        return 1
    try:
        status = deliver(cfg, "test")
    except OSError as error:
        print(f"[Status: Critical] Push failed: {type(error).__name__}. Check network access to {cfg.server}.")
        return 1
    print(f"[Status: OK] Test push sent (HTTP {status}). Subscribe in the ntfy app to: {subscribe_url(cfg)}")
    return 0


def main(argv: list[str]) -> int:
    if argv[:1] == ["--test-push"]: return test_push()
    try:
        if argv[:1] == ["--deferred"]: deferred(argv[1], argv[2] if len(argv) > 2 else None)
        else: hook(sys.stdin.read())
    except Exception:  # noqa: BLE001 — a hook or its worker must never interrupt a session
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
