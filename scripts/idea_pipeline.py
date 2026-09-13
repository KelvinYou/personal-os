#!/usr/bin/env python3
# flow: ideas
"""CLI for the private startup-idea evaluation lifecycle."""
from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from lib.ideas.model_client import (  # noqa: E402
    ClaudeAgentSDKClient,
    DemoModelClient,
    ScriptedModelClient,
)
from lib.ideas.canonical import sha256_hex  # noqa: E402
from lib.ideas.config import load_idea_config  # noqa: E402
from lib.ideas.models import (  # noqa: E402
    CostEstimate,
    EvaluationInput,
    EvidenceItem,
    TestResultState,
)
from lib.ideas.lifecycle import TestLifecycle  # noqa: E402
from lib.ideas.orchestrator import IdeaPipeline  # noqa: E402
from lib.ideas.storage import IdeaStore, StorageError  # noqa: E402
from lib.ideas.validate import ContextValidationError, validate_context  # noqa: E402


DEFAULT_IDEAS_ROOT = PROJECT_ROOT / "data" / "ideas"


def _load_yaml(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise StorageError(f"cannot read {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise StorageError(f"invalid YAML in {path}: {exc}") from exc


def _load_input(path: Path) -> EvaluationInput:
    value = _load_yaml(path)
    if isinstance(value, dict) and "input" in value:
        value = value["input"]
    try:
        return EvaluationInput.model_validate(value)
    except (ValidationError, TypeError) as exc:
        raise ContextValidationError(f"invalid evaluation input: {exc}") from exc


def _parse_now(value: str | None) -> datetime | None:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ContextValidationError(f"invalid evaluated-at timestamp: {value}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ContextValidationError("evaluated-at must include a timezone")
    return parsed


def _store(args: argparse.Namespace) -> IdeaStore:
    if args.output_dir:
        configured = Path(args.output_dir)
        private_data = (PROJECT_ROOT / "data").resolve()
        try:
            configured.resolve().relative_to(private_data)
        except ValueError:
            return IdeaStore(configured)
        if not (private_data / ".git").exists():
            raise StorageError(
                "output directory is inside the private data submodule, but the "
                "submodule is not checked out; run make setup-private"
            )
        return IdeaStore(configured)
    private_data = PROJECT_ROOT / "data"
    if not (private_data / ".git").exists():
        raise StorageError(
            "private data submodule is not checked out; run make setup-private "
            "or pass --output-dir to an explicitly private working directory"
        )
    return IdeaStore(DEFAULT_IDEAS_ROOT)


def _client(args: argparse.Namespace):
    if args.engine == "demo":
        return DemoModelClient(model=args.model)
    if args.engine == "claude":
        return ClaudeAgentSDKClient(model=args.model)
    if not args.response:
        raise ContextValidationError("--response is required for the scripted engine")
    value = _load_yaml(Path(args.response))
    if isinstance(value, dict) and "responses" in value:
        value = value["responses"]
    if not isinstance(value, dict):
        raise ContextValidationError("scripted response file must contain a mapping")
    return ScriptedModelClient(value, model="scripted")


def _ensure_input(store: IdeaStore, input_: EvaluationInput) -> EvaluationInput:
    idea_dir = Path(store.root) / input_.idea_id
    if (idea_dir / "brief.md").exists() or (idea_dir / "evidence.yaml").exists():
        stored = store.load_input(input_.idea_id)
        if sha256_hex(stored) != sha256_hex(input_):
            raise StorageError(
                f"idea {input_.idea_id} already exists with different input; "
                "edit the private brief or use add-evidence before evaluating"
            )
        return stored
    store.save_input(input_)
    return input_


def _evaluate(args: argparse.Namespace) -> int:
    input_ = _load_input(Path(args.input))
    store = _store(args)
    config = load_idea_config(Path(args.config) if args.config else None)
    client = _client(args)
    input_ = _ensure_input(store, input_)
    artifact = asyncio.run(
        IdeaPipeline(
            client,
            mode=args.mode,
            store=store,
            lens_checklists=config.lens_checklists,
            now=_parse_now(args.evaluated_at),
            max_top_rows=(
                args.max_top_rows
                if args.max_top_rows is not None
                else config.max_top_rows
            ),
            config_schema_version=config.schema_version,
        ).run(input_)
    )
    path = store.root / artifact.idea_id / "runs" / f"{artifact.run_id}.md"
    label = "OK" if artifact.run_status.value == "COMPLETE" else "Warning"
    print(f"[Status: {label}] {artifact.run_status.value} — {path}")
    print(f"  run_id: {artifact.run_id}")
    print(f"  input_snapshot_id: {artifact.input_snapshot_id}")
    return 0 if artifact.run_status.value == "COMPLETE" else 2


def _validate(args: argparse.Namespace) -> int:
    input_ = _load_input(Path(args.input))
    context = validate_context(input_, now=_parse_now(args.evaluated_at))
    print("[Status: OK] context accepted")
    print(f"  run_id: {context.run_id}")
    print(f"  input_snapshot_id: {context.input_snapshot_id}")
    return 0


def _init(args: argparse.Namespace) -> int:
    if not args.input:
        raise ContextValidationError("--input is required when creating an idea record")
    input_ = _load_input(Path(args.input))
    validate_context(input_)
    path = _store(args).save_input(input_)
    print(f"[Status: OK] created private idea record: {path}")
    return 0


def _confirm_test(args: argparse.Namespace) -> int:
    store = _store(args)
    now = _parse_now(args.confirmed_at) or datetime.now(timezone.utc)
    confirmation = TestLifecycle(store).confirm(
        idea_id=args.idea_id,
        run_id=args.run_id,
        test_id=args.test_id,
        confirmed_by=args.confirmed_by,
        confirmed_at=now,
    )
    print(f"[Status: OK] confirmed {confirmation.test_id} for execution")
    return 0


def _record_result(args: argparse.Namespace) -> int:
    store = _store(args)
    refs = args.result_evidence or []
    now = _parse_now(args.recorded_at) or datetime.now(timezone.utc)
    actual_cost = None
    if args.actual_cost is not None:
        if not args.actual_currency:
            raise ContextValidationError(
                "--actual-currency is required with --actual-cost"
            )
        try:
            actual_amount = Decimal(args.actual_cost)
        except (InvalidOperation, ValueError) as exc:
            raise ContextValidationError("--actual-cost must be a decimal amount") from exc
        actual_cost = CostEstimate(
            amount=actual_amount,
            currency=args.actual_currency,
            user_minutes=args.actual_user_minutes,
        )
    elif args.actual_currency or args.actual_user_minutes is not None:
        raise ContextValidationError(
            "--actual-cost is required with --actual-currency/--actual-user-minutes"
        )
    result = TestLifecycle(store).record_result(
        idea_id=args.idea_id,
        run_id=args.run_id,
        test_id=args.test_id,
        state=TestResultState(args.state),
        recorded_by=args.recorded_by,
        observation=args.observation,
        result_evidence_refs=refs,
        recorded_at=now,
        actual_cost=actual_cost,
    )
    print(f"[Status: OK] recorded {result.state.value} for {args.test_id}")
    return 0


def _add_evidence(args: argparse.Namespace) -> int:
    value = _load_yaml(Path(args.input))
    if isinstance(value, dict) and "evidence" in value:
        value = value["evidence"]
    if not isinstance(value, list):
        raise ContextValidationError("evidence input must be a list")
    items = [EvidenceItem.model_validate(item).model_dump(mode="json") for item in value]
    store = _store(args)
    store.append_evidence(args.idea_id, items)
    print(f"[Status: OK] appended {len(items)} evidence item(s)")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Private startup-idea evaluation pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    def common(command):
        command.add_argument("--output-dir", default=None, help="private idea root (default: data/ideas)")

    validate = sub.add_parser("validate", help="validate an input YAML without model calls")
    validate.add_argument("--input", required=True)
    validate.add_argument("--evaluated-at", default=None)

    init = sub.add_parser("init", help="create a private idea record from input YAML")
    init.add_argument("--input", required=True)
    common(init)

    evaluate = sub.add_parser("evaluate", help="run an evaluation")
    evaluate.add_argument("--input", required=True)
    evaluate.add_argument("--mode", choices=("single", "multi"), default="single")
    evaluate.add_argument("--engine", choices=("demo", "scripted", "claude"), default="demo")
    evaluate.add_argument("--response", default=None, help="scripted response YAML")
    evaluate.add_argument("--model", default="sonnet")
    evaluate.add_argument("--evaluated-at", default=None)
    evaluate.add_argument("--max-top-rows", type=int, default=None)
    evaluate.add_argument("--config", default=None)
    common(evaluate)

    confirm = sub.add_parser("confirm-test", help="append a user confirmation event")
    confirm.add_argument("--idea-id", required=True)
    confirm.add_argument("--run-id", required=True)
    confirm.add_argument("--test-id", required=True)
    confirm.add_argument("--confirmed-by", required=True)
    confirm.add_argument("--confirmed-at", default=None)
    common(confirm)

    record = sub.add_parser("record-result", help="append a user test result")
    record.add_argument("--idea-id", required=True)
    record.add_argument("--run-id", required=True)
    record.add_argument("--test-id", required=True)
    record.add_argument("--state", choices=[state.value for state in TestResultState], required=True)
    record.add_argument("--recorded-by", required=True)
    record.add_argument("--observation", required=True)
    record.add_argument("--result-evidence", action="append", default=[])
    record.add_argument("--recorded-at", default=None)
    record.add_argument("--actual-cost", default=None)
    record.add_argument("--actual-currency", default=None)
    record.add_argument("--actual-user-minutes", type=int, default=None)
    common(record)

    evidence = sub.add_parser("add-evidence", help="append validated evidence items")
    evidence.add_argument("--idea-id", required=True)
    evidence.add_argument("--input", required=True)
    common(evidence)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "validate":
            return _validate(args)
        if args.command == "init":
            return _init(args)
        if args.command == "evaluate":
            return _evaluate(args)
        if args.command == "confirm-test":
            return _confirm_test(args)
        if args.command == "record-result":
            return _record_result(args)
        if args.command == "add-evidence":
            return _add_evidence(args)
    except (ContextValidationError, StorageError, ValidationError, ValueError) as exc:
        print(f"[Status: Critical] {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
