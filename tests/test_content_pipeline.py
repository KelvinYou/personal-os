"""Autonomous content pipeline: idea approval → headless run → runner-owned gate → owner review."""
import struct
import tempfile
import unittest
import zlib
from datetime import datetime, timezone
from pathlib import Path

import yaml

from scripts.lib.content_lab import ContentWriteError, LabRecord, apply_command, read_item

NOW = datetime(2026, 1, 2, tzinfo=timezone.utc)


def png(width: int, height: int) -> bytes:
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + ihdr + struct.pack(">I", zlib.crc32(b"IHDR" + ihdr))


def idea(root: Path, name: str = "sample-2026-01-01", **record) -> Path:
    post = root / name
    post.mkdir()
    (post / "post.md").write_text("# Idea\nReader moment: synthetic.\n")
    (post / "lab.yaml").write_text(yaml.safe_dump({"stage": "idea", **record}))
    return post


def complete_package(post: Path, pages: int = 6, size=(1200, 1600)) -> None:
    (post / "images").mkdir(exist_ok=True)
    for n in range(1, pages + 1):
        (post / "images" / f"{n:02d}-page.png").write_bytes(png(*size))
    for name in ["publish.txt", "verification.md", "prompts.md"]:
        (post / name).write_text("synthetic\n")
    record = yaml.safe_load((post / "lab.yaml").read_text())
    record["experiment"] = {"hypothesis": "h", "changed_variable": "v",
                            "gate": [{"question": q, "result": "pass", "note": ""} for q in range(1, 6)],
                            "demand_evidence": [{"reference": "https://example.com", "observed_at": "2026-01-02T00:00:00Z", "observation": "synthetic"}]}
    record["readiness"] = {**record.get("readiness", {}), "factual": "passed", "visual": "passed"}
    record["stage"] = "ready"  # the agent cannot promote itself; the runner decides
    (post / "lab.yaml").write_text(yaml.safe_dump(record))


class CommandTests(unittest.TestCase):
    def cmd(self, root, post, action, **extra):
        return apply_command(root, {"action": action, "post_id": post.name, "expected_revision": read_item(post, root).revision, **extra}, now=NOW)

    def test_approve_idea_queues_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); post = idea(root)
            item = self.cmd(root, post, "approve_idea")
            self.assertEqual((item.record.stage, item.record.pipeline.status), ("research", "queued"))
            self.assertEqual(self.cmd(root, post, "approve_idea"), item)

    def test_change_request_with_note_requeues_and_resets_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); post = idea(root, stage="review", readiness={"factual": "passed", "visual": "passed"})
            item = self.cmd(root, post, "review_content", decision="changes_requested", note="Cover headline too long")
            r = item.record
            self.assertEqual((r.stage, r.pipeline.status, r.readiness.factual, r.readiness.visual), ("production", "queued", "unknown", "unknown"))
            self.assertEqual(r.pipeline.feedback[-1].note, "Cover headline too long")
        self.assertEqual(r.readiness.reviewed_at, NOW)  # review latency evidence

    def test_writes_are_rejected_while_a_run_owns_the_post(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); post = idea(root, stage="research", pipeline={"status": "running", "requested_at": "2026-01-01T00:00:00Z"})
            with self.assertRaises(ContentWriteError) as ctx:
                self.cmd(root, post, "archive")
            self.assertEqual((ctx.exception.code, ctx.exception.status), ("pipeline_running", 409))

    def test_requeue_only_from_failed_and_archive_stops_work(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); post = idea(root)
            with self.assertRaises(ContentWriteError) as ctx:
                self.cmd(root, post, "requeue")
            self.assertEqual(ctx.exception.code, "invalid_transition")
            item = self.cmd(root, post, "archive")
            self.assertEqual((item.record.stage, item.record.pipeline.status), ("archived", "idle"))

    def test_legacy_record_defaults_to_idle_pipeline(self):
        self.assertEqual(LabRecord.model_validate({"stage": "research"}).pipeline.status, "idle")
        with self.assertRaises(ValueError):
            LabRecord.model_validate({"pipeline": {"status": "queued"}})  # queued requires requested_at


