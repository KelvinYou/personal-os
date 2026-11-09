"""Claude Code observation, attention zones and waits — synthetic transcripts only; never read real sessions."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
import unittest.mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from lib.office.attention import expand_segments, waits  # noqa: E402
from lib.office.claude import workspace_slug  # noqa: E402
from lib.office.monitor import Monitor  # noqa: E402
from lib.schema import OfficeCfg  # noqa: E402

NOW = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)
MAIN = "10000000-0000-4000-8000-000000000001"
OTHER = "10000000-0000-4000-8000-000000000002"
CFG = OfficeCfg.model_validate_json((ROOT / "tests/fixtures/office/config.json").read_text())
SECRETS = ["SECRET_PROMPT", "SECRET_INPUT", "SECRET_OUTPUT", "SECRET_TITLE", "SECRET_TEXT"]


def at(seconds: float) -> str:
    return (NOW + timedelta(seconds=seconds)).isoformat().replace("+00:00", "Z")


class ClaudeFixture(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.workspace = self.root / "personal-os"; self.workspace.mkdir()
        self.codex = self.root / "codex"; self.codex.mkdir()
        self.projects = self.root / "claude" / "projects"; self.projects.mkdir(parents=True)
        self.cache = self.root / "private" / "office"
        self.monitor = Monitor(self.codex, self.workspace, self.cache, CFG, self.projects)

    def transcript(self, ident=MAIN, cwd=None, folder=None, subagent=None):
        directory = self.projects / (folder or workspace_slug(self.workspace.resolve()))
        directory.mkdir(parents=True, exist_ok=True)
        if subagent:
            path = directory / ident / "subagents" / f"agent-{subagent}.jsonl"; path.parent.mkdir(parents=True, exist_ok=True)
        else:
            path = directory / f"{ident}.jsonl"
        header = [{"type": "permission-mode", "permissionMode": "default", "sessionId": ident},
                  {"type": "ai-title", "aiTitle": "SECRET_TITLE", "sessionId": ident}]
        path.write_text("".join(json.dumps(r) + "\n" for r in header))
        self.cwd = str(cwd or self.workspace)
        return path

    def add(self, path, *records):
        with path.open("a") as out:
            for record in records: out.write(json.dumps(record) + "\n")

    def prompt(self, seconds, text="SECRET_PROMPT"):
        return {"type": "user", "cwd": self.cwd, "timestamp": at(seconds), "message": {"role": "user", "content": text}}

    def tool(self, seconds, name, call, skill=None):
        record = {"type": "assistant", "cwd": self.cwd, "timestamp": at(seconds), "message": {"role": "assistant", "stop_reason": "tool_use", "content": [{"type": "tool_use", "id": call, "name": name, "input": {"command": "SECRET_INPUT"}}]}}
        if skill: record["attributionSkill"] = skill
        return record

    def result(self, seconds, call, error=False, output="SECRET_OUTPUT"):
        return {"type": "user", "cwd": self.cwd, "timestamp": at(seconds), "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": call, "is_error": error, "content": output}]}}

    def end(self, seconds):
        return {"type": "assistant", "cwd": self.cwd, "timestamp": at(seconds), "message": {"role": "assistant", "stop_reason": "end_turn", "content": [{"type": "text", "text": "SECRET_TEXT"}]}}

    def session(self, seconds=0, ident=MAIN):
        snap = self.monitor.snapshot(NOW + timedelta(seconds=seconds))
        return next(s for s in snap["sessions"] if s["session_id"] == ident)


class ClaudeObservationTests(ClaudeFixture):
    def test_tool_call_works_then_flags_possible_approval_then_resolves(self):
        p = self.transcript(); self.add(p, self.prompt(0), self.tool(1, "Bash", "call-1"))
        live = self.session(2)
        self.assertEqual((live["runtime"], live["state"], live["attention"], live["tool"]), ("claude", "working", "working", "command"))
        flagged = self.session(1 + CFG.pending_tool_seconds + 1)
        self.assertEqual(flagged["attention"], "needs_you")
        self.assertEqual(flagged["activity_label"], "Tool pending: approval or long run")
        self.assertEqual(flagged["attention_since"], at(1 + CFG.pending_tool_seconds))
        self.add(p, self.result(60, "call-1"))
        self.assertEqual(self.session(61)["attention"], "working")

    def test_end_turn_is_review_then_done_after_the_window(self):
        p = self.transcript(); self.add(p, self.prompt(0), self.end(5))
        ended = self.session(6)
        self.assertEqual((ended["state"], ended["attention"], ended["attention_since"]), ("idle", "review", at(5)))
        later = self.session(5 + CFG.review_window_seconds + 1)
        self.assertEqual(later["attention"], "done")

    def test_explicit_question_needs_you_until_answered(self):
        p = self.transcript(); self.add(p, self.prompt(0), self.tool(1, "AskUserQuestion", "ask-1"))
        waiting = self.session(2)
        self.assertEqual((waiting["state"], waiting["attention"], waiting["activity_label"]), ("waiting", "needs_you", "Waiting for your input"))
        self.add(p, self.result(30, "other")); self.assertEqual(self.session(31)["attention"], "needs_you")
        self.add(p, self.result(40, "ask-1")); self.assertEqual(self.session(41)["state"], "working")

    def test_waiting_longer_than_the_cap_is_abandoned_not_waiting(self):
        p = self.transcript(); self.add(p, self.prompt(0), self.tool(1, "AskUserQuestion", "ask-1"))
        self.assertEqual(self.session(CFG.wait_cap_seconds + 10)["attention"], "done")

    def test_sibling_prefix_directory_is_rejected_by_recorded_cwd(self):
        sibling = self.root / "personal-os-other"; sibling.mkdir()
        p = self.transcript(OTHER, cwd=sibling, folder=workspace_slug(self.workspace.resolve()) + "-other")
        self.add(p, self.prompt(0))
        q = self.transcript(MAIN, folder=workspace_slug(self.workspace.resolve()) + "--claude-worktrees-x", cwd=self.workspace / ".claude" / "worktrees" / "x")
        self.add(q, self.prompt(0))
        ids = [s["session_id"] for s in self.monitor.snapshot(NOW)["sessions"]]
        self.assertEqual(ids, [MAIN])

    def test_fresh_subagent_links_to_parent_and_stale_subagent_leaves(self):
        p = self.transcript(); self.add(p, self.prompt(0), self.tool(1, "Agent", "spawn-1"))
        sub = self.transcript(MAIN, subagent="abc123"); self.add(sub, self.prompt(2), self.tool(3, "Read", "r-1"))
        snap = self.monitor.snapshot(NOW + timedelta(seconds=4))
        child = next(s for s in snap["sessions"] if s["parent_session_id"])
        self.assertEqual((child["session_id"], child["parent_session_id"], child["tool"]), (f"{MAIN}:abc123", MAIN, "read"))
        parent = next(s for s in snap["sessions"] if s["session_id"] == MAIN)
        self.assertEqual(parent["tool"], "agent")
        old = (NOW - timedelta(seconds=CFG.review_window_seconds + 60)).timestamp()
        import os; os.utime(sub, (old, old))
        snap = self.monitor.snapshot(NOW + timedelta(seconds=5))
        self.assertFalse(any(s["parent_session_id"] for s in snap["sessions"]))

    def test_skill_attribution_becomes_a_badge_and_invalid_names_are_dropped(self):
        p = self.transcript(); self.add(p, self.prompt(0), self.tool(1, "Read", "r-1", skill="weekly-review"))
        self.assertEqual(self.session(2)["role_ids"], ["weekly-review"])
        self.add(p, self.tool(3, "Read", "r-2", skill="../../etc/passwd"))
        self.assertEqual(self.session(4)["role_ids"], ["weekly-review"])

    def test_no_private_content_reaches_output_or_cache(self):
        p = self.transcript(); self.add(p, self.prompt(0), self.tool(1, "Bash", "c-1"), self.result(2, "c-1"), self.end(3))
        output = json.dumps(self.monitor.snapshot(NOW + timedelta(seconds=4))); cache = (self.cache / "projection.json").read_text()
        for value in SECRETS + [str(self.workspace), str(self.projects)]:
            self.assertNotIn(value, output); self.assertNotIn(value, cache)

    def test_giant_tool_result_closes_the_call_without_a_coverage_gap(self):
        p = self.transcript(); self.add(p, self.prompt(0), self.tool(1, "Read", "big-1"), self.result(2, "big-1", output="x" * (CFG.max_record_bytes + 10)))
        snap = self.monitor.snapshot(NOW + timedelta(seconds=CFG.pending_tool_seconds + 10))
        self.assertEqual(snap["sessions"][0]["attention"], "working")
        self.assertNotEqual(snap["sessions"][0]["activity_label"], "Tool pending: approval or long run")
        self.assertNotIn("history_partial", snap["warnings"])

    def test_interrupt_marker_ends_the_turn(self):
        p = self.transcript(); self.add(p, self.prompt(0), self.tool(1, "Bash", "c-1"), self.prompt(2, "[Request interrupted by user for tool use]"))
        self.assertEqual(self.session(3)["state"], "idle")

    def test_codex_only_and_claude_only_report_coverage_and_both_missing_fail(self):
        p = self.transcript(); self.add(p, self.prompt(0))
        only_claude = Monitor(self.root / "missing", self.workspace, self.cache, CFG, self.projects).snapshot(NOW)
        self.assertEqual(only_claude["source_coverage"], {"codex": "unavailable", "claude": "connected"})
        self.assertIn("source_missing", only_claude["warnings"])
        only_codex = Monitor(self.codex, self.workspace, self.root / "c2", CFG).snapshot(NOW)
        self.assertEqual(only_codex["source_coverage"], {"codex": "connected", "claude": "disabled"})
        self.assertNotIn("source_missing", only_codex["warnings"])
        with self.assertRaises(FileNotFoundError):
            Monitor(self.root / "missing", self.workspace, self.root / "c3", CFG, self.root / "nope").snapshot(NOW)

    def test_disabled_claude_source_is_not_read(self):
        p = self.transcript(); self.add(p, self.prompt(0))
        cfg = CFG.model_copy(update={"claude_enabled": False})
        snap = Monitor(self.codex, self.workspace, self.root / "c4", cfg, self.projects).snapshot(NOW)
        self.assertEqual((snap["sessions"], snap["source_coverage"]["claude"]), ([], "disabled"))

    def test_segments_replay_the_day_including_implied_crossings(self):
        p = self.transcript(); self.add(p, self.prompt(0), self.tool(10, "Edit", "e-1"), self.result(200, "e-1"), self.end(210), self.prompt(210 + CFG.review_window_seconds + 100))
        segments = self.session(210 + CFG.review_window_seconds + 101)["segments"]
        self.assertEqual([(s["attention"], s["tool"]) for s in segments], [
            ("working", None), ("working", "edit"), ("needs_you", "edit"), ("working", "edit"), ("review", None), ("done", None), ("working", None),
        ])
        self.assertEqual(segments[2]["at"], at(10 + CFG.pending_tool_seconds))

    def test_incremental_reads_do_not_duplicate_segments(self):
        p = self.transcript(); self.add(p, self.prompt(0), self.tool(1, "Read", "r-1"))
        first = self.session(2)["segments"]
        self.assertEqual(self.session(2)["segments"], first)


class WeekWaitTests(ClaudeFixture):
    def test_week_scan_buckets_waits_by_local_day_and_renders_markdown(self):
        from zoneinfo import ZoneInfo
        from lib.office.waits import markdown, week_waits
        p = self.transcript(); self.add(p, self.prompt(0), self.end(10), self.prompt(130), self.end(140), self.prompt(140 + 600))
        week = week_waits(self.codex, self.workspace, self.projects, CFG, NOW.date() - timedelta(days=NOW.weekday()), ZoneInfo("Asia/Kuala_Lumpur"), NOW + timedelta(hours=1))
        summary = week.summary()
        self.assertEqual((summary["waits"], summary["total_minutes"], summary["median_minutes"]), (2, 12.0, 6.0))
        day = next(d for d in week.days if d.closed)
        self.assertEqual(day.day.isoformat(), "2026-11-01")
        text = "\n".join(markdown(week, CFG))
        self.assertIn("2 turns waited for you", text); self.assertIn("[Status: OK]", text)
        for secret in SECRETS: self.assertNotIn(secret, text)


class HookSignalTests(ClaudeFixture):
    """Exact permission waits from the office_signal hook (office-attention-radar.md §4.1)."""

    def signal(self, seconds, event, kind=None, ident=MAIN):
        from lib.office.signals import record
        payload = {"hook_event_name": event, "session_id": ident, "cwd": str(self.workspace), "message": "SECRET_TEXT", "transcript_path": str(self.projects)}
        if kind: payload["notification_type"] = kind
        return record(payload, self.cache, NOW + timedelta(seconds=seconds))

    def test_record_keeps_only_allowlisted_fields_and_ignores_other_events(self):
        from lib.office.signals import FILE_NAME
        self.assertTrue(self.signal(0, "SessionStart"))
        self.assertTrue(self.signal(1, "Notification", "permission_prompt"))
        self.assertFalse(self.signal(2, "Notification", "idle_prompt"))
        self.assertFalse(self.signal(3, "Notification", "permission_prompt", ident="../not-a-uuid"))
        path = self.cache / FILE_NAME
        lines = [json.loads(line) for line in path.read_text().splitlines()]
        self.assertEqual([(l["kind"], set(l)) for l in lines], [("hooked", {"session_id", "kind", "at"}), ("prompt", {"session_id", "kind", "at"})])
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        for value in ["SECRET_TEXT", str(self.workspace), str(self.projects)]: self.assertNotIn(value, path.read_text())

    def test_record_rotates_to_the_newest_lines(self):
        from lib.office import signals
        with unittest.mock.patch.object(signals, "MAX_BYTES", 400), unittest.mock.patch.object(signals, "KEEP_LINES", 3):
            for i in range(20): self.signal(i, "SessionStart")
        lines = (self.cache / signals.FILE_NAME).read_text().splitlines()
        self.assertLessEqual(len(lines), 4); self.assertIn(at(19), lines[-1])

    def test_permission_prompt_is_an_exact_wait_closed_by_the_tool_result(self):
        p = self.transcript(); self.add(p, self.prompt(0), self.tool(1, "Bash", "c-1"))
        self.signal(0, "SessionStart"); self.signal(2, "Notification", "permission_prompt")
        waiting = self.session(3)
        self.assertEqual((waiting["state"], waiting["attention"], waiting["attention_since"], waiting["activity_label"]),
                         ("waiting", "needs_you", at(2), "Waiting for your approval"))
        self.add(p, self.result(30, "c-1"))
        resumed = self.session(31)
        self.assertEqual((resumed["state"], resumed["attention"]), ("working", "working"))
        self.assertIn(("waiting", "needs_you"), [(s["state"], s["attention"]) for s in resumed["segments"]])

    def test_hooked_session_without_a_prompt_is_a_long_run_not_a_guess(self):
        p = self.transcript(); self.add(p, self.prompt(0), self.tool(1, "Bash", "c-1"))
        self.signal(0, "SessionStart")
        late = self.session(1 + CFG.pending_tool_seconds + 5)
        self.assertEqual((late["attention"], late["tool"]), ("working", "command"))
        self.assertNotIn("needs_you", [s["attention"] for s in late["segments"]])

    def test_prompt_before_the_turn_is_ignored_and_subagents_never_take_signals(self):
        p = self.transcript(); self.add(p, self.prompt(10), self.end(20))
        self.signal(5, "Notification", "permission_prompt")
        self.assertEqual(self.session(21)["attention"], "review")

    def test_week_scan_counts_the_permission_wait(self):
        from zoneinfo import ZoneInfo
        from lib.office.waits import week_waits
        p = self.transcript(); self.add(p, self.prompt(0), self.tool(1, "Bash", "c-1"), self.result(301, "c-1"), self.end(310))
        self.signal(0, "SessionStart"); self.signal(1, "Notification", "permission_prompt")
        week = week_waits(self.codex, self.workspace, self.projects, CFG, NOW.date() - timedelta(days=NOW.weekday()), ZoneInfo("Asia/Kuala_Lumpur"), NOW + timedelta(hours=1), signals_dir=self.cache)
        self.assertEqual(week.summary()["waits"], 1); self.assertEqual(week.closed, [300.0])


class InPlayTests(unittest.TestCase):
    def line(self, *points):
        from lib.office.waits import timeline
        return timeline([{"at": at(seconds), "phase": phase, "tool": None} for seconds, phase in points])

    def test_counts_running_and_queued_sessions_only_while_they_hold_attention(self):
        from lib.office.waits import in_play
        lines = {"self": self.line((0, "active"), (100, "ended")),
                 "running": self.line((50, "active"), (500, "ended")),
                 "in-review": self.line((0, "ended")),
                 "asked": self.line((90, "input")),
                 "not-started": self.line((200, "active"))}
        self.assertEqual(in_play(lines, NOW + timedelta(seconds=100), CFG), 4)
        later = NOW + timedelta(seconds=CFG.review_window_seconds + 1)
        self.assertEqual(in_play({"finished": self.line((0, "ended"))}, later, CFG), 0)
        silent = NOW + timedelta(seconds=CFG.stale_after_seconds + 1)
        self.assertEqual(in_play({"silent": self.line((0, "active"))}, silent, CFG), 0)

    def test_markdown_names_where_long_waits_happen(self):
        from datetime import date
        from lib.office.waits import DayWaits, WeekWaits, markdown
        long, short = CFG.wait_median_warning_seconds + 60.0, 30.0
        day = DayWaits(date(2026, 11, 2), closed=[long, long, short, short, short])
        week = WeekWaits(date(2026, 11, 2), [day], 2, 0, {1: [long, long], 3: [short, short, short]})
        text = "\n".join(markdown(week, CFG))
        self.assertIn("| In play | Waits |", text); self.assertIn("only 1–2 sessions in play (100% vs 0%)", text)
        week.by_play = {1: [short, short], 6: [long, short]}
        self.assertIn("cap parallel sessions", "\n".join(markdown(week, CFG)))
        self.assertIn("| 5+ | 2 |", "\n".join(markdown(week, CFG)))


class WaitTests(unittest.TestCase):
    def raw(self, *points):
        return [{"at": at(seconds), "phase": phase, "tool": None} for seconds, phase in points]

    def test_closed_abandoned_open_and_unclosed_waits(self):
        cap = CFG.wait_cap_seconds
        points = self.raw((0, "active"), (10, "ended"), (70, "active"), (80, "input"), (90, "ended"), (200, "active"),
                          (300, "ended"), (300 + cap + 5, "active"), (cap + 400, "ended"), (cap + 410, "failed"), (cap + 500, "ended"))
        result = waits(points, CFG, NOW, NOW + timedelta(days=2))
        self.assertEqual([(w["kind"], w["seconds"]) for w in result], [("closed", 60.0), ("closed", 120.0), ("abandoned", cap + 5.0), ("open", None)])

    def test_waits_outside_the_range_are_ignored(self):
        points = self.raw((10, "ended"), (70, "active"))
        self.assertEqual(waits(points, CFG, NOW + timedelta(seconds=20), NOW + timedelta(days=1)), [])

    def test_expand_segments_bounds_output(self):
        points = self.raw(*[(i * 2, "active" if i % 2 else "ended") for i in range(CFG.max_segments * 3)])
        self.assertLessEqual(len(expand_segments(points, NOW + timedelta(days=1), CFG)), CFG.max_segments)


if __name__ == "__main__": unittest.main()
