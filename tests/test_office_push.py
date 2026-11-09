"""Phone push for agent waits — synthetic payloads only; no network, no real private config."""
from __future__ import annotations

import importlib.util
import io
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from pydantic import ValidationError  # noqa: E402
from lib.office import push  # noqa: E402
from lib.schema import OfficePushCfg  # noqa: E402

spec = importlib.util.spec_from_file_location("office_signal", ROOT / "scripts" / "office_signal.py")
office_signal = importlib.util.module_from_spec(spec); spec.loader.exec_module(office_signal)

TOPIC = "pos-test-topic-0123456789abcdef"
CFG = OfficePushCfg(enabled=True, topic=TOPIC)
SESSION = "10000000-0000-4000-8000-000000000001"


class FakeResponse:
    status = 200
    def __enter__(self): return self
    def __exit__(self, *_): return False


class PushTests(unittest.TestCase):
    def test_config_rejects_guessable_topics_and_plain_http(self):
        for bad in ({"topic": "short"}, {"topic": TOPIC, "server": "http://ntfy.sh"}, {"topic": "has/slash-0123456789abcdef"}):
            with self.assertRaises(ValidationError): OfficePushCfg(**bad)
        self.assertEqual((CFG.server, CFG.approval_delay_seconds, CFG.idle_turns), ("https://ntfy.sh", 90, True))

    def test_deliver_sends_fixed_text_only(self):
        sent = []
        push.deliver(CFG, "approval", opener=lambda request, timeout, context: sent.append(request) or FakeResponse())
        request = sent[0]
        self.assertEqual(request.full_url, f"https://ntfy.sh/{TOPIC}")
        self.assertEqual(request.data.decode(), push.MESSAGES["approval"][1])
        self.assertEqual(request.get_header("Priority"), "high")
        for value in [SESSION, "SECRET", str(ROOT)]: self.assertNotIn(value, request.data.decode() + str(request.header_items()))

    def test_approval_pushes_only_when_the_transcript_stays_unchanged(self):
        with TemporaryDirectory() as folder:
            transcript = Path(folder) / f"{SESSION}.jsonl"; transcript.write_text("{}\n")
            self.assertTrue(push.unanswered_approval(CFG, transcript, sleep=lambda _: None))
            calls = iter([None, lambda: transcript.write_text("{}\n{}\n")])
            def sleep(_):
                action = next(calls)
                if action: action()
            self.assertFalse(push.unanswered_approval(CFG, transcript, sleep=sleep))

    def test_transcript_path_must_be_a_jsonl_file_under_projects(self):
        with TemporaryDirectory() as folder:
            projects = Path(folder) / "projects"; (projects / "slug").mkdir(parents=True)
            good = projects / "slug" / f"{SESSION}.jsonl"; good.write_text("")
            outside = Path(folder) / "outside.jsonl"; outside.write_text("")
            link = projects / "slug" / "link.jsonl"; link.symlink_to(outside)
            self.assertEqual(push.transcript_path(str(good), projects), good)
            for value in [str(outside), str(link), str(projects / "slug" / "missing.jsonl"), None, 3]:
                self.assertIsNone(push.transcript_path(value, projects))


class HookRoutingTests(unittest.TestCase):
    def payload(self, kind):
        return {"hook_event_name": "Notification", "notification_type": kind, "session_id": SESSION}

    def test_push_kind_maps_notifications_and_respects_switches(self):
        self.assertEqual(office_signal.push_kind(self.payload("permission_prompt"), CFG), "approval")
        self.assertEqual(office_signal.push_kind(self.payload("elicitation_dialog"), CFG), "approval")
        self.assertEqual(office_signal.push_kind(self.payload("idle_prompt"), CFG), "idle")
        self.assertIsNone(office_signal.push_kind(self.payload("idle_prompt"), CFG.model_copy(update={"idle_turns": False})))
        self.assertIsNone(office_signal.push_kind(self.payload("auth_success"), CFG))
        self.assertIsNone(office_signal.push_kind(self.payload("permission_prompt"), None))
        self.assertIsNone(office_signal.push_kind({"hook_event_name": "SessionStart", "session_id": SESSION}, CFG))

    def test_deferred_worker_skips_answered_prompts_and_sends_idle_at_once(self):
        with mock.patch.object(office_signal, "push_cfg", return_value=CFG), mock.patch("lib.office.push.deliver") as deliver, \
             mock.patch("lib.office.push.unanswered_approval", return_value=False):
            office_signal.deferred("approval", "/x.jsonl"); deliver.assert_not_called()
            office_signal.deferred("idle", None); deliver.assert_called_once_with(CFG, "idle")

    def test_hook_never_raises_and_always_exits_zero(self):
        # Hook mode reads the payload from stdin; give it one so the test never blocks on a live terminal.
        with mock.patch.object(office_signal, "hook", side_effect=RuntimeError("boom")), mock.patch("sys.stdin", io.StringIO("{}")):
            self.assertEqual(office_signal.main([]), 0)
        with mock.patch.object(office_signal, "deferred", side_effect=OSError("offline")):
            self.assertEqual(office_signal.main(["--deferred", "idle"]), 0)


if __name__ == "__main__": unittest.main()
