"""Synthetic collaboration workflow; never read the owner's private data."""
import sys
from pathlib import Path
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from lib.office.collaboration import Board, Conflict


class CollaborationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.board = Board(Path(self.tmp.name) / "board.sqlite3", lease_seconds=60)

    def test_two_sessions_cannot_claim_the_same_task(self):
        task = self.board.apply({"action": "create", "request_id": "create-1", "title": "Review fixture"})
        claimed = self.board.apply({"action": "claim", "request_id": "claim-1", "task_id": task["id"], "revision": 0, "session_id": "session-a"})
        self.assertEqual(claimed["status"], "running")
        self.assertEqual(claimed["assignee"], "session-a")
        with self.assertRaises(Conflict):
            self.board.apply({"action": "claim", "request_id": "claim-2", "task_id": task["id"], "revision": 0, "session_id": "session-b"})
        self.assertEqual(self.board.snapshot()["tasks"][0]["assignee"], "session-a")

    def test_handoff_requires_explicit_recipient_and_unblocks_dependency_only_after_finish(self):
        create = {"action": "create", "request_id": "a", "title": "Inspect fixture", "resources": ["path:web/components"]}
        task = self.board.apply(create)
        self.assertEqual(self.board.apply(create), task)
        child = self.board.apply({"action": "create", "request_id": "b", "title": "Review evidence", "depends_on": [task["id"]]})
        def act(action, item, owner, **extra):
            return self.board.apply({"action": action, "request_id": f"{action}-{owner}-{item['revision']}", "task_id": item["id"], "revision": item["revision"], "session_id": owner, **extra})
        with self.assertRaises(Conflict):
            act("claim", child, "reviewer")
        task = act("claim", task, "builder")
        with self.assertRaises(Conflict):
            act("finish", task, "stranger", result="not mine")
        task = act("handoff", task, "builder", result="Spacing inspected; see fixture.", recipient="reviewer")
        self.assertFalse(self.board.snapshot()["resources"])
        with self.assertRaises(Conflict):
            act("claim", task, "stranger")
        task = act("claim", task, "reviewer")
        task = act("finish", task, "reviewer", result="Verified against fixture.")
        self.assertEqual(act("claim", child, "reviewer")["status"], "running")

    def test_overlapping_resource_claims_are_atomic_and_expire(self):
        now = [100.0]
        board = Board(Path(self.tmp.name) / "leases.sqlite3", 60, now=lambda: now[0])
        board.apply({"action": "resource", "request_id": "r1", "session_id": "a", "resource": "path:web"})
        with self.assertRaises(Conflict):
            board.apply({"action": "resource", "request_id": "r2", "session_id": "b", "resource": "build:web/.next"})
        with self.assertRaises(ValueError):
            board.apply({"action": "resource", "request_id": "r3", "session_id": "b", "resource": "path:../private"})
        now[0] += 61
        board.apply({"action": "resource", "request_id": "r4", "session_id": "b", "resource": "build:web/.next"})
        active = [r for r in board.snapshot()["resources"] if r["active"]]
        self.assertEqual([r["owner"] for r in active], ["b"])

    def test_concurrent_claims_and_request_id_collision(self):
        from concurrent.futures import ThreadPoolExecutor
        task = self.board.apply({"action": "create", "request_id": "c1", "title": "One owner"})
        def claim(owner):
            try:
                self.board.apply({"action": "claim", "request_id": owner, "task_id": task["id"], "revision": 0, "session_id": owner})
                return True
            except Conflict:
                return False
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sum(pool.map(claim, ["a", "b"])), 1)
        with self.assertRaises(Conflict):
            self.board.apply({"action": "create", "request_id": "c1", "title": "Different payload"})

    def test_team_runs_two_workers_then_returns_results_to_the_coordinator_once(self):
        from lib.office.team import run_team
        import json
        import threading
        barrier = threading.Barrier(2)
        instances = []
        class Runtime:
            def __init__(self, *args):
                self.role = None
                self.turns = []
                instances.append(self)
            def start(self, root, role):
                self.role = role
                return "thread-" + str(len(instances))
            def turn(self, prompt, schema=None):
                self.turns.append(prompt)
                if schema:
                    return json.dumps({"tasks": [{"title": "Inspect UI", "description": "Read the view"}, {"title": "Inspect API", "description": "Read the route"}]})
                if self.role == "worker":
                    barrier.wait(timeout=5)
                    return "Fixture evidence"
                self.assert_results = "Fixture evidence" in prompt
                return "Both fixture checks agree."
            def close(self):
                pass
        team = self.board.apply({"action": "team", "request_id": "team1", "title": "Read-only review"})
        run_team(self.board, team["id"], Path(self.tmp.name), "unused", 10, 1, factory=Runtime)
        tasks = self.board.snapshot()["tasks"]
        self.assertEqual(len(tasks), 3)
        self.assertTrue(all(t["status"] == "done" for t in tasks))
        self.assertEqual(sum(t["parent_id"] == team["id"] for t in tasks), 2)
        self.assertEqual(len(instances[0].turns), 2)
        self.assertTrue(instances[0].assert_results)
        run_team(self.board, team["id"], Path(self.tmp.name), "unused", 10, 1, factory=Runtime)
        self.assertEqual(len(instances), 3)

    def test_task_owner_can_renew_bound_resources_without_reclaiming_task(self):
        task = self.board.apply({"action": "create", "request_id": "renew-create", "title": "Long task", "resources": ["path:web/example"]})
        task = self.board.apply({"action": "claim", "request_id": "renew-claim", "task_id": task["id"], "revision": 0, "session_id": "a"})
        renewed = self.board.apply({"action": "renew", "request_id": "renew", "task_id": task["id"], "revision": task["revision"], "session_id": "a"})
        self.assertEqual(renewed["status"], "running")
        self.assertGreater(renewed["revision"], task["revision"])

    def test_recovery_cannot_overwrite_a_completed_result(self):
        task = self.board.apply({"action": "team", "request_id": "recover", "title": "Recovery check"})
        self.board.begin_team(task["id"], 99999999, 1)
        self.board.update(task["id"], status="done", result="Verified result")
        self.board.recover_lost(task["id"], 99999999)
        self.assertEqual(self.board.task(task["id"])["result"], "Verified result")

    def test_cancelled_runner_holds_capacity_until_cleanup_finishes(self):
        import os
        team = self.board.apply({"action": "team", "request_id": "cap1", "title": "Active team"})
        self.board.begin_team(team["id"], os.getpid(), 1)
        team = self.board.task(team["id"])
        self.board.apply({"action": "cancel", "request_id": "cap2", "task_id": team["id"], "revision": team["revision"], "session_id": "operator"})
        replacement = self.board.apply({"action": "team", "request_id": "cap3", "title": "Replacement"})
        with self.assertRaises(Conflict):
            self.board.begin_team(replacement["id"], os.getpid(), 1)
        self.board.end_team(team["id"])
        self.assertTrue(self.board.begin_team(replacement["id"], os.getpid(), 1))

    def test_managed_teams_reject_manual_dependencies_and_resource_claims(self):
        task = self.board.apply({"action": "create", "request_id": "manual", "title": "Prerequisite"})
        for extra in [{"depends_on": [task["id"]]}, {"resources": ["port:3000"]}]:
            with self.assertRaises(ValueError):
                self.board.apply({"action": "team", "request_id": str(extra), "title": "Managed", **extra})

    def test_invalid_second_plan_item_leaves_no_orphan_child(self):
        import json
        from lib.office.team import run_team
        class Runtime:
            def __init__(self, *args): pass
            def start(self, *args): return "fixture-thread"
            def turn(self, *args):
                return json.dumps({"tasks": [{"title": "Valid", "description": "Read fixture"}, {"title": "", "description": "Invalid"}]})
            def close(self): pass
        team = self.board.apply({"action": "team", "request_id": "invalid-plan", "title": "Plan check"})
        run_team(self.board, team["id"], Path(self.tmp.name), "unused", 10, 1, factory=Runtime)
        tasks = self.board.snapshot()["tasks"]
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["status"], "blocked")
        self.assertIsNone(tasks[0]["runner_pid"])

    def test_parent_cancellation_atomically_cancels_children_and_late_results_lose(self):
        import os
        team = self.board.apply({"action": "team", "request_id": "parent", "title": "Parent"})
        self.board.begin_team(team["id"], os.getpid(), 1)
        child = self.board.child(team["id"], "Child", "Read fixture")
        team = self.board.task(team["id"])
        self.board.apply({"action": "cancel", "request_id": "cancel-parent", "task_id": team["id"], "revision": team["revision"], "session_id": "operator"})
        self.board.update(child["id"], status="done", result="Late result")
        self.assertEqual(self.board.task(child["id"])["status"], "cancelled")
        self.assertEqual(self.board.task(team["id"])["status"], "cancelled")


if __name__ == "__main__":
    unittest.main()
