"""Content Lab review latency for §4.6 (docs/design/office-world.md "Town attention"). Synthetic records only."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from lib.content_lab import LabRecord, review_waits  # noqa: E402
from lib.office.waits import content_review_markdown, content_review_summary  # noqa: E402

T0 = datetime(2026, 11, 2, 1, tzinfo=timezone.utc)  # Monday 09:00 KL
H = timedelta(hours=1)


def record(stage: str, runs: list[datetime], feedback: list[datetime] = (), reviewed: datetime | None = None, status: str = "idle") -> LabRecord:
    return LabRecord.model_validate({
        "stage": stage,
        "readiness": {"factual": "passed", "visual": "passed", "owner_review": "accepted" if stage in ("ready", "published") else "pending",
                      "reviewed_at": reviewed.isoformat() if reviewed else None},
        "pipeline": {"status": status, "requested_at": T0.isoformat() if status in ("queued", "running") else None,
                     "feedback": [{"at": at.isoformat(), "note": "synthetic"} for at in feedback],
                     "runs": [{"started_at": (at - H).isoformat(), "finished_at": at.isoformat(), "outcome": "succeeded"} for at in runs]},
    })


class ReviewWaitTests(unittest.TestCase):
    def test_each_finished_package_closes_at_the_next_owner_decision(self):
        # Run 1 → change request 2 h later → run 2 → accepted 5 h later.
        waits = review_waits(record("ready", [T0, T0 + 10 * H], feedback=[T0 + 2 * H], reviewed=T0 + 15 * H))
        self.assertEqual([(w["kind"], w["seconds"]) for w in waits], [("closed", 2 * 3600), ("closed", 5 * 3600)])

    def test_still_in_review_is_open_and_legacy_decisions_are_unmeasured(self):
        self.assertEqual([w["kind"] for w in review_waits(record("review", [T0]))], ["open"])
        self.assertEqual([w["kind"] for w in review_waits(record("ready", [T0]))], ["unmeasured"])  # accepted before reviewed_at existed
        self.assertEqual([w["kind"] for w in review_waits(record("archived", [T0]))], ["unmeasured"])
        self.assertEqual(review_waits(record("idea", [])), [])

    def test_week_summary_counts_by_review_arrival_and_open_only_for_the_current_week(self):
        start, end = T0 - H, T0 - H + 7 * 24 * H
        records = [record("ready", [T0], reviewed=T0 + 2 * H), record("ready", [T0 + H], reviewed=T0 + 7 * H),
                   record("review", [T0 + 24 * H]), record("archived", [T0]), record("ready", [start - H], reviewed=T0)]
        s = content_review_summary(records, start, end, now=T0 + 30 * H)
        self.assertEqual((s["reviewed"], s["median_hours"], s["longest_hours"], s["open"], s["oldest_open_hours"], s["unmeasured"]), (2, 4.0, 6.0, 1, 6.0, 1))
        self.assertEqual(content_review_summary(records, start, end, now=end + H)["open"], 0)  # a past week reports no "still waiting"

    def test_markdown_states_unavailable_empty_and_measured_weeks(self):
        self.assertIn("unavailable", content_review_markdown(None)[0])
        empty = {"reviewed": 0, "median_hours": None, "longest_hours": None, "open": 0, "oldest_open_hours": None, "unmeasured": 0}
        self.assertIn("no package reached review", content_review_markdown(empty)[0])
        line = content_review_markdown({**empty, "reviewed": 2, "median_hours": 4.0, "longest_hours": 6.0, "open": 1, "oldest_open_hours": 6.0})[0]
        self.assertEqual(line, "- Content Lab review (package ready → your decision): 2 reviewed, median 4.0 h, longest 6.0 h; 1 still waiting (oldest 6.0 h).")


if __name__ == "__main__":
    unittest.main()
