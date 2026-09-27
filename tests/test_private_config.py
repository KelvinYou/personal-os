"""Fork setup must reject unreviewed examples and preserve existing private files."""
from __future__ import annotations

import sys
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.clock import user_timezone  # noqa: E402
from lib.config import load_thresholds  # noqa: E402
import lib.config as private_config  # noqa: E402
import setup_private  # noqa: E402


class PrivateConfigTests(unittest.TestCase):
    def test_missing_private_thresholds_never_fall_back_to_public_example(self):
        with TemporaryDirectory() as tmp:
            with patch.dict("os.environ", {}, clear=True), patch.object(private_config, "DEFAULT_PATH", Path(tmp) / "missing.yaml"):
                with self.assertRaisesRegex(FileNotFoundError, "Private thresholds missing"):
                    load_thresholds()

    def test_unreviewed_threshold_example_is_refused(self):
        with self.assertRaisesRegex(ValueError, "owner_configured"):
            load_thresholds(ROOT / "templates" / "thresholds.example.yaml")

    def test_unreviewed_timezone_example_is_refused(self):
        with self.assertRaisesRegex(ValueError, "owner_configured"):
            user_timezone(ROOT / "templates" / "settings.example.yaml")

    def test_explicit_timezone_is_used(self):
        with TemporaryDirectory() as tmp:
            file = Path(tmp) / "settings.yaml"
            file.write_text("timezone: America/New_York\nowner_configured: true\n", encoding="utf-8")
            self.assertEqual(user_timezone(file).key, "America/New_York")

    def test_setup_refuses_to_overwrite_an_existing_data_directory(self):
        with TemporaryDirectory() as tmp:
            data = Path(tmp) / "data"
            data.mkdir()
            personal_file = data / "daily.md"
            personal_file.write_text("keep me", encoding="utf-8")
            with patch.object(setup_private, "DATA", data), patch.object(sys, "argv", ["setup_private", "--repo", "unused"]):
                with self.assertRaisesRegex(SystemExit, "Nothing was changed"):
                    setup_private.main()
            self.assertEqual(personal_file.read_text(encoding="utf-8"), "keep me")

    def test_setup_clones_own_repo_and_seeds_unreviewed_config(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            remote = root / "owner.git"
            data = root / "data"
            subprocess.run(["git", "init", "--bare", "--quiet", str(remote)], check=True)
            with patch.object(setup_private, "DATA", data), patch.object(sys, "argv", ["setup_private", "--repo", str(remote)]):
                self.assertEqual(setup_private.main(), 0)
            self.assertTrue((data / ".git").is_dir())
            self.assertTrue((data / "daily").is_dir())
            self.assertIn("TODO:", (data / "user_profile.md").read_text(encoding="utf-8"))
            with self.assertRaisesRegex(ValueError, "owner_configured"):
                load_thresholds(data / "config" / "thresholds.yaml")


if __name__ == "__main__":
    unittest.main()
