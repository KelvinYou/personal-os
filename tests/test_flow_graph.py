"""Tests for scripts/lib/flows/ — the /flows dashboard's extraction pipeline.

Fixtures here are synthetic Makefile/script snippets, not the real repo
layout: these tests pin down the parsing/heuristic *rules*, independent of
however many targets or scripts the real Makefile/scripts/ happen to have
today (that end-to-end shape is exercised by `make flows` itself).
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.flows import compute_ranks, parse_makefile, read_flow_group  # noqa: E402
from lib.flows.path_scanner import scan_script  # noqa: E402


class MakefileParserTests(unittest.TestCase):
    def _parse(self, text: str):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "Makefile"
            path.write_text(text, encoding="utf-8")
            return parse_makefile(path)

    def test_target_becomes_node(self):
        nodes, _ = self._parse("lint:\n\t@echo lint\n")
        self.assertIn({"id": "make:lint", "label": "lint", "kind": "make-target", "meta": {}}, nodes)

    def test_dependency_becomes_edge(self):
        nodes, edges = self._parse("lint:\n\t@echo lint\ncheck:\n\t@echo check\nreport: lint check\n\t@echo done\n")
        self.assertIn({"from": "make:report", "to": "make:lint", "kind": "depends-on"}, edges)
        self.assertIn({"from": "make:report", "to": "make:check", "kind": "depends-on"}, edges)

    def test_variable_assignment_is_not_a_target(self):
        nodes, _ = self._parse("PYTHON := .venv/bin/python3\ncheck:\n\t@$(PYTHON) foo.py\n")
        ids = {n["id"] for n in nodes}
        self.assertNotIn("make:PYTHON", ids)
        self.assertIn("make:check", ids)

    def test_recipe_invoking_script_becomes_edge(self):
        _, edges = self._parse("SCRIPTS_DIR := scripts\ncheck:\n\t@$(PYTHON) $(SCRIPTS_DIR)/report_gen.py\n")
        self.assertIn({"from": "make:check", "to": "script:report_gen.py", "kind": "invokes"}, edges)

    def test_submake_invocation_becomes_edge(self):
        _, edges = self._parse(
            "doctor:\n\t@echo doctor\nweb:\n\t@$(MAKE) --no-print-directory doctor-web\ndoctor-web:\n\t@echo x\n"
        )
        self.assertIn({"from": "make:web", "to": "make:doctor-web", "kind": "invokes"}, edges)


class AnnotationTests(unittest.TestCase):
    def test_reads_flow_header(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "script.py"
            path.write_text('#!/usr/bin/env python3\n# flow: weekly-report\n"""doc"""\n', encoding="utf-8")
            self.assertEqual(read_flow_group(path), "weekly-report")

    def test_no_header_returns_none(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "script.py"
            path.write_text("#!/usr/bin/env python3\n\"\"\"doc\"\"\"\n", encoding="utf-8")
            self.assertIsNone(read_flow_group(path))


class PathScannerTests(unittest.TestCase):
    KNOWN_DIRS = ["/data/daily/", "/data/reports/", "/config/"]

    def _scan(self, source: str):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "s.py"
            path.write_text(source, encoding="utf-8")
            return scan_script(path, "s.py", self.KNOWN_DIRS)

    ROOT_DEF = "ROOT = Path(__file__).resolve().parent.parent\n"

    def test_module_level_constant_read(self):
        edges, unresolved = self._scan(
            "from pathlib import Path\n"
            + self.ROOT_DEF
            + "DAILY_DIR = ROOT / 'data' / 'daily'\n"
            "def f():\n"
            "    return open(DAILY_DIR / 'x.md').read()\n"
        )
        self.assertIn({"from": "script:s.py", "to": "path:/data/daily/", "kind": "reads"}, edges)
        self.assertEqual(unresolved, [])

    def test_local_variable_write(self):
        edges, _ = self._scan(
            "from pathlib import Path\n"
            + self.ROOT_DEF
            + "REPORTS_DIR = ROOT / 'data' / 'reports'\n"
            "def f(name):\n"
            "    out_path = REPORTS_DIR / name\n"
            "    out_path.write_text('x', encoding='utf-8')\n"
        )
        self.assertIn({"from": "script:s.py", "to": "path:/data/reports/", "kind": "writes"}, edges)

    def test_open_write_mode(self):
        edges, _ = self._scan(
            "from pathlib import Path\n"
            + self.ROOT_DEF
            + "CFG = ROOT / 'config'\n"
            "def f():\n"
            "    with open(CFG / 'x.yaml', 'w') as fh:\n"
            "        fh.write('x')\n"
        )
        self.assertIn({"from": "script:s.py", "to": "path:/config/", "kind": "writes"}, edges)

    def test_self_referential_accumulator_does_not_hang_or_misresolve(self):
        """Regression: `cur = cur / seg` must not be treated as a path
        constant — resolving it against itself repeatedly is what caused an
        earlier version of the resolver to loop forever."""
        edges, unresolved = self._scan(
            "cur = None\n"
            "for seg in ['a', 'b']:\n"
            "    cur = cur / seg\n"
        )
        self.assertEqual(edges, [])

    def test_untracked_path_is_ignored_not_unresolved(self):
        edges, unresolved = self._scan("open('/etc/hosts')\n")
        self.assertEqual(edges, [])
        self.assertEqual(unresolved, [])

    def test_tracked_but_unmapped_dir_is_reported_unresolved(self):
        edges, unresolved = self._scan(
            "from pathlib import Path\n"
            "def f(x):\n"
            "    return open(Path('data') / x).read()\n"
        )
        self.assertEqual(edges, [])
        self.assertEqual(len(unresolved), 1)


class RankTests(unittest.TestCase):
    def test_dependency_ranked_before_target(self):
        nodes = [{"id": "make:a"}, {"id": "make:b"}]
        edges = [{"from": "make:b", "to": "make:a", "kind": "depends-on"}]
        ranks = compute_ranks(nodes, edges)
        self.assertLess(ranks["make:a"], ranks["make:b"])

    def test_write_ranked_after_script(self):
        nodes = [{"id": "script:s.py"}, {"id": "path:/data/"}]
        edges = [{"from": "script:s.py", "to": "path:/data/", "kind": "writes"}]
        ranks = compute_ranks(nodes, edges)
        self.assertLess(ranks["script:s.py"], ranks["path:/data/"])

    def test_read_and_write_same_path_does_not_blow_up_ranks(self):
        """Regression: a script that both reads and writes the same path
        (e.g. archive.py on data/archive/) creates a 2-cycle — `reads` says
        path precedes script, `writes` says script precedes path. An earlier
        version treated the iteration cap as a safety net for this, but a
        real cycle never settles and just grows every pass instead."""
        nodes = [{"id": "script:archive.py"}, {"id": "path:/data/archive/"}]
        edges = [
            {"from": "script:archive.py", "to": "path:/data/archive/", "kind": "reads"},
            {"from": "script:archive.py", "to": "path:/data/archive/", "kind": "writes"},
        ]
        ranks = compute_ranks(nodes, edges)
        self.assertLessEqual(max(ranks.values()), 1)


if __name__ == "__main__":
    unittest.main()
