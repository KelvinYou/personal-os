"""Observation invariants with synthetic files only; never read real sessions."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from lib.office.monitor import Monitor, activity  # noqa: E402
from lib.schema import OfficeCfg  # noqa: E402

NOW = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)
IDENT = "00000000-0000-4000-8000-000000000001"
OTHER = "00000000-0000-4000-8000-000000000002"
CFG = OfficeCfg.model_validate_json((ROOT / "tests/fixtures/office/config.json").read_text())


def event(kind, at=NOW, **kwargs):
    return {"timestamp": at.isoformat(), "type": "event_msg", "payload": {"type": kind, **kwargs}}


def response(kind, at=NOW, **kwargs):
    return {"timestamp": at.isoformat(), "type": "response_item", "payload": {"type": kind, **kwargs}}


class OfficeTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.workspace = self.root / "workspace"; self.workspace.mkdir()
        self.source = self.root / "sessions"; self.source.mkdir()
        self.cache = self.root / "private" / "office"
        self.monitor = Monitor(self.source, self.workspace, self.cache, CFG)

    def file(self, ident=IDENT, cwd=None):
        folder = self.source / "2026/11/01"; folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"rollout-{ident}.jsonl"
        meta = {"timestamp": NOW.isoformat(), "type": "session_meta", "payload": {"id": ident, "cwd": str(cwd or self.workspace), "base_instructions": "PRIVATE_INSTRUCTIONS"}}
        path.write_text(json.dumps(meta) + "\n")
        return path

    def append(self, path, *records):
        with path.open("a") as out:
            for record in records: out.write(json.dumps(record) + "\n")

    def snap(self, at=NOW): return self.monitor.snapshot(at)

    def test_existing_session_attaches_and_incremental_events_do_not_duplicate(self):
        p = self.file(); self.append(p, event("task_started"), response("function_call", name="exec_command", arguments="SECRET"))
        first = self.snap()["sessions"][0]
        self.assertEqual(first["state"], "working")
        self.assertEqual(self.snap()["sessions"][0], first)
        self.append(p, event("task_complete", at=NOW + timedelta(seconds=1), last_agent_message="PRIVATE_RESPONSE"))
        ended = self.snap(NOW + timedelta(seconds=2))["sessions"][0]
        self.assertEqual(ended["state"], "idle")
        self.assertEqual(ended["activity_label"], "Turn ended")

    def test_current_workspace_only_and_no_sibling_prefix(self):
        self.file(); self.file(OTHER, self.root / "workspace-other")
        self.assertEqual([s["session_id"] for s in self.snap()["sessions"]], [IDENT])

    def test_two_sessions_keep_independent_state(self):
        first = self.file(); second = self.file(OTHER)
        self.append(first, event("task_started")); self.append(second, event("task_complete"))
        states = {s["session_id"]: s["state"] for s in self.snap()["sessions"]}
        self.assertEqual(states, {IDENT: "working", OTHER: "idle"})

    def test_working_stales_to_unknown_but_ended_turn_is_historical_fact(self):
        first = self.file(); second = self.file(OTHER)
        self.append(first, event("task_started")); self.append(second, event("task_complete"))
        states = {s["session_id"]: s["state"] for s in self.snap(NOW + timedelta(seconds=181))["sessions"]}
        self.assertEqual(states, {IDENT: "unknown", OTHER: "idle"})

    def test_waiting_requires_explicit_input_call_and_matching_reply(self):
        p = self.file()
        self.append(p, response("function_call", name="request_user_input", call_id="input-1", arguments="PRIVATE_QUESTION"))
        self.assertEqual(self.snap()["sessions"][0]["state"], "waiting")
        self.append(p, response("function_call_output", call_id="other", output="PRIVATE_RESULT"))
        self.assertEqual(self.snap()["sessions"][0]["state"], "waiting")
        self.append(p, response("function_call_output", call_id="input-1", output="PRIVATE_RESULT"))
        self.assertEqual(self.snap()["sessions"][0]["state"], "working")

    def test_async_question_is_not_a_waiting_session(self):
        self.assertEqual(activity(response("function_call", name="request_user_input_async"))[1], "working")

    def test_tool_error_does_not_fail_the_session(self):
        p = self.file(); self.append(p, event("item_completed", item={"type": "CommandExecution", "exit_code": 1, "command": "SECRET_COMMAND", "aggregated_output": "SECRET_OUTPUT"}))
        s = self.snap()["sessions"][0]
        self.assertEqual(s["state"], "working"); self.assertEqual(s["last_tool_outcome"], "error")

    def test_partial_last_line_is_retried_after_completion(self):
        p = self.file(); data = json.dumps(event("task_complete"))
        with p.open("a") as f: f.write(data[:20])
        self.assertEqual(self.snap()["sessions"][0]["state"], "unknown")
        with p.open("a") as f: f.write(data[20:] + "\n")
        self.assertEqual(self.snap()["sessions"][0]["state"], "idle")

    def test_out_of_order_events_do_not_overwrite_newer_evidence(self):
        p = self.file(); self.append(p, event("task_complete"), event("task_started", at=NOW - timedelta(seconds=1)))
        self.assertEqual(self.snap()["sessions"][0]["state"], "idle")

    def test_final_text_alone_does_not_prove_task_completion(self):
        p = self.file(); self.append(p, event("task_started"), response("message", role="assistant", phase="final_answer", content=[{"text": "PRIVATE"}]))
        self.assertEqual(self.snap()["sessions"][0]["state"], "working")

    def test_schema_mismatch_unknown_shapes_and_malformed_lines_are_visible(self):
        p = self.file(); self.append(p, event("task_started"))
        with p.open("a") as f: f.write('broken-json\n[]\n')
        result = self.snap()
        self.assertEqual(result["source_status"], "partial")
        self.assertIn("history_partial", result["warnings"])
        (self.cache / "projection.json").write_text('{"schema_version":999,"files":{}}')
        self.assertEqual(self.snap()["sessions"][0]["state"], "working")

    def test_truncation_rebuilds_and_reconnect_replays_without_invented_state(self):
        p = self.file(); self.append(p, event("task_started")); self.snap()
        self.file(); self.append(p, event("task_complete"))
        self.assertEqual(self.snap()["sessions"][0]["state"], "idle")

    def test_no_private_content_is_copied_to_public_output_or_private_projection(self):
        p = self.file(); self.append(p, response("function_call", name="exec_command", arguments="SECRET_ARGUMENT"), event("task_complete", last_agent_message="SECRET_RESPONSE"))
        output = json.dumps(self.snap()); cache = (self.cache / "projection.json").read_text()
        for value in [str(self.workspace), "PRIVATE_INSTRUCTIONS", "SECRET_ARGUMENT", "SECRET_RESPONSE"]:
            self.assertNotIn(value, output); self.assertNotIn(value, cache)

    def test_missing_source_and_symlink_cache_fail_explicitly(self):
        monitor = Monitor(self.root / "missing", self.workspace, self.cache, CFG)
        with self.assertRaises(FileNotFoundError): monitor.snapshot(NOW)
        other = self.root / "elsewhere"; other.mkdir()
        cache = self.root / "cache-link"; cache.symlink_to(other)
        with self.assertRaisesRegex(ValueError, "unsafe_cache_path"):
            Monitor(self.source, self.workspace, cache, CFG).snapshot(NOW)

    def test_private_permissions_and_bounded_event_history(self):
        p = self.file(); self.append(p, *[response("reasoning") for _ in range(30)])
        self.assertEqual(len(self.snap()["sessions"][0]["events"]), CFG.recent_events)
        self.assertEqual(self.cache.stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.cache / "projection.json").stat().st_mode & 0o777, 0o600)

    def test_giant_records_do_not_hide_following_live_activity(self):
        p = self.file()
        self.append(p, response("custom_tool_call_output", output="x" * (CFG.max_read_bytes + 10)), event("task_started"))
        snapshot = self.snap()
        self.assertEqual(snapshot["sessions"][0]["state"], "working")
        self.assertIn("history_partial", snapshot["warnings"])

    def test_snapshot_field_parity_with_the_web_boundary_fixture(self):
        p = self.file(); self.append(p, event("task_started"))
        actual = self.snap()
        fixture = json.loads((ROOT / "tests/fixtures/office/snapshot.json").read_text())
        self.assertEqual(set(actual), set(fixture))
        self.assertEqual(set(actual["sessions"][0]), set(fixture["sessions"][0]))
        self.assertEqual(set(actual["sessions"][0]["events"][0]), set(fixture["sessions"][0]["events"][0]))

    def test_concurrent_readers_share_atomic_private_projection(self):
        from concurrent.futures import ThreadPoolExecutor
        p = self.file(); self.append(p, event("task_started"))
        with ThreadPoolExecutor(max_workers=4) as pool:
            values = list(pool.map(lambda _: self.snap(), range(8)))
        self.assertTrue(all(v["sessions"][0]["state"] == "working" for v in values))
        self.assertEqual(len(values[-1]["sessions"][0]["events"]), 1)

    def test_bounds_config_is_optional_for_other_consumers_but_strict_when_enabled(self):
        from lib.schema import Thresholds
        import yaml
        cfg = yaml.safe_load((ROOT / "tests/fixtures/config/thresholds.yaml").read_text())
        self.assertIsNone(Thresholds.model_validate(cfg).office)
        with self.assertRaises(ValueError): OfficeCfg.model_validate({**CFG.model_dump(), "stale_after_seconds": 0})

    def test_local_date_folder_ahead_of_utc_is_discovered(self):
        p = self.file(); self.append(p, event("task_started"))
        tomorrow = self.source / "2026/11/02"; tomorrow.mkdir()
        p.rename(tomorrow / p.name)
        self.assertEqual(self.snap()["sessions"][0]["state"], "working")

    def test_unsupported_source_header_is_partial_not_empty_success(self):
        p = self.file(); p.write_text('{"type":"future_format"}\n')
        result = self.snap()
        self.assertEqual(result["source_status"], "partial")
        self.assertIn("record_unavailable", result["warnings"])

    def test_same_inode_rewrite_with_an_unchanged_prefix_rebuilds(self):
        p = self.file()
        self.append(p, response("custom_tool_call_output", output="x" * 5000), event("task_started"))
        self.snap()
        content = p.read_text().replace('"task_started"', '"task_complete"')
        p.write_text(content)
        self.assertEqual(self.snap()["sessions"][0]["state"], "idle")

    def test_explicit_failure_and_abort_have_distinct_states(self):
        p = self.file(); self.append(p, event("task_failed"))
        self.assertEqual(self.snap()["sessions"][0]["state"], "error")
        self.append(p, event("turn_aborted", at=NOW + timedelta(seconds=1)))
        self.assertEqual(self.snap(NOW + timedelta(seconds=2))["sessions"][0]["state"], "idle")

    def test_duplicate_source_records_do_not_spawn_duplicate_workers(self):
        p = self.file(); self.append(p, event("task_started"))
        (p.parent / "copy.jsonl").write_text(p.read_text())
        snapshot = self.snap()
        self.assertEqual(len(snapshot["sessions"]), 1)
        self.assertIn("duplicate_session", snapshot["warnings"])


if __name__ == "__main__": unittest.main()
