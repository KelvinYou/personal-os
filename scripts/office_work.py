#!/usr/bin/env python3
# flow: office
"""Local owned-run archive, sharing the canonical office collaboration database."""
import argparse
import json
import os
import sys
from lib.config import ROOT, load_thresholds
from lib.office.collaboration import Board, Conflict


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["list", "record", "review", "get"])
    args = parser.parse_args()
    try:
        office = load_thresholds().office
        if not office or not office.execution or not office.execution.enabled:
            raise ValueError("execution_not_configured")
        private = ROOT / "data"
        folder = private / "office"
        if not private.is_dir() or not folder.resolve().is_relative_to(private.resolve()):
            raise ValueError("private_storage_unavailable")
        folder.mkdir(mode=0o700, exist_ok=True)
        file = folder / "collaboration.sqlite3"
        if file.is_symlink():
            raise ValueError("private_storage_unavailable")
        os.chmod(folder, 0o700)
        board = Board(file, office.collaboration.lease_seconds if office.collaboration else 0)
        if args.operation == "list":
            runs = board.runs(office.execution.max_messages + 1)
            result = {"schema_version": 1, "runs": runs[:office.execution.max_messages], "has_more": len(runs) > office.execution.max_messages}
        else:
            raw = sys.stdin.read(8 * 1024 * 1024 + 1)
            if len(raw) > 8 * 1024 * 1024:
                raise ValueError("payload_too_large")
            payload = json.loads(raw)
            if args.operation == "get":
                result = board.run(payload["task_id"])
            elif args.operation == "record":
                result = board.record_run(payload)
            else:
                if not isinstance(payload, dict) or set(payload) != {"task_id", "revision", "review"}:
                    raise ValueError("invalid_review")
                result = board.review_run(**payload)
        print(json.dumps(result))
        return 0
    except Conflict as error:
        print(json.dumps({"error": {"code": str(error), "status": 409}}))
    except Exception as error:
        code = str(error) if isinstance(error, ValueError) and (str(error).startswith("invalid_") or str(error) in {"execution_not_configured", "task_not_found", "payload_too_large"}) else "history_unavailable"
        print(json.dumps({"error": {"code": code, "status": 400 if code.startswith("invalid_") or code == "task_not_found" else 503}}))
    return 1


if __name__ == "__main__":
    sys.exit(main())
