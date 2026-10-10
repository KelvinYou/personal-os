from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import doctor  # noqa: E402


class NutritionParityTests(unittest.TestCase):
    def test_absent_notes_is_expected(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(doctor, "ROOT", Path(tmp)):
            report = doctor.Report()
            doctor.check_nutrition_fields(report)
            self.assertEqual(report.rows[0][0], "expected")

    def test_present_drift_is_error(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(doctor, "ROOT", Path(tmp)):
            schema = Path(tmp) / "repos/notes/datasets/nutrition/schema.yaml"
            schema.parent.mkdir(parents=True)
            schema.write_text("food:\n  micronutrient_fields: [iron_mg]\n")
            report = doctor.Report()
            doctor.check_nutrition_fields(report)
            self.assertEqual(report.rows[0][0], "error")


if __name__ == "__main__":
    unittest.main()
