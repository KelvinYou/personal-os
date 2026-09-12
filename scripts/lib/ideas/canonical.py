"""Canonical serialization helpers used for immutable idea-run identities."""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel


def canonical_payload(value: Any) -> Any:
    """Return JSON-compatible data with model semantics preserved."""
    if isinstance(value, BaseModel):
        return canonical_payload(value.model_dump(mode="python", exclude_none=False))
    if isinstance(value, dict):
        return {str(key): canonical_payload(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [canonical_payload(item) for item in value]
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def canonical_json(value: Any) -> str:
    """Serialize a payload deterministically for hashing and comparison."""
    return json.dumps(
        canonical_payload(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_hex(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
