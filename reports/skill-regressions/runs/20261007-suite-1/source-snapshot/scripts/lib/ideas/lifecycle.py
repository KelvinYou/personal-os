"""User-owned test confirmation and result lifecycle rules."""
from __future__ import annotations

from datetime import datetime

from .models import (
    CostEstimate,
    LedgerState,
    Priority,
    RunStatus,
    TestConfirmation,
    TestResult,
    TestResultState,
)
from .storage import IdeaStore, StorageError


class TestLifecycle:
    """Apply the execution/result state machine before appending an event."""

    def __init__(self, store: IdeaStore) -> None:
        self.store = store

    @staticmethod
    def _find_test(run, test_id: str):
        rows = [*run.ledger.rows, *run.ledger.appendix_rows] if run.ledger else []
        for row in rows:
            if row.test_id == test_id:
                return row
        raise StorageError(f"test {test_id} is not present in run {run.run_id}")

    def confirm(
        self,
        *,
        idea_id: str,
        run_id: str,
        test_id: str,
        confirmed_by: str,
        confirmed_at: datetime,
    ) -> TestConfirmation:
        run = self.store.load_run(idea_id, run_id)
        row = self._find_test(run, test_id)
        if run.run_status is not RunStatus.COMPLETE:
            raise StorageError("only a COMPLETE run can be confirmed for execution")
        if row.priority is Priority.UNPRIORITIZED or row.state is LedgerState.UNPRIORITIZED:
            raise StorageError("cannot confirm an unprioritized or incomplete test contract")
        if not all(
            [
                row.claim_ids or row.gap_ids,
                row.discriminating_test,
                row.criterion,
                row.target_or_sample,
                row.owner,
                row.deadline,
                row.estimated_cost,
                row.impact_if_false is not None
                and row.impact_if_false.value != "UNKNOWN",
            ]
        ):
            raise StorageError("test contract is incomplete; fill every execution field first")
        if self.store.has_confirmation(idea_id, run_id, test_id):
            raise StorageError(f"test {test_id} is already confirmed for {run_id}")
        if row.estimated_cost.user_minutes is None:
            raise StorageError(
                "test contract must include estimated user_minutes before confirmation"
            )

        confirmed_minutes = 0
        for event in self.store.test_events(idea_id):
            if (
                event["event_type"] != "confirmation"
                or event["run_id"] != run.run_id
            ):
                continue
            prior_row = self._find_test(run, event["test_id"])
            if (
                prior_row.estimated_cost is None
                or prior_row.estimated_cost.user_minutes is None
            ):
                raise StorageError(
                    f"confirmed test {prior_row.test_id} has no estimated user_minutes"
                )
            confirmed_minutes += prior_row.estimated_cost.user_minutes

        if (
            confirmed_minutes + row.estimated_cost.user_minutes
            > run.context.run_budget.max_user_minutes
        ):
            raise StorageError(
                "confirming this test exceeds the run's max_user_minutes budget; "
                "increase the declared budget or choose a smaller test"
            )

        confirmation = TestConfirmation(
            test_id=row.test_id,
            run_id=run.run_id,
            confirmed_at=confirmed_at,
            confirmed_by=confirmed_by,
        )
        self.store.append_test_event(
            idea_id,
            {"event_type": "confirmation", **confirmation.model_dump(mode="json")},
        )
        return confirmation

    def record_result(
        self,
        *,
        idea_id: str,
        run_id: str,
        test_id: str,
        state: TestResultState,
        recorded_by: str,
        observation: str,
        result_evidence_refs: list[str],
        recorded_at: datetime,
        actual_cost: CostEstimate | None = None,
    ) -> TestResult:
        run = self.store.load_run(idea_id, run_id)
        self._find_test(run, test_id)
        if not self.store.has_confirmation(idea_id, run_id, test_id):
            raise StorageError("record the user confirmation before recording a result")
        if self.store.has_result(idea_id, run_id, test_id):
            raise StorageError(
                "a result already exists for this test and run; record a changed test in a new run"
            )

        known = {item.evidence_id for item in self.store.load_input(idea_id).evidence}
        missing = sorted(set(result_evidence_refs) - known)
        if missing:
            raise StorageError(
                f"result references unknown evidence: {', '.join(missing)}"
            )

        result = TestResult(
            test_id=test_id,
            run_id=run_id,
            state=state,
            recorded_at=recorded_at,
            recorded_by=recorded_by,
            observation=observation,
            result_evidence_refs=result_evidence_refs,
            actual_cost=actual_cost,
        )
        self.store.append_test_event(
            idea_id,
            {"event_type": "result", **result.model_dump(mode="json")},
        )
        return result
