"""Phone push for agent waits through ntfy (docs/design/office-attention-radar.md §4.2).

Fixed text only: no session id, name, path, command or message text leaves the
machine. The topic in private thresholds is the only access control on a public
ntfy server. Stdlib plus optional `truststore`; the caller passes the validated OfficePushCfg.
"""
from __future__ import annotations

from pathlib import Path
import ssl
import time
import urllib.request

# kind -> (title, body, ntfy tags)
MESSAGES = {
    "approval": ("Agent needs your approval", "A Claude Code session may be waiting for your approval.", "raised_hand"),
    "idle": ("Agent is waiting for you", "A Claude Code session finished its turn and is waiting for your reply.", "hourglass"),
    "content_review": ("Content ready for review", "A content package finished its checks and is waiting for your review.", "art"),
    "content_failed": ("Content run needs attention", "A content pipeline run failed its checks. Open Content Lab for the reason.", "warning"),
    "finance_attention": ("Finance needs attention", "A new item entered the Finance attention list. Open Finance for details.", "moneybag"),
    "test": ("Personal-OS push test", "Phone push for agent waits is working.", "white_check_mark"),
}
SETTLE_SECONDS = 2  # let the transcript catch up with the prompt before taking the baseline
TIMEOUT_SECONDS = 10


def subscribe_url(cfg) -> str:
    return f"{cfg.server.rstrip('/')}/{cfg.topic}"


def tls_context() -> ssl.SSLContext:
    """Verify against the OS trust store when truststore is installed.

    Networks that inspect TLS install their root in the OS keychain; Python's
    bundled roots do not include it, so plain urllib fails with "self-signed
    certificate in certificate chain" where curl succeeds.
    """
    try:
        import truststore
        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except ImportError:
        return ssl.create_default_context()


def deliver(cfg, kind: str, opener=urllib.request.urlopen) -> int:
    """POST one fixed message; returns the HTTP status. Raises on network errors."""
    title, body, tags = MESSAGES[kind]
    request = urllib.request.Request(subscribe_url(cfg), data=body.encode(), method="POST",
                                     headers={"Title": title, "Tags": tags, "Priority": "high" if kind == "approval" else "default"})
    with opener(request, timeout=TIMEOUT_SECONDS, context=tls_context()) as response:
        return response.status


def transcript_path(value: object, projects: Path) -> Path | None:
    """The hook's transcript path, accepted only as a regular .jsonl file under the Claude projects folder."""
    if not isinstance(value, str): return None
    path = Path(value)
    try:
        if path.suffix != ".jsonl" or path.is_symlink() or not path.is_file(): return None
        return path if path.resolve().is_relative_to(projects.resolve()) else None
    except OSError:
        return None


def unanswered_approval(cfg, transcript: Path, sleep=time.sleep) -> bool:
    """True when the transcript did not change during the approval delay.

    An answered prompt writes the tool result (or the denial) to the transcript.
    Limit: an approved command still running after the delay has not written
    its result yet, so it also reads as unanswered; the message says "may".
    """
    sleep(SETTLE_SECONDS)
    before = transcript.stat().st_size
    sleep(max(0, cfg.approval_delay_seconds - SETTLE_SECONDS))
    return transcript.stat().st_size == before