class RunnerTests(unittest.TestCase):
    def setUp(self):
        from scripts.lib import content_pipeline
        self.p = content_pipeline
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "posts"; self.root.mkdir()
        self.logs = Path(self.tmp.name) / "logs"
        self.pushes = []

    def tearDown(self):
        self.tmp.cleanup()

    def queue(self, name="sample-2026-01-01", at="2026-01-01T00:00:00Z"):
        return idea(self.root, name, stage="research", pipeline={"status": "queued", "requested_at": at})

    def run_all(self, agent):
        return self.p.run_queue(self.root, self.logs, agent, push=self.pushes.append, now=lambda: NOW)

    def test_complete_package_goes_to_review_never_ready(self):
        post = self.queue()
        prompts = []
        def agent(post_id, prompt, log):
            prompts.append(prompt); complete_package(self.root / post_id); return True, "done"
        self.assertEqual(self.run_all(agent), [post.name])
        r = read_item(post, self.root).record
        self.assertEqual((r.stage, r.pipeline.status, r.readiness.owner_review), ("review", "idle", "pending"))
        self.assertEqual(r.pipeline.runs[-1].outcome, "succeeded")
        self.assertEqual(self.pushes, ["content_review"])
        self.assertIn("AUTONOMOUS", prompts[0])

    def test_runner_keeps_the_owner_review_time_whatever_the_agent_writes(self):
        reviewed = datetime(2025, 12, 31, tzinfo=timezone.utc)
        post = idea(self.root, stage="production", readiness={"owner_review": "changes_requested", "reviewed_at": reviewed.isoformat()},
                    pipeline={"status": "queued", "requested_at": "2026-01-01T00:00:00Z"})
        def agent(post_id, prompt, log):
            complete_package(self.root / post_id)
            record = yaml.safe_load((self.root / post_id / "lab.yaml").read_text())
            record["readiness"]["reviewed_at"] = "2030-01-01T00:00:00Z"  # an agent cannot fake a review time
            (self.root / post_id / "lab.yaml").write_text(yaml.safe_dump(record))
            return True, "done"
        self.run_all(agent)
        r = read_item(post, self.root).record
        self.assertEqual((r.stage, r.readiness.owner_review, r.readiness.reviewed_at), ("review", "pending", reviewed))

    def test_missing_or_wrong_output_fails_with_named_checks(self):
        post = self.queue()
        def agent(post_id, prompt, log):
            complete_package(self.root / post_id, pages=4, size=(1058, 1487)); return True, "done"
        self.run_all(agent)
        r = read_item(post, self.root).record
        self.assertEqual(r.pipeline.status, "failed")
        self.assertIn("images: 4 pages", r.pipeline.runs[-1].reason)
        self.assertIn("3:4", r.pipeline.runs[-1].reason)
        self.assertNotEqual(r.stage, "ready")
        self.assertEqual(self.pushes, ["content_failed"])

    def test_agent_that_breaks_lab_yaml_is_recovered_as_failed(self):
        post = self.queue()
        def agent(post_id, prompt, log):
            (self.root / post_id / "lab.yaml").write_text("stage: [broken\n"); return False, "crashed"
        self.run_all(agent)
        r = read_item(post, self.root).record
        self.assertEqual(r.pipeline.status, "failed")
        self.assertIn("lab.yaml", r.pipeline.runs[-1].reason)

    def test_oldest_first_feedback_reaches_prompt_and_interrupted_runs_fail(self):
        newer = self.queue("newer-2026-01-01", "2026-01-01T05:00:00Z")
        older = self.queue("older-2026-01-01", "2026-01-01T01:00:00Z")
        record = yaml.safe_load((older / "lab.yaml").read_text())
        record["pipeline"]["feedback"] = [{"at": "2026-01-01T00:30:00Z", "note": "Use RM not $"}]
        (older / "lab.yaml").write_text(yaml.safe_dump(record))
        stale = idea(self.root, "stale-2026-01-01", stage="research", pipeline={"status": "running", "requested_at": "2026-01-01T00:00:00Z"})
        order, prompts = [], {}
        def agent(post_id, prompt, log):
            order.append(post_id); prompts[post_id] = prompt; return False, "no output"
        self.run_all(agent)
        self.assertEqual(order, [older.name, newer.name])
        self.assertIn("Use RM not $", prompts[older.name])
        self.assertEqual(read_item(stale, self.root).record.pipeline.status, "failed")

    def test_second_runner_exits_while_first_holds_the_lock(self):
        self.queue()
        with self.p.runner_lock(self.root) as held:
            self.assertTrue(held)
            self.assertEqual(self.run_all(lambda *a: (True, "")), None)


if __name__ == "__main__":
    unittest.main()
