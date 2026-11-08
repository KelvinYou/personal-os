"""Owned task evidence survives restarts without changing manual task ownership."""
import tempfile
import unittest
from pathlib import Path
from scripts.lib.office.collaboration import Board, Conflict


def run_record(status="idle"):
    return {"schema_version": 1, "task": {"id": "run-1", "instruction": "Review fixture", "status": "completed" if status == "idle" else "running", "skill_id": "contract-guardian", "collaboration": "solo", "started_at": "2026-11-03T00:00:00Z"}, "status": status, "result": "Checked fixture" if status == "idle" else "", "agents": [], "artifacts": [], "updated_at": "2026-11-03T00:01:00Z", "error": None}


class OfficeWorkTests(unittest.TestCase):
    def test_result_survives_reopen_and_requires_human_acceptance(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "office.sqlite3"
            board = Board(file, 60)
            board.record_run(run_record())
            reopened = Board(file, 60)
            record = reopened.runs()[0]
            self.assertEqual(record["result"], "Checked fixture")
            self.assertEqual(record["review"], "pending")
            reopened.review_run("run-1", record["revision"], "accepted")
            self.assertEqual(Board(file, 60).runs()[0]["review"], "accepted")
            self.assertEqual(board.snapshot()["tasks"], [])

    def test_stale_reviews_cannot_overwrite_acceptance_and_checkpoints_cannot_erase_it(self):
        with tempfile.TemporaryDirectory() as folder:
            board = Board(Path(folder) / "office.sqlite3", 60)
            saved = board.record_run(run_record())
            board.review_run("run-1", saved["revision"], "accepted")
            with self.assertRaises(Conflict):
                board.review_run("run-1", saved["revision"], "rework")
            board.record_run(run_record())
            self.assertEqual(board.runs()[0]["review"], "accepted")

    def test_running_and_incomplete_results_cannot_be_accepted(self):
        with tempfile.TemporaryDirectory() as folder:
            board = Board(Path(folder) / "office.sqlite3", 60)
            saved = board.record_run(run_record("working"))
            with self.assertRaisesRegex(Conflict, "run_not_finished"):
                board.review_run("run-1", saved["revision"], "accepted")
            record = run_record()
            record["task"]["status"] = "incomplete"
            saved = board.record_run(record)
            with self.assertRaisesRegex(Conflict, "result_incomplete"):
                board.review_run("run-1", saved["revision"], "accepted")
            board.review_run("run-1", saved["revision"], "rework")
            with self.assertRaises(Conflict):
                board.record_run(run_record("working"))

    def test_raw_messages_and_invalid_evidence_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            board = Board(Path(folder) / "office.sqlite3", 60)
            record = run_record()
            record["messages"] = [{"text": "SECRET"}]
            with self.assertRaises(ValueError):
                board.record_run(record)
            self.assertEqual(board.runs(), [])

    def test_cli_boundary_reopens_private_store_and_obeys_response_budget(self):
        import io
        import json
        import sys
        from types import SimpleNamespace
        from unittest.mock import patch
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
        import office_work
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "data").mkdir()
            config = SimpleNamespace(office=SimpleNamespace(execution=SimpleNamespace(enabled=True, max_messages=1), collaboration=None))
            def invoke(operation, payload=None):
                output = io.StringIO()
                with patch.object(office_work, "ROOT", root), patch.object(office_work, "load_thresholds", return_value=config), patch.object(sys, "argv", ["office_work.py", operation]), patch.object(sys, "stdin", io.StringIO(json.dumps(payload))), patch.object(sys, "stdout", output):
                    code = office_work.main()
                return code, json.loads(output.getvalue())
            self.assertEqual(invoke("record", run_record())[0], 0)
            code, history = invoke("list")
            self.assertEqual(code, 0)
            self.assertEqual(history["runs"][0]["result"], "Checked fixture")
            self.assertFalse(history["has_more"])
            second = run_record()
            second["task"]["id"] = "run-2"
            self.assertEqual(invoke("record", second)[0], 0)
            self.assertTrue(invoke("list")[1]["has_more"])
            self.assertEqual(invoke("get", {"task_id": "run-1"})[1]["task"]["id"], "run-1")
            self.assertEqual(invoke("review", {"task_id": "run-1", "revision": 0, "review": "accepted"})[0], 0)
            self.assertEqual(invoke("review", {"task_id": "run-1", "revision": 0, "review": "rework"})[1]["error"]["status"], 409)
            self.assertEqual((root / "data/office/collaboration.sqlite3").stat().st_mode & 0o777, 0o600)
            self.assertEqual((root / "data/office").stat().st_mode & 0o777, 0o700)
