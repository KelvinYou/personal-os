"""Private financial tasks. Evidence and decisions never post account balances."""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import subprocess
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from .activity import Transaction
from .files import FINANCE_DIR
from .workbench_planning import AllocationInput, AllocationResult, Policy, PolicyAudit, ScenarioInput, ScenarioResult, allocate, audit_policy, compare, fingerprint

LEDGER_PATH = FINANCE_DIR / "workbench.jsonl"
STRICT = ConfigDict(extra="forbid", allow_inf_nan=False, str_strip_whitespace=True, json_schema_serialization_defaults_required=True)
ID = Annotated[str, Field(pattern=r"^[a-zA-Z0-9_-]{1,100}$")]


class Model(BaseModel):
    model_config = STRICT


class Step(Model):
    id: str
    label: str
    status: Literal["planned", "in_transit", "confirmed", "not_applicable"] = "planned"
    amount: float | None = Field(default=None, gt=0)
    currency: Literal["MYR", "USD", "CNY"] | None = None
    occurred_on: date | None = None
    evidence: str = Field(default="", max_length=2000)
    source_event_id: str | None = None

    @model_validator(mode="after")
    def coherent(self):
        if (self.amount is None) != (self.currency is None):
            raise ValueError("Amount and currency must be supplied together")
        if self.status != "planned" and not self.evidence:
            raise ValueError("Evidence or an explicit skip reason is required")
        if self.status in ("confirmed", "in_transit") and self.id != "reconcile" and self.amount is None:
            raise ValueError("Movement evidence requires original-currency amount")
        if self.id == "reconcile" and self.status == "in_transit":
            raise ValueError("Reconciliation is not a money movement")
        return self


class Workflow(Model):
    id: ID
    revision: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=160)
    kind: Literal["flow", "allocation", "scenario"] = "flow"
    status: Literal["open", "completed", "draft", "reviewed"] = "open"
    steps: list[Step] = Field(default_factory=list)
    recorded_at: str
    policy_fingerprint: str | None = None
    inputs: AllocationInput | ScenarioInput | None = None
    result: AllocationResult | ScenarioResult | None = None

    @model_validator(mode="after")
    def coherent(self):
        if self.kind == "flow":
            if {s.id for s in self.steps} != {"redeem", "settle", "fx", "transfer", "purchase", "reconcile"} or len(self.steps) != 6:
                raise ValueError("Funding flow requires six distinct steps")
            status = "completed" if all(s.status in ("confirmed", "not_applicable") for s in self.steps) else "open"
            if self.status != status or self.inputs is not None or self.result is not None:
                raise ValueError("Incoherent funding flow")
        else:
            expected = (AllocationInput, AllocationResult) if self.kind == "allocation" else (ScenarioInput, ScenarioResult)
            if not isinstance(self.inputs, expected[0]) or not isinstance(self.result, expected[1]) or self.steps or self.status not in ("draft", "reviewed"):
                raise ValueError("Incoherent worksheet")
            if self.kind == "allocation" and not self.policy_fingerprint:
                raise ValueError("Allocation requires source policy fingerprint")
        return self


class CreateFlow(Model):
    action: Literal["create_flow"]
    request_id: ID
    id: ID
    title: str = Field(min_length=1, max_length=160)
    source_event_id: ID | None = None


class UpdateStep(Model):
    action: Literal["update_step"]
    request_id: ID
    id: ID
    expected_revision: int = Field(ge=1, strict=True)
    step_id: Literal["redeem", "settle", "fx", "transfer", "purchase", "reconcile"]
    status: Literal["planned", "in_transit", "confirmed", "not_applicable"]
    amount: float | None = Field(default=None, gt=0, strict=True)
    currency: Literal["MYR", "USD", "CNY"] | None = None
    occurred_on: date | None = None
    evidence: str = Field(min_length=1, max_length=2000)


class SaveAllocation(Model):
    action: Literal["save_allocation"]
    request_id: ID
    id: ID
    title: str = Field(min_length=1, max_length=160)
    inputs: AllocationInput


class SaveScenario(Model):
    action: Literal["save_scenario"]
    request_id: ID
    id: ID
    title: str = Field(min_length=1, max_length=160)
    inputs: ScenarioInput


class Review(Model):
    action: Literal["review"]
    request_id: ID
    id: ID
    expected_revision: int = Field(ge=1, strict=True)


Command = Annotated[CreateFlow | UpdateStep | SaveAllocation | SaveScenario | Review, Field(discriminator="action")]


class WorkbenchSnapshot(Model):
    schema_version: Literal[1] = 1
    as_of: str
    ledger_state: Literal["missing", "present"]
    workflows: list[Workflow]
    policy: PolicyAudit
    purchase_evidence: list[Transaction]


class Event(Model):
    request_id: ID
    digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    workflow: Workflow


class WorkbenchError(ValueError):
    def __init__(self, code: str, status: int = 400):
        super().__init__(code)
        self.code, self.status = code, status


def require_private_finance():
    # Offline working-tree transfers can preserve ignored private data without .git.
    # Accept an existing excluded finance root; never create a missing default root.
    root = FINANCE_DIR.parents[1]
    if not FINANCE_DIR.is_dir() or not (FINANCE_DIR / "savings.yaml").is_file() or not (FINANCE_DIR / "portfolio.yaml").is_file():
        raise WorkbenchError("private_data_required", 503)
    ignored = subprocess.run(["git", "check-ignore", "--quiet", "data/finance/workbench.jsonl"], cwd=root, capture_output=True)
    if ignored.returncode != 0:
        raise WorkbenchError("private_data_required", 503)


