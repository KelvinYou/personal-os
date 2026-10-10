"""Synthetic review semantics: unknown evidence must never become failure or zero."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from skill_regressions import build_report


class SkillRegressionContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.corpus = self.root / "cases.json"
        self.runs = self.root / "runs"
        self.runs.mkdir()
        self.corpus.write_text(json.dumps({"schema_version": 1, "corpus_version": "test.1", "cases": [{
            "id": "fixture-case", "stage": "fixture-stage", "candidate_skills": [],
            "source": {"path": "synthetic.md", "heading": "Fixture", "status": "candidate"},
            "checks": [{"id": "content", "criterion": "Record retained"},
                       {"id": "order", "criterion": "Verified before deletion"}],
        }]}))

    def record(self, name, statuses, outcome, reviewed=True, **overrides):
        result = {
            "schema_version": 1, "run_id": name, "case_id": "fixture-case",
            "corpus_version": "test.1", "corpus_sha256": hashlib.sha256(self.corpus.read_bytes()).hexdigest(),
            "checks": [{"id": key, "status": value, "rationale": "Synthetic evidence",
                        "evidence_refs": ["fixture.txt"]} for key, value in statuses.items()],
            "reviewer": "Independent fixture reviewer" if reviewed else None,
            "reviewed_at": "2030-01-01T00:00:00Z" if reviewed else None,
            "outcome": outcome, "harness": "fixture", "model": None, "notes": None,
        }
        result.update(overrides)
        directory = self.runs / name / "with_skill"
        directory.mkdir(parents=True)
        (directory / "result.json").write_text(json.dumps(result))
        (directory / "execution.md").write_text("Synthetic completed execution fixture.\n")
        return directory

    def report(self):
        return build_report(self.corpus, self.runs)

    def test_unknown_and_unreviewed_are_separate_from_conclusive_denominator(self):
        self.record("passed", {"content": "pass", "order": "pass"}, "pass")
        self.record("failed", {"content": "fail", "order": "unobserved"}, "fail")
        self.record("unknown", {"content": "pass", "order": "unobserved"}, "inconclusive")
        self.record("pending", {}, None, reviewed=False)
        report = self.report()
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["summary"], {"runs": 4, "passed": 1, "failed": 1,
            "inconclusive": 1, "unreviewed": 1, "conclusive": 2, "pass_rate": 0.5})

    def test_partial_review_has_no_overall_pass_rate(self):
        self.record("partial", {"content": "pass"}, "inconclusive")
        self.assertIsNone(self.report()["summary"]["pass_rate"])

    def test_inconsistent_pass_is_reported_and_excluded(self):
        self.record("false-pass", {"content": "pass"}, "pass")
        report = self.report()
        self.assertEqual(report["summary"]["runs"], 0)
        self.assertIn("disagrees", report["errors"][0]["message"])

    def test_missing_reviewer_cannot_supply_grades(self):
        self.record("self-grade", {"content": "pass", "order": "pass"}, "pass", reviewed=False)
        self.assertIn("reviewer identity", self.report()["errors"][0]["message"])

    def test_mismatched_corpus_is_not_silently_compared(self):
        self.record("old", {}, None, reviewed=False, corpus_sha256="old-hash")
        self.assertIn("different corpus", self.report()["errors"][0]["message"])

    def test_evidence_symlink_cannot_escape_public_run_root(self):
        directory = self.record("safe", {}, None, reviewed=False)
        outside = self.root / "private.txt"
        outside.write_text("SECRET SYNTHETIC VALUE")
        (directory / "outputs").mkdir()
        (directory / "outputs/response.md").symlink_to(outside)
        report = self.report()
        self.assertFalse(any(doc["path"] == "outputs/response.md" for doc in report["cases"][0]["runs"][0]["documents"]))
        self.assertNotIn("SECRET SYNTHETIC VALUE", json.dumps(report))

    def test_prepared_record_is_not_counted_as_an_execution(self):
        directory = self.record("prepared", {}, None, reviewed=False)
        (directory / "execution.md").unlink()
        self.assertEqual(self.report()["summary"]["runs"], 0)


if __name__ == "__main__":
    unittest.main()
