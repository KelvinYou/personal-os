#!/usr/bin/env python3
"""Validate content records or emit the private browser projection."""
# flow: office
import argparse
import json
from pathlib import Path
import sys

from lib.content_lab import LabCollection, LabItem, LabRecord, read_collection, apply_command, ContentWriteError
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]


def start_pipeline(root: Path) -> None:
    """Queued work starts the autonomous runner at once, only for the owner's real posts and only when enabled."""
    if root.resolve() != (ROOT / "data/posts").resolve():
        return
    try:
        from content_pipeline import config, spawn_detached
        cfg = config()
    except Exception:  # noqa: BLE001 — a missing/invalid config leaves the work queued, never fails the write
        return
    if cfg and cfg.enabled:
        spawn_detached()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT / "data/posts")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        if args.apply:
            if args.demo:
                raise ContentWriteError("demo_read_only", 403)
            raw = sys.stdin.buffer.read(65537)
            if len(raw) > 65536:
                raise ContentWriteError("request_too_large", 413)
            item = apply_command(args.root, json.loads(raw))
            if item.record and item.record.pipeline.status == "queued":
                start_pipeline(args.root)
        if args.demo:
            record = LabRecord.model_validate({"stage": "research", "experiment": {"hypothesis": "An actionable question earns saves", "changed_variable": "Opening question"}})
            collection, errors = LabCollection(items=[LabItem(post_id="sample-2026-01-01", record=record)], partial=False), []
        else:
            collection, errors = read_collection(args.root)
        if args.json:
            print(collection.model_dump_json())
            return 0
        for error in errors:
            print(f"[Status: Critical] {error}")
        if errors:
            return 1
        print(f"[Status: OK] {len(collection.items)} posts checked; legacy records remain unknown")
        return 0
    except (ContentWriteError, ValidationError) as exc:
        code = exc.code if isinstance(exc, ContentWriteError) else "record_invalid"
        status = exc.status if isinstance(exc, ContentWriteError) else 422
        message = exc.errors()[0]["msg"] if isinstance(exc, ValidationError) else code
        print(json.dumps({"error": {"code": code, "status": status, "message": message}}))
        return 1
    except (OSError, ValueError):
        if args.json:
            print(json.dumps({"error": {"code": "content_lab_unavailable"}}))
        else:
            print("[Status: Warning] content_lab_unavailable: private posts root is unavailable")
        return 1


if __name__ == "__main__":
    sys.exit(main())
