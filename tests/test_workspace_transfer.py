"""Exercise offline transfers using synthetic Git repos; never real private data."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile

spec = importlib.util.spec_from_file_location("workspace_transfer", Path(__file__).parents[1] / "scripts/workspace_transfer.py")
transfer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transfer)


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.DEVNULL)


def init(root):
    root.mkdir(parents=True)
    git(root, "init")
    git(root, "config", "user.name", "Synthetic Test")
    git(root, "config", "user.email", "test@example.invalid")


def commit(root):
    git(root, "add", ".")
    git(root, "commit", "-m", "fixture")


class WorkspaceTransferTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.source = self.home / "source"
        self.target = self.home / "target"
        init(self.source)
        (self.source / ".gitignore").write_text("/data/\n.env\n/*.zip\n/*.zip.sha256\n")
        (self.source / "edit.txt").write_text("original\n")
        (self.source / "remove.txt").write_text("remove me\n")
        commit(self.source)
        git(self.home, "clone", str(self.source), str(self.target))
        (self.source / "edit.txt").write_text("changed\n")
        (self.source / "remove.txt").unlink()
        (self.source / "binary.bin").write_bytes(b"\x00\xff\x10")
        (self.source / "run.sh").write_text("#!/bin/sh\n")
        (self.source / "run.sh").chmod(0o755)
        (self.source / "link").symlink_to("edit.txt")
        (self.source / ".env").write_text("omitted credential")
        (self.source / "data/empty").mkdir(parents=True)
        (self.source / "data/.hidden").write_text("synthetic private")
        (self.source / "data/.git").mkdir()
        (self.source / "data/.git/config").write_text("omit metadata")
        self.archive = self.home / "transfer.zip"

    def test_round_trip_and_idempotence(self):
        transfer.export(self.source, self.archive)
        transfer.apply(self.archive, self.target)
        self.assertEqual((self.target / "edit.txt").read_text(), "original\n")
        transfer.apply(self.archive, self.target, write=True)
        self.assertEqual((self.target / "edit.txt").read_text(), "changed\n")
        self.assertFalse((self.target / "remove.txt").exists())
        self.assertEqual((self.target / "binary.bin").read_bytes(), b"\x00\xff\x10")
        self.assertTrue((self.target / "run.sh").stat().st_mode & 0o100)
        self.assertEqual(os.readlink(self.target / "link"), "edit.txt")
        self.assertTrue((self.target / "data/empty").is_dir())
        self.assertEqual((self.target / "data/.hidden").read_text(), "synthetic private")
        self.assertFalse((self.target / "data/.git").exists())
        self.assertFalse((self.target / ".env").exists())
        transfer.apply(self.archive, self.target, write=True)

    def test_conflict_refuses_all_writes(self):
        transfer.export(self.source, self.archive)
        (self.target / "edit.txt").write_text("destination work")
        with self.assertRaisesRegex(ValueError, "Conflicting"):
            transfer.apply(self.archive, self.target, write=True)
        self.assertTrue((self.target / "remove.txt").exists())
        self.assertFalse((self.target / "data").exists())

    def test_root_export_ignores_prior_archives_and_writes_checksum(self):
        (self.source / "old.zip").write_bytes(b"private previous archive")
        (self.source / "old.zip.sha256").write_text("old checksum")
        output = self.source / "transfer.zip"
        transfer.export(self.source, output)
        with zipfile.ZipFile(output) as archive:
            entries = json.loads(archive.read("manifest.json"))["entries"]
            self.assertNotIn("old.zip", entries)
            self.assertNotIn("old.zip.sha256", entries)
            self.assertNotIn("transfer.zip", entries)
            self.assertNotIn("transfer.zip.sha256", entries)
        checksum = output.with_name(output.name + ".sha256").read_text()
        self.assertEqual(checksum, transfer.hashlib.sha256(output.read_bytes()).hexdigest() + "  transfer.zip\n")
        self.assertEqual(git(self.source, "check-ignore", "transfer.zip").decode().strip(), "transfer.zip")
        with self.assertRaisesRegex(ValueError, "already exists"):
            transfer.export(self.source, output)

    def test_existing_data_requires_opt_in_and_preserves_git(self):
        transfer.export(self.source, self.archive)
        (self.target / "data/.git").mkdir(parents=True)
        (self.target / "data/.git/config").write_text("destination metadata")
        (self.target / "data/.hidden").write_text("other private")
        with self.assertRaisesRegex(ValueError, "Conflicting"):
            transfer.apply(self.archive, self.target, write=True)
        transfer.apply(self.archive, self.target, write=True, overwrite_data=True)
        self.assertEqual((self.target / "data/.git/config").read_text(), "destination metadata")

    def test_symlink_parent_is_rejected(self):
        transfer.export(self.source, self.archive)
        elsewhere = self.home / "elsewhere"
        elsewhere.mkdir()
        (self.target / "data").symlink_to(elsewhere)
        with self.assertRaisesRegex(ValueError, "Symlink parent"):
            transfer.apply(self.archive, self.target, write=True)
        self.assertFalse((elsewhere / ".hidden").exists())

    def test_child_committed_delta_and_dirty_worktree(self):
        child = self.source / "repos/child"
        init(child)
        (child / "file.txt").write_text("child base")
        commit(child)
        base = git(child, "rev-parse", "HEAD").decode().strip()
        git(self.source, "update-index", "--add", "--cacheinfo", f"160000,{base},repos/child")
        git(self.source, "commit", "-m", "child pointer")
        git(self.target, "fetch", str(self.source), "HEAD")
        git(self.target, "merge", "--ff-only", "FETCH_HEAD")
        git(self.home, "clone", str(child), str(self.target / "repos/child"))
        (child / "file.txt").write_text("committed delta")
        commit(child)
        (child / "dirty.txt").write_text("untracked child")
        transfer.export(self.source, self.archive)
        transfer.apply(self.archive, self.target, write=True)
        self.assertEqual((self.target / "repos/child/file.txt").read_text(), "committed delta")
        self.assertEqual((self.target / "repos/child/dirty.txt").read_text(), "untracked child")
        self.assertEqual(git(self.target / "repos/child", "rev-parse", "HEAD").decode().strip(), base)


if __name__ == "__main__":
    unittest.main()
