"""Append-only JSONL event logger for engine observability (D5)."""
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = ROOT / "data" / "logs"


def _json_safe(obj: Any) -> Any:
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if hasattr(obj, "__dict__"):
        return {k: _json_safe(v) for k, v in obj.__dict__.items()}
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(x) for x in obj]
    return obj


def emit_event(event_type: str, payload: dict | None = None) -> None:
    """Append one JSON line to data/logs/engine-YYYY-MM-DD.jsonl.

    Never raises — observability must not break the main pipeline.
    """
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        fname = f"engine-{date.today().isoformat()}.jsonl"
        record = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "event": event_type,
            "payload": _json_safe(payload or {}),
        }
        with (LOG_DIR / fname).open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass
