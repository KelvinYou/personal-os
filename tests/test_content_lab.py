"""Content readiness through the same validator used by the CLI and web projection."""
import tempfile
import unittest
import subprocess
import sys
import yaml
from pathlib import Path

from scripts.lib.content_lab import LabRecord, read_collection, validate_post


class ContentLabTests(unittest.TestCase):
    def test_review_does_not_claim_unchecked_facts_are_ready_and_stale_edits_do_not_win(self):
        from scripts.lib.content_lab import apply_command, ContentWriteError
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            post = root / "sample-2026-01-01"
            post.mkdir()
            (post / "post.md").write_text("# Synthetic\n")
            reviewed = apply_command(root, {"action": "review_content", "post_id": post.name, "expected_revision": None, "decision": "accepted"})
            self.assertEqual(reviewed.record.readiness.owner_review, "accepted")
            self.assertEqual(reviewed.record.stage, "review")
            # A client changes the source after the browser loaded its revision.
            record = reviewed.record.model_dump(mode="json")
            record["experiment"]["hypothesis"] = "A new client edit"
            (post / "lab.yaml").write_text(yaml.safe_dump(record))
            with self.assertRaises(ContentWriteError) as context:
                apply_command(root, {"action": "review_content", "post_id": post.name, "expected_revision": reviewed.revision, "decision": "changes_requested"})
            self.assertEqual(context.exception.code, "record_changed")
            self.assertEqual(validate_post(post, root).experiment.hypothesis, "A new client edit")

    def test_invalid_result_does_not_change_the_file_and_cli_writes_use_the_same_validator(self):
        import json
        from scripts.lib.content_lab import apply_command
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            post = root / "sample-2026-01-01"
            post.mkdir()
            (post / "post.md").write_text("# Sample")
            command = {"action": "record_results", "post_id": post.name, "expected_revision": None,
                       "publication": {"platform": "xhs", "published_at": "2026-01-02T00:00:00Z", "url": "https://www.xiaohongshu.com/explore/sample"},
                       "measurement": {"observed_at": "2026-01-01T00:00:00Z", "source": "Synthetic evidence", "views": 1}}
            with self.assertRaises(ValueError):
                apply_command(root, command)
            self.assertFalse((post / "lab.yaml").exists())
            command["measurement"]["observed_at"] = "2026-01-09T00:00:00Z"
            result = subprocess.run([sys.executable, str(repo / "scripts/content_lab.py"), "--root", str(root), "--apply", "--json"], input=json.dumps(command), capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout)
            value = json.loads(result.stdout)
            self.assertEqual(value["items"][0]["record"]["measurements"][0]["views"], 1)
            self.assertEqual(validate_post(post, root).stage, "published")

    def test_results_save_is_atomic_retryable_and_rejects_stale_edits(self):
        from scripts.lib.content_lab import apply_command, ContentWriteError
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            post = root / "sample-2026-01-01"
            post.mkdir()
            (post / "post.md").write_text("# Synthetic post\n")
            command = {"action": "record_results", "post_id": post.name, "expected_revision": None,
                       "publication": {"platform": "xhs", "published_at": "2026-01-01T00:00:00Z", "url": "https://www.xiaohongshu.com/explore/sample"},
                       "measurement": {"observed_at": "2026-01-08T00:00:00Z", "source": "Synthetic dashboard capture", "traffic": "organic", "views": 0}}
            first = apply_command(root, command)
            self.assertEqual(first.record.measurements[0].views, 0)
            self.assertIsNone(first.record.measurements[0].saves)
            self.assertEqual(apply_command(root, command), first)
            with self.assertRaises(ContentWriteError) as context:
                apply_command(root, {**command, "measurement": {**command["measurement"], "observed_at": "2026-01-09T00:00:00Z"}})
            self.assertEqual(context.exception.code, "record_changed")
            self.assertEqual(validate_post(post, root), first.record)

    def test_timestamps_counts_and_readiness_cannot_invent_evidence(self):
        publication = {"platform": "xhs", "published_at": "2026-01-01T00:00:00Z", "url": "https://www.xiaohongshu.com/explore/sample"}
        measurement = {"observed_at": "2026-01-08T00:00:00Z", "source": "Private platform capture", "views": 0}
        record = LabRecord.model_validate({"stage": "published", "publication": publication, "measurements": [measurement]})
        self.assertEqual(record.measurements[0].views, 0)
        self.assertIsNone(record.measurements[0].saves)
        for change in [{"views": -1}, {"views": True}, {"views": "100"}, {"observed_at": "2025-12-31T00:00:00Z"}, {"observed_at": "2026-01-08T00:00:00"}]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                LabRecord.model_validate({"publication": publication, "measurements": [{**measurement, **change}]})
        with self.assertRaisesRegex(ValueError, "readiness"):
            LabRecord.model_validate({"stage": "ready"})

    def test_symlink_escape_and_bad_images_are_rejected_and_cli_names_field(self):
        root_dir = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as other:
            root = Path(tmp)
            post = root / "sample-2026-01-01"
            post.mkdir()
            (post / "post.md").write_text("# Sample")
            (post / "publish.txt").write_text("Sample copy")
            (post / "lab.yaml").write_text(yaml.safe_dump({"stage": "ready", "readiness": {"factual": "passed", "visual": "passed", "owner_review": "accepted"}}))
            result = subprocess.run([sys.executable, str(root_dir / "scripts/content_lab.py"), "--root", str(root)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertRegex(result.stdout, "sample-2026-01-01.*images")
            (post / "images").mkdir()
            (post / "images/01-cover.png").write_bytes(b"not a PNG")
            with self.assertRaisesRegex(ValueError, "images"):
                validate_post(post, root)
            (post / "images/01-cover.png").write_bytes(b"\x89PNG\r\n\x1a\nsynthetic")
            self.assertEqual(validate_post(post, root).stage, "ready")
            (post / "lab.yaml").unlink()
            outside = Path(other) / "lab.yaml"
            outside.write_text("stage: research\n")
            (post / "lab.yaml").symlink_to(outside)
            with self.assertRaisesRegex(ValueError, "escaped"):
                validate_post(post, root)

    def test_generated_contract_is_current(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run([sys.executable, str(root / "scripts/export_content_lab_schema.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_legacy_and_unknown_are_preserved_while_bad_records_are_partial(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ["legacy", "research", "bad"]:
                post = root / f"{name}-2026-01-01"
                post.mkdir()
                (post / "post.md").write_text("# Sample\n")
            (root / "research-2026-01-01/lab.yaml").write_text("schema_version: 1\nstage: research\n")
            (root / "bad-2026-01-01/lab.yaml").write_text("stage: published\n")
            collection, errors = read_collection(root)
            self.assertTrue(collection.partial)
            self.assertEqual(len(errors), 1)
            self.assertIn("publication", errors[0])
            records = {i.post_id: i.record for i in collection.items}
            self.assertIsNone(records["legacy-2026-01-01"])
            self.assertEqual(records["research-2026-01-01"].readiness.factual, "unknown")

    def test_ready_with_missing_images_is_rejected_with_the_post_and_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            post = Path(tmp) / "sample-2026-01-01"
            post.mkdir()
            (post / "post.md").write_text("# Sample\n")
            (post / "publish.txt").write_text("Title: Sample\n")
            (post / "lab.yaml").write_text("""schema_version: 1
stage: ready
readiness:
  factual: passed
  visual: passed
  owner_review: accepted
""")
            with self.assertRaisesRegex(ValueError, "sample-2026-01-01.*images"):
                validate_post(post, Path(tmp))
