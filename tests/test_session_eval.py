"""Tests for the session-eval loop.

These lean on synthetic transcripts rather than real ones on purpose: the real
files live in ~/.claude/projects, they are private, and they change every time
anyone uses the machine. A test that reads them would pass or fail depending on
what the user did that afternoon.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import session_eval  # noqa: E402
from lib.transcript import classify_tool, is_injected, parse_session  # noqa: E402


# ---------------------------------------------------------------------------
# Transcript builder
# ---------------------------------------------------------------------------


def _line(**kw) -> str:
    return json.dumps(kw)


def build_transcript(path: Path, blocks: list[dict]) -> Path:
    """Write a minimal but structurally faithful transcript.

    `blocks` is a flat script of {"user": text} / {"tool": (name, input)} /
    {"result": is_error} / {"assistant": text} steps.
    """
    lines: list[str] = []
    counter = 0
    common = dict(
        cwd="/repo/personal-os",
        gitBranch="main",
        sessionId=path.stem,
        isSidechain=False,
        userType="external",
        version="1.0.0",
        entrypoint="cli",
    )
    for step in blocks:
        counter += 1
        ts = f"2026-08-01T0{counter % 10}:00:00.000Z"
        if "user" in step:
            lines.append(
                _line(
                    type="user",
                    timestamp=ts,
                    message={"role": "user", "content": step["user"]},
                    **common,
                )
            )
        elif "assistant" in step:
            lines.append(
                _line(
                    type="assistant",
                    timestamp=ts,
                    message={
                        "role": "assistant",
                        "model": "claude-opus-5",
                        "usage": {"output_tokens": 10},
                        "content": [{"type": "text", "text": step["assistant"]}],
                    },
                    **common,
                )
            )
        elif "tool" in step:
            name, tool_input = step["tool"]
            tid = f"toolu_{counter}"
            lines.append(
                _line(
                    type="assistant",
                    timestamp=ts,
                    message={
                        "role": "assistant",
                        "model": "claude-opus-5",
                        "usage": {"output_tokens": 5},
                        "content": [
                            {"type": "tool_use", "id": tid, "name": name, "input": tool_input}
                        ],
                    },
                    **common,
                )
            )
            lines.append(
                _line(
                    type="user",
                    timestamp=ts,
                    message={
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": tid,
                                "is_error": step.get("is_error", False),
                                "content": "ok",
                            }
                        ],
                    },
                    **common,
                )
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


class ClassifyToolTests(unittest.TestCase):
    def test_dedicated_tools(self):
        self.assertEqual(classify_tool("Read", {"file_path": "a.py"}), "read")
        self.assertEqual(classify_tool("Edit", {"file_path": "a.py"}), "mutate")
        self.assertEqual(classify_tool("ScheduleWakeup", {}), "other")

    def test_bash_verify_beats_mutate(self):
        # make test writes caches; its purpose is still checking.
        self.assertEqual(classify_tool("Bash", {"command": "make test > out.log"}), "verify")

    def test_devnull_redirect_is_not_a_mutation(self):
        # The regression this whole classifier exists for: a read-only grep
        # counted as a write, which made write-before-read fire on sessions
        # that never wrote anything.
        for cmd in (
            "grep -rn foo src 2>/dev/null | head",
            "ls node_modules 2>&1",
            "cat file > /dev/null",
        ):
            with self.subTest(cmd=cmd):
                self.assertEqual(classify_tool("Bash", {"command": cmd}), "read")

    def test_scratchpad_redirect_is_not_a_mutation(self):
        cmd = "npm run dev > /private/tmp/claude-1/scratchpad/dev.log"
        self.assertEqual(classify_tool("Bash", {"command": cmd}), "other")

    def test_real_writes_are_mutations(self):
        for cmd in (
            "sed -i '' s/a/b/ file.py",
            "git commit -m x",
            "rm -rf build",
            "echo hi > real_file.txt",
        ):
            with self.subTest(cmd=cmd):
                self.assertEqual(classify_tool("Bash", {"command": cmd}), "mutate")


class InjectedTurnTests(unittest.TestCase):
    def test_harness_banners_are_injected(self):
        for text in (
            "<command-name>/clear</command-name>",
            "<local-command-caveat>Caveat: …</local-command-caveat>",
            "<system-reminder>be good</system-reminder>",
            "Caveat: The messages below were generated…",
            "<task-notification>\n<task-id>abc</task-id>",
            "Another Claude session sent a message:\n<teammate>…",
            "Base directory for this skill: /repo/.claude/skills/x",
            "<local-command-stdout>Set model to Opus 5",
            "[Image: source: /home/u/.claude/image-cache/x.png]",
        ):
            with self.subTest(text=text):
                self.assertTrue(is_injected(text))

    def test_slash_command_body_is_injected(self):
        self.assertTrue(is_injected("# /loop — schedule a recurring prompt\n\nParse the input…"))

    def test_human_prose_is_not_injected(self):
        self.assertFalse(is_injected("fix 1, 3, 4"))
        self.assertFalse(is_injected("# My heading in a pasted doc"))
        # An image plus a real question is a real prompt.
        self.assertFalse(is_injected("[Image #6] why is the back button broken?"))


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


class ParseSessionTests(unittest.TestCase):
    def _parse(self, blocks):
        with TemporaryDirectory() as d:
            p = build_transcript(Path(d) / "abcd1234-0000-0000-0000-000000000000.jsonl", blocks)
            return parse_session(p)

    def test_tool_results_do_not_count_as_prompts(self):
        s = self._parse(
            [
                {"user": "do the thing"},
                {"tool": ("Read", {"file_path": "a.py"})},
                {"tool": ("Read", {"file_path": "b.py"})},
            ]
        )
        self.assertEqual(s.user_prompts, ["do the thing"])
        self.assertEqual(len(s.tool_calls), 2)

    def test_injected_turns_excluded_from_prompts(self):
        s = self._parse(
            [
                {"user": "<command-name>/clear</command-name>"},
                {"user": "real question"},
            ]
        )
        self.assertEqual(s.user_prompts, ["real question"])

    def test_errors_are_paired_to_their_call(self):
        s = self._parse(
            [
                {"user": "go"},
                {"tool": ("Bash", {"command": "false"}), "is_error": True},
                {"tool": ("Bash", {"command": "ls"}), "is_error": False},
            ]
        )
        self.assertEqual(len(s.tool_errors), 1)
        self.assertEqual(s.tool_errors[0].summary, "false")

    def test_malformed_line_is_skipped_not_fatal(self):
        with TemporaryDirectory() as d:
            p = Path(d) / "abcd1234.jsonl"
            build_transcript(p, [{"user": "hi"}])
            with p.open("a", encoding="utf-8") as fh:
                fh.write('{"type": "assistant", "message": {broken\n')
            s = parse_session(p)
            self.assertEqual(s.user_prompts, ["hi"])

    def test_tool_input_is_truncated(self):
        secret = "x" * 5000
        s = self._parse([{"user": "go"}, {"tool": ("Write", {"file_path": secret})}])
        self.assertLess(len(s.tool_calls[0].summary), 200)


# ---------------------------------------------------------------------------
# Signals
# ---------------------------------------------------------------------------


class SignalTests(unittest.TestCase):
    def _codes(self, blocks):
        with TemporaryDirectory() as d:
            p = build_transcript(Path(d) / "abcd1234-x.jsonl", blocks)
            return {c for c, *_ in session_eval.derive_signals(parse_session(p))}

    def test_write_before_read(self):
        codes = self._codes([{"user": "go"}, {"tool": ("Edit", {"file_path": "a.py"})}])
        self.assertIn("write-before-read", codes)
        self.assertNotIn("context-gathered", codes)

    def test_context_gathered_then_verified(self):
        codes = self._codes(
            [
                {"user": "go"},
                {"tool": ("Read", {"file_path": "a.py"})},
                {"tool": ("Grep", {"pattern": "foo"})},
                {"tool": ("Edit", {"file_path": "a.py"})},
                {"tool": ("Bash", {"command": "make test"})},
            ]
        )
        self.assertIn("context-gathered", codes)
        self.assertIn("verified-mutation", codes)
        self.assertNotIn("unverified-mutation", codes)

    def test_unverified_mutation(self):
        codes = self._codes(
            [
                {"user": "go"},
                {"tool": ("Read", {"file_path": "a.py"})},
                {"tool": ("Read", {"file_path": "b.py"})},
                {"tool": ("Edit", {"file_path": "a.py"})},
            ]
        )
        self.assertIn("unverified-mutation", codes)

    def test_verify_before_the_last_mutation_does_not_count(self):
        # Ordering is the point: a test that ran and then got invalidated by a
        # later edit is not evidence the final state works.
        codes = self._codes(
            [
                {"user": "go"},
                {"tool": ("Read", {"file_path": "a.py"})},
                {"tool": ("Read", {"file_path": "b.py"})},
                {"tool": ("Edit", {"file_path": "a.py"})},
                {"tool": ("Bash", {"command": "make test"})},
                {"tool": ("Edit", {"file_path": "a.py"})},
            ]
        )
        self.assertIn("unverified-mutation", codes)

    def test_error_loop_needs_a_repeat(self):
        once = self._codes(
            [{"user": "go"}, {"tool": ("Bash", {"command": "false"}), "is_error": True}]
        )
        self.assertIn("recovered-from-error", once)
        self.assertNotIn("tool-error-loop", once)

        twice = self._codes(
            [
                {"user": "go"},
                {"tool": ("Bash", {"command": "false"}), "is_error": True},
                {"tool": ("Bash", {"command": "false"}), "is_error": True},
            ]
        )
        self.assertIn("tool-error-loop", twice)

    def test_opening_prompt_is_never_a_correction(self):
        codes = self._codes([{"user": "don't use tabs"}, {"tool": ("Read", {"file_path": "a"})}])
        self.assertNotIn("user-correction", codes)

    def test_follow_up_correction_is_caught(self):
        codes = self._codes(
            [
                {"user": "add a helper"},
                {"tool": ("Read", {"file_path": "a"})},
                {"user": "no, that's not what I asked for"},
            ]
        )
        self.assertIn("user-correction", codes)

    def test_conversational_session(self):
        codes = self._codes([{"user": "what do you think?"}, {"assistant": "I think so."}])
        self.assertIn("conversational", codes)

    def test_suggested_judgement_never_writes_judgement(self):
        with TemporaryDirectory() as d:
            p = build_transcript(
                Path(d) / "abcd1234-y.jsonl",
                [
                    {"user": "go"},
                    {"tool": ("Read", {"file_path": "a"})},
                    {"tool": ("Read", {"file_path": "b"})},
                    {"tool": ("Edit", {"file_path": "a"})},
                    {"tool": ("Bash", {"command": "make test"})},
                ],
            )
            body = session_eval.render(parse_session(p))
        self.assertIn("judgement: null", body)
        self.assertIn("suggested_judgement: looks-clean", body)
        self.assertIn("reviewed: false", body)


# ---------------------------------------------------------------------------
# Write / merge
# ---------------------------------------------------------------------------


class ReviewPreservationTests(unittest.TestCase):
    def test_regeneration_preserves_filled_review_fields(self):
        blocks = [
            {"user": "go"},
            {"tool": ("Read", {"file_path": "a"})},
            {"tool": ("Edit", {"file_path": "a"})},
        ]
        with TemporaryDirectory() as d:
            transcript = build_transcript(Path(d) / "abcd1234-z.jsonl", blocks)
            evals = Path(d) / "evals"
            original = session_eval.EVALS_DIR
            session_eval.EVALS_DIR = evals
            try:
                path, status = session_eval.write_eval(parse_session(transcript))
                self.assertEqual(status, "created")

                # A reviewer fills the record in.
                text = path.read_text(encoding="utf-8")
                text = text.replace("judgement: null", "judgement: partial", 1)
                text = text.replace("notes: null", "notes: read the diff, it was fine", 1)
                text = text.replace("reviewed: false", "reviewed: true", 1)
                path.write_text(text, encoding="utf-8")

                _, status = session_eval.write_eval(parse_session(transcript))
                after = path.read_text(encoding="utf-8")
                self.assertIn("review fields preserved", status)
                self.assertIn("judgement: partial", after)
                self.assertIn("notes: read the diff, it was fine", after)
                self.assertIn("reviewed: true", after)

                # --force is the documented escape hatch.
                session_eval.write_eval(parse_session(transcript), force=True)
                forced = path.read_text(encoding="utf-8")
                self.assertIn("judgement: null", forced)
            finally:
                session_eval.EVALS_DIR = original


if __name__ == "__main__":
    unittest.main()
