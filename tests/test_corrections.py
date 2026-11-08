"""Correction-queue recurrence parsing (scripts/lib/corrections.py). Synthetic text only."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from lib.corrections import load_entries, parse_entries, recurrence_by_month  # noqa: E402

ARCHIVE = """# archive

## 2026-10-04 — First styling miss

**Class:** `design-bypass`

## 2026-09-29 — Older one-off

**Class:** `one-off`
"""

PENDING = """# pending

<!-- Template:

## YYYY-MM-DD — <summary>

**Class:** `<slug>`
-->

## 2026-10-27 — Styling miss again

**Class:** `design-bypass`

**What I did:** mentions **Class:** `ignored` only at line start counts? no — this is mid-line.

## 2026-11-05 — Not yet classified

**What I did:** something
"""


class CorrectionRecurrenceTests(unittest.TestCase):
    def test_template_comment_is_not_an_entry(self):
        titles = [e.title for e in parse_entries(PENDING, "pending.md")]
        self.assertEqual(titles, ["Styling miss again", "Not yet classified"])

    def test_class_read_per_entry_and_missing_class_is_none(self):
        entries = parse_entries(PENDING, "pending.md")
        self.assertEqual([e.cls for e in entries], ["design-bypass", None])

    def test_repeat_counts_across_files_in_date_order(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "archive.md").write_text(ARCHIVE, encoding="utf-8")
            Path(d, "pending.md").write_text(PENDING, encoding="utf-8")
            rows = {r["month"]: r for r in recurrence_by_month(load_entries(Path(d)))}
        self.assertEqual(rows["2026-09"]["repeats"], 0)
        oct_ = rows["2026-10"]
        self.assertEqual((oct_["logged"], oct_["repeats"]), (2, 1))
        self.assertEqual(oct_["repeat_entries"][0]["title"], "Styling miss again")
        self.assertEqual(oct_["repeat_rate_pct"], 50.0)
        nov = rows["2026-11"]
        self.assertEqual((nov["logged"], nov["unclassified"], nov["repeats"]), (1, 1, 0))
        self.assertIsNone(nov["repeat_rate_pct"])

    def test_missing_directory_yields_no_rows(self):
        self.assertEqual(recurrence_by_month(load_entries(Path("/nonexistent-corrections"))), [])


if __name__ == "__main__":
    unittest.main()
