#!/usr/bin/env python3
# flow: wealth
"""Read or update private financial task evidence; never execute financial actions.

Default: read snapshot. `apply` reads one command from stdin. --demo replays a
bounded session-local command history in a temporary directory using synthetic facts.
--finance-dir is an explicit offline/test root; the web bridge never accepts a path.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.clock import now_kl
from lib.wealth.activity import Transaction, read_transactions
from lib.wealth.files import FINANCE_DIR
from lib.wealth.workbench import WorkbenchError, WorkbenchSnapshot, apply_command, read_workflows, require_private_finance
from lib.wealth.workbench_planning import audit_policy

ROOT = Path(__file__).resolve().parents[1]


def transactions(directory: Path):
    try:
        return read_transactions(directory / "transactions.jsonl")
    except (ValueError, OSError) as exc:
        raise WorkbenchError("source_evidence_unavailable", 503) from exc


def snapshot(directory: Path, stamp: datetime) -> WorkbenchSnapshot:
    path = directory / "workbench.jsonl"
    return WorkbenchSnapshot(as_of=stamp.date().isoformat(), ledger_state="present" if path.exists() else "missing", workflows=read_workflows(path), policy=audit_policy(directory / "policy.yaml"), purchase_evidence=[t for t in transactions(directory) if t.kind == "buy"])


def operate(directory: Path, stamp: datetime, command: dict | None):
    if command:
        policy = audit_policy(directory / "policy.yaml")
        apply_command(command, path=directory / "workbench.jsonl", transactions=transactions(directory), policy=policy.policy.model_dump() if policy.policy else None, now=stamp)
    return snapshot(directory, stamp)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", nargs="?", choices=["read", "apply"], default="read")
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--finance-dir", type=Path)
    args = parser.parse_args()
    try:
        payload = json.load(sys.stdin) if args.operation == "apply" else None
        if args.demo:
            seed = json.loads((ROOT / "tests/fixtures/finance_workbench.json").read_text())
            stamp = datetime.now(timezone.utc)
            history = payload.get("history", []) if payload else []
            if not isinstance(history, list) or len(history) > 30 or (payload and set(payload) - {"command", "history"}):
                raise WorkbenchError("invalid_demo_history")
            with tempfile.TemporaryDirectory() as tmp:
                directory = Path(tmp)
                (directory / "policy.yaml").write_text(json.dumps(seed["policy"]))
                (directory / "transactions.jsonl").write_text("\n".join(Transaction.model_validate(t).model_dump_json() for t in seed["transactions"]) + "\n")
                for command in seed["commands"] + history:
                    operate(directory, stamp, command)
                result = operate(directory, stamp, payload.get("command") if payload else None)
        else:
            directory = args.finance_dir.resolve() if args.finance_dir else FINANCE_DIR
            if not args.finance_dir:
                require_private_finance()
            result = operate(directory, now_kl(), payload)
        print(result.model_dump_json())
        return 0
    except WorkbenchError as exc:
        print(json.dumps({"error": {"code": exc.code, "status": exc.status}}))
    except OSError:
        print(json.dumps({"error": {"code": "workbench_unavailable", "status": 503}}))
    except (ValueError, KeyError, TypeError):
        print(json.dumps({"error": {"code": "invalid_or_unavailable_workbench", "status": 400}}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
