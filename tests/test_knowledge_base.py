"""Behavioural tests for the public knowledge-base interfaces."""
from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.knowledge import check_note, load_note  # noqa: E402
from kb_eval import evaluate_queries  # noqa: E402
from kb_graph import render_graph  # noqa: E402
from kb_index import search_notes  # noqa: E402


class KnowledgeNoteTests(unittest.TestCase):
    def test_valid_note_exposes_metadata_title_and_headings(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "example.md"
            path.write_text(
                "---\n"
                "type: concept\n"
                "status: active\n"
                "summary: A compact example note\n"
                "updated: 2026-09-22\n"
                "---\n\n"
                "# Example note\n\n"
                "## Answer\n\nKeep the answer small.\n",
                encoding="utf-8",
            )

            note = load_note(path)

        self.assertEqual(note.title, "Example note")
        self.assertEqual(note.metadata["type"], "concept")
        self.assertEqual(note.metadata["status"], "active")
        self.assertEqual(note.headings, ("Answer",))

    def test_checker_reports_invalid_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "broken.md"
            path.write_text(
                "---\n"
                "type: essay\n"
                "status: current\n"
                "updated: not-a-date\n"
                "---\n\n"
                "# Broken\n",
                encoding="utf-8",
            )

            issues = check_note(path, today=date(2026, 9, 22))

        self.assertEqual(
            {issue.code for issue in issues},
            {"invalid_type", "invalid_status", "missing_summary", "invalid_updated"},
        )

    def test_checker_requires_replacement_and_rejects_private_links(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            superseded = root / "superseded.md"
            superseded.write_text(
                "---\n"
                "type: reference\n"
                "status: superseded\n"
                "summary: An old note\n"
                "updated: 2026-09-22\n"
                "---\n\n"
                "# Old note\n\nNo replacement was recorded.\n",
                encoding="utf-8",
            )
            private = root / "private.md"
            private.write_text(
                "---\n"
                "type: reference\n"
                "status: active\n"
                "summary: A note with a private link\n"
                "updated: 2026-09-22\n"
                "---\n\n"
                "# Private\n\n[Profile](../../data/user_profile.md)\n",
                encoding="utf-8",
            )

            superseded_codes = {issue.code for issue in check_note(superseded)}
            private_codes = {issue.code for issue in check_note(private)}

        self.assertIn("missing_replacement", superseded_codes)
        self.assertIn("private_link", private_codes)

    def test_checker_accepts_a_resolved_markdown_heading_link(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "target.md").write_text("# Target\n\n## Section\n", encoding="utf-8")
            source = root / "source.md"
            source.write_text(
                "---\n"
                "type: reference\n"
                "status: active\n"
                "summary: A source note\n"
                "updated: 2026-09-22\n"
                "---\n\n"
                "# Source\n\n[Section](target.md#section)\n",
                encoding="utf-8",
            )

            issues = check_note(source)

        self.assertNotIn("missing_anchor", {issue.code for issue in issues})
        self.assertNotIn("broken_link", {issue.code for issue in issues})

    def test_search_ranks_matching_summary_before_unrelated_notes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            context = root / "context.md"
            context.write_text(
                "---\n"
                "type: concept\n"
                "status: active\n"
                "summary: Save tokens with a small agent context budget\n"
                "updated: 2026-09-22\n"
                "---\n\n"
                "# Agent context budget\n",
                encoding="utf-8",
            )
            unrelated = root / "unrelated.md"
            unrelated.write_text(
                "---\n"
                "type: reference\n"
                "status: active\n"
                "summary: Public and private repository boundaries\n"
                "updated: 2026-09-22\n"
                "---\n\n"
                "# Boundary\n",
                encoding="utf-8",
            )

            results = search_notes("How do agents save tokens?", [load_note(context), load_note(unrelated)], limit=1)

        self.assertEqual(results[0].note.path, context)

    def test_golden_queries_measure_route_and_hit_rates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            notes = []
            for filename, title, summary in (
                ("routing.md", "Documentation routing", "Lifecycle owners route durable docs"),
                ("budget.md", "Context budget", "Agents save tokens with small context"),
            ):
                path = root / filename
                path.write_text(
                    "---\n"
                    "type: concept\n"
                    "status: active\n"
                    f"summary: {summary}\n"
                    "updated: 2026-09-22\n"
                    "---\n\n"
                    f"# {title}\n",
                    encoding="utf-8",
                )
                notes.append(load_note(path))

            report = evaluate_queries(
                [
                    {
                        "id": "budget",
                        "query": "How do agents save tokens?",
                        "expected_paths": ["budget.md"],
                    },
                    {
                        "id": "routing",
                        "query": "Which docs have lifecycle owners?",
                        "expected_paths": ["routing.md"],
                    },
                ],
                notes,
                root=root,
            )

        self.assertEqual(report.total, 2)
        self.assertEqual(report.route_at_1, 2)
        self.assertEqual(report.hit_at_3, 2)

    def test_negative_query_passes_when_no_note_matches(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            note = root / "routing.md"
            note.write_text(
                "---\n"
                "type: concept\n"
                "status: active\n"
                "summary: Documentation lifecycle owners\n"
                "updated: 2026-09-22\n"
                "---\n\n"
                "# Documentation routing\n",
                encoding="utf-8",
            )

            report = evaluate_queries(
                [
                    {
                        "id": "unknown-domain",
                        "query": "What is the canonical moon-colony retention policy?",
                        "expected_paths": [],
                        "expect_no_match": True,
                    }
                ],
                [load_note(note)],
                root=root,
            )

        self.assertEqual(report.no_answer_total, 1)
        self.assertEqual(report.no_answer_correct, 1)
        self.assertEqual(report.misses, ())

    def test_search_abstains_on_a_low_coverage_near_miss(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            note = root / "boundary.md"
            note.write_text(
                "---\n"
                "type: reference\n"
                "status: active\n"
                "summary: Public and private boundaries for personal data\n"
                "updated: 2026-09-22\n"
                "---\n\n"
                "# Public and private boundary\n",
                encoding="utf-8",
            )

            results = search_notes(
                "What is the canonical data retention policy?",
                [load_note(note)],
                limit=3,
            )

        self.assertEqual(results, [])

    def test_answer_eval_checks_required_claims_and_citations(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            note = root / "routing.md"
            note.write_text(
                "---\n"
                "type: reference\n"
                "status: active\n"
                "summary: Documentation lifecycle owners\n"
                "updated: 2026-09-22\n"
                "---\n\n"
                "# Documentation routing\n",
                encoding="utf-8",
            )

            report = evaluate_queries(
                [
                    {
                        "id": "routing-answer",
                        "query": "Who owns documentation routing?",
                        "expected_paths": ["routing.md"],
                        "answer": (
                            "Use the lifecycle owners and read the smallest authoritative section. "
                            "See [routing.md](routing.md)."
                        ),
                        "required_claims": [
                            "lifecycle owners",
                            "smallest authoritative section",
                        ],
                        "required_citations": ["routing.md"],
                        "scope": ["routing.md"],
                    }
                ],
                [load_note(note)],
                root=root,
            )

        self.assertEqual(report.answer_total, 1)
        self.assertEqual(report.answer_passed, 1)
        self.assertEqual(report.claim_total, 2)
        self.assertEqual(report.claim_passed, 2)
        self.assertEqual(report.citation_total, 1)
        self.assertEqual(report.citation_passed, 1)
        self.assertEqual(report.answer_misses, ())

    def test_answer_eval_reports_missing_claims_and_out_of_scope_citations(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            note = root / "routing.md"
            note.write_text(
                "---\n"
                "type: reference\n"
                "status: active\n"
                "summary: Documentation lifecycle owners\n"
                "updated: 2026-09-22\n"
                "---\n\n"
                "# Documentation routing\n",
                encoding="utf-8",
            )

            report = evaluate_queries(
                [
                    {
                        "id": "routing-answer-miss",
                        "query": "Who owns documentation routing?",
                        "expected_paths": ["routing.md"],
                        "answer": "Use the lifecycle owners. See [routing.md](routing.md) and [other.md](other.md).",
                        "required_claims": ["smallest authoritative section"],
                        "required_citations": ["routing.md"],
                        "scope": ["routing.md"],
                    }
                ],
                [load_note(note)],
                root=root,
            )

        self.assertEqual(report.answer_total, 1)
        self.assertEqual(report.answer_passed, 0)
        self.assertEqual(report.claim_passed, 0)
        self.assertEqual(report.citation_passed, 1)
        self.assertEqual(report.answer_misses[0]["missing_claims"], ["smallest authoritative section"])
        self.assertEqual(report.answer_misses[0]["out_of_scope"], ["other.md"])

    def test_eval_rejects_malformed_expected_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            note = root / "routing.md"
            note.write_text(
                "---\n"
                "type: reference\n"
                "status: active\n"
                "summary: Documentation lifecycle owners\n"
                "updated: 2026-09-22\n"
                "---\n\n"
                "# Documentation routing\n",
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                evaluate_queries(
                    [
                        {
                            "id": "malformed",
                            "query": "Who owns documentation routing?",
                            "expected_paths": "routing.md",
                        }
                    ],
                    [load_note(note)],
                    root=root,
                )

    def test_search_avoids_superseded_notes_by_default(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            notes = []
            for filename, status in (("current.md", "active"), ("old.md", "superseded")):
                path = root / filename
                path.write_text(
                    "---\n"
                    "type: concept\n"
                    f"status: {status}\n"
                    "summary: The same retrieval concept\n"
                    "updated: 2026-09-22\n"
                    "---\n\n"
                    "# Retrieval concept\n",
                    encoding="utf-8",
                )
                notes.append(load_note(path))

            results = search_notes("retrieval concept", notes, limit=3)

        self.assertEqual([result.note.path.name for result in results], ["current.md"])

    def test_graph_is_deterministic_and_portable_mermaid(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.md"
            target = root / "target.md"
            for path, title, body in (
                (source, "Source", "[Target](target.md)"),
                (target, "Target", "A stable concept."),
            ):
                path.write_text(
                    "---\n"
                    "type: reference\n"
                    "status: active\n"
                    f"summary: {title} summary\n"
                    "updated: 2026-09-22\n"
                    "---\n\n"
                    f"# {title}\n\n{body}\n",
                    encoding="utf-8",
                )

            notes = [load_note(source), load_note(target)]
            first = render_graph(notes, root=root)
            second = render_graph(notes, root=root)

        self.assertEqual(first, second)
        self.assertIn("graph LR", first)
        self.assertIn("classDef note", first)
        self.assertIn("classDef owner", first)
        self.assertIn("-->", first)
        self.assertNotIn(r"\n", first)


if __name__ == "__main__":
    unittest.main()