def _events(text: str) -> list[Event]:
    result, revisions, ids = [], {}, set()
    try:
        for line in text.splitlines():
            if not line.strip():
                continue
            event = Event.model_validate_json(line)
            w = event.workflow
            if event.request_id in ids or w.revision != revisions.get(w.id, 0) + 1:
                raise ValueError("Invalid revision sequence")
            ids.add(event.request_id)
            revisions[w.id] = w.revision
            result.append(event)
    except ValueError as exc:
        raise WorkbenchError("invalid_workbench_ledger", 503) from exc
    return result


def _latest(events: list[Event]) -> list[Workflow]:
    return list({event.workflow.id: event.workflow for event in events}.values())


def read_workflows(path: Path = LEDGER_PATH) -> list[Workflow]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        fcntl.flock(fh, fcntl.LOCK_SH)
        return _latest(_events(fh.read()))


def _new_flow(command: CreateFlow, transactions: list[Transaction], stamp: str) -> Workflow:
    steps = [Step(id=id, label=label) for id, label in [
        ("redeem", "Fund redemption"), ("settle", "Cash settlement"),
        ("fx", "Currency conversion"), ("transfer", "Broker transfer"),
        ("purchase", "Purchase"), ("reconcile", "Reconcile balances and holdings"),
    ]]
    if command.source_event_id:
        source = next((t for t in transactions if t.id == command.source_event_id and t.kind == "buy"), None)
        if source is None:
            raise WorkbenchError("purchase_evidence_not_found")
        steps[4] = Step(id="purchase", label="Purchase", status="confirmed", amount=source.amount,
                        currency=source.currency, occurred_on=source.occurred_on,
                        evidence="Owner-reported purchase in the transaction journal; funding remains unconfirmed.", source_event_id=source.id)
    return Workflow(id=command.id, revision=1, title=command.title, recorded_at=stamp, steps=steps)


def apply_command(raw: dict, *, path: Path = LEDGER_PATH, transactions: list[Transaction], policy: dict | None = None, now: datetime | None = None) -> Workflow:
    command = TypeAdapter(Command).validate_python(raw)
    digest = hashlib.sha256(command.model_dump_json().encode()).hexdigest()
    if path == LEDGER_PATH:
        require_private_finance()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        fh.seek(0)
        text = fh.read()
        events = _events(text)
        for event in events:
            if event.request_id == command.request_id:
                if event.digest != digest:
                    raise WorkbenchError("request_id_conflict", 409)
                return event.workflow
        current = next((w for w in _latest(events) if w.id == command.id), None)
        stamp = now or datetime.now(timezone.utc)
        if isinstance(command, (CreateFlow, SaveAllocation, SaveScenario)):
            if current:
                raise WorkbenchError("workflow_already_exists", 409)
            if isinstance(command, CreateFlow):
                workflow = _new_flow(command, transactions, stamp.isoformat())
            else:
                if command.inputs.as_of > stamp.date():
                    raise WorkbenchError("future_assumption_date")
                if isinstance(command, SaveAllocation):
                    if policy is None:
                        raise WorkbenchError("policy_unavailable")
                    p = Policy.model_validate(policy)
                    result, source = allocate(command.inputs, p), fingerprint(p)
                else:
                    result, source = compare(command.inputs), None
                workflow = Workflow(id=command.id, revision=1, title=command.title, kind="allocation" if isinstance(command, SaveAllocation) else "scenario", status="draft", recorded_at=stamp.isoformat(), policy_fingerprint=source, inputs=command.inputs, result=result)
        else:
            if current is None:
                raise WorkbenchError("workflow_not_found", 404)
            if current.revision != command.expected_revision:
                raise WorkbenchError("revision_conflict", 409)
            workflow = current.model_copy(deep=True)
            if isinstance(command, Review):
                if current.kind == "flow":
                    raise WorkbenchError("review_requires_a_worksheet")
                if current.kind == "allocation" and (policy is None or fingerprint(Policy.model_validate(policy)) != current.policy_fingerprint):
                    raise WorkbenchError("policy_changed", 409)
                workflow.status = "reviewed"
            else:
                if current.kind != "flow":
                    raise WorkbenchError("not_a_funding_flow")
                if command.occurred_on and command.occurred_on > stamp.date():
                    raise WorkbenchError("future_execution_date")
                updated = Step(id=command.step_id, label=next(s.label for s in current.steps if s.id == command.step_id),
                               status=command.status, amount=command.amount, currency=command.currency,
                               occurred_on=command.occurred_on, evidence=command.evidence)
                workflow.steps = [updated if s.id == updated.id else s for s in workflow.steps]
                workflow.status = "completed" if all(s.status in ("confirmed", "not_applicable") for s in workflow.steps) else "open"
            workflow.revision += 1
            workflow.recorded_at = stamp.isoformat()
        workflow = Workflow.model_validate(workflow.model_dump())
        event = Event(request_id=command.request_id, digest=digest, workflow=workflow)
        fh.seek(0, os.SEEK_END)
        fh.write(("\n" if text and not text.endswith("\n") else "") + event.model_dump_json() + "\n")
        fh.flush()
        os.fsync(fh.fileno())
        return workflow
