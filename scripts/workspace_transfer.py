#!/usr/bin/env python3
"""Offline working-tree transfer, including private data; Python standard library only."""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import tempfile
import zipfile


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args])


def fingerprint(content, kind, mode):
    return {"sha256": hashlib.sha256(content).hexdigest(), "kind": kind, "mode": mode}


def snapshot(path):
    if path.is_symlink():
        content = os.fsencode(os.readlink(path))
        return fingerprint(content, "symlink", 0o777), content
    if not path.exists():
        return None, b""
    if not path.is_file():
        raise ValueError(f"Not a regular file: {path}")
    content = path.read_bytes()
    mode = 0o755 if path.stat().st_mode & stat.S_IXUSR else 0o644
    return fingerprint(content, "file", mode), content


def safe_path(root, name):
    parts = PurePosixPath(name).parts
    if not parts or name.startswith("/") or any(p in ("..", ".git") for p in parts):
        raise ValueError(f"Unsafe archive path: {name}")
    path = root.joinpath(*parts)
    for parent in path.parents:
        if parent == root:
            break
        if parent.is_symlink():
            raise ValueError(f"Symlink parent: {parent}")
    return path


def export(root, output):
    root = root.resolve()
    output = output.absolute()
    checksum_path = output.with_name(output.name + ".sha256")
    if output.resolve().is_relative_to(root):
        relative = output.resolve().relative_to(root).as_posix()
        ignored = subprocess.run(["git", "-C", str(root), "check-ignore", "--quiet", "--", relative])
        if ignored.returncode != 0:
            raise ValueError("A ZIP inside the checkout must be ignored by Git; root *.zip files are supported.")
    if output.exists() or output.is_symlink() or checksum_path.exists() or checksum_path.is_symlink():
        raise ValueError(f"Output already exists: {output}")
    head = git(root, "rev-parse", "HEAD").decode().strip()
    repos = [{"path": ".", "base": head, "head": head}]
    root_tree = git(root, "ls-tree", "-rz", head).split(b"\0")
    for line in root_tree:
        if line.startswith(b"160000 "):
            meta, name = line.split(b"\t", 1)
            rel = os.fsdecode(name)
            child = root / rel
            if git(child, "rev-parse", "--show-toplevel").decode().strip() != str(child.resolve()):
                raise ValueError(f"Initialize submodule before export: {rel}")
            repos.append({"path": rel, "base": meta.split()[2].decode(),
                          "head": git(child, "rev-parse", "HEAD").decode().strip()})
    entries, payload = {}, {}
    for repo in repos:
        location = root / repo["path"]
        tree = {}
        for line in git(location, "ls-tree", "-rz", repo["base"]).split(b"\0"):
            if line:
                meta, name = line.split(b"\t", 1)
                tree[os.fsdecode(name)] = meta.split()
        changed = git(location, "diff", "--name-only", "-z", repo["base"], "--").split(b"\0")
        untracked = git(location, "ls-files", "--others", "--exclude-standard", "-z").split(b"\0")
        for raw in set(changed + untracked) - {b""}:
            name = os.fsdecode(raw)
            old = tree.get(name)
            if old and old[0] == b"160000":
                continue
            full = str(PurePosixPath(repo["path"]) / name)
            if full.startswith("data/"):
                continue
            before = None
            if old:
                content = git(location, "cat-file", "blob", old[2].decode())
                before = fingerprint(content, "symlink" if old[0] == b"120000" else "file",
                                     0o777 if old[0] == b"120000" else int(old[0], 8) & 0o777)
            after, content = snapshot(safe_path(root, full))
            entries[full] = {"before": before, "after": after}
            if after:
                payload[full] = content
    data = root / "data"
    if not data.is_dir() or data.is_symlink():
        raise ValueError("A real data/ directory is required for the complete private snapshot.")
    directories = ["data"]
    for parent, dirs, files in os.walk(data, followlinks=False):
        dirs[:] = [d for d in dirs if d != ".git"]
        for name in files + [d for d in dirs if (Path(parent) / d).is_symlink()]:
            if name == ".git":
                continue
            path = Path(parent) / name
            if path.absolute() in (output, checksum_path):
                continue
            full = path.relative_to(root).as_posix()
            after, content = snapshot(path)
            entries[full] = {"before": None, "after": after}
            payload[full] = content
        directories.extend((Path(parent) / d).relative_to(root).as_posix()
                           for d in dirs if not (Path(parent) / d).is_symlink())
    manifest = {"version": 1, "repos": repos, "directories": sorted(directories),
                "entries": dict(sorted(entries.items()))}
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=output.parent, suffix=".zip")
    os.close(fd)
    try:
        with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("manifest.json", json.dumps(manifest, indent=2))
            archive.writestr("workspace_transfer.py", Path(__file__).read_bytes())
            archive.writestr("README.md", INSTRUCTIONS)
            for name, content in sorted(payload.items()):
                archive.writestr("payload/" + name, content)
        os.replace(temporary, output)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    checksum_path.write_text(hashlib.sha256(output.read_bytes()).hexdigest() + "  " + output.name + "\n")
    print(f"Created {output}: {len(entries)} file operations; full data snapshot included.")
    print(f"Checksum: {checksum_path}")


def apply(archive_path, target, write=False, overwrite_data=False):
    target = target.resolve()
    with zipfile.ZipFile(archive_path) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        if manifest["version"] != 1:
            raise ValueError("Unsupported transfer version")
        for repo in manifest["repos"]:
            location = target if repo["path"] == "." else safe_path(target, repo["path"])
            if git(location, "rev-parse", "--show-toplevel").decode().strip() != str(location):
                raise ValueError(f"Initialize target repository: {location}")
        operations, conflicts = [], []
        for name, entry in manifest["entries"].items():
            path = safe_path(target, name)
            current, old_content = snapshot(path)
            after = entry["after"]
            content = archive.read("payload/" + name) if after else b""
            if after and fingerprint(content, after["kind"], after["mode"]) != after:
                raise ValueError(f"Payload checksum mismatch: {name}")
            if current == after:
                continue
            if current != entry["before"] and not (name.startswith("data/") and overwrite_data):
                conflicts.append(name)
            operations.append((path, name, current, old_content, after, content))
        for name in manifest["directories"]:
            path = safe_path(target, name)
            if path.is_symlink() or (path.exists() and not path.is_dir()):
                conflicts.append(name)
        if conflicts:
            raise ValueError("Conflicting destination files (no changes applied):\n" + "\n".join(conflicts))
        print(f"{'Apply' if write else 'Preview'}: {len(operations)} file operations; {len(manifest['directories'])} data directories.")
        if not write:
            print("Re-run with --write to apply. Different existing data requires --overwrite-data.")
            return
        fd, backup = tempfile.mkstemp(prefix="personal-os-before-transfer-", suffix=".zip")
        os.close(fd)
        with zipfile.ZipFile(backup, "w", zipfile.ZIP_DEFLATED) as saved:
            saved.writestr("manifest.json", json.dumps({name: before for _, name, before, _, _, _ in operations}, indent=2))
            for _, name, before, old_content, _, _ in operations:
                if before:
                    saved.writestr("payload/" + name, old_content)
        print(f"Before-image backup: {backup}")
        for name in manifest["directories"]:
            safe_path(target, name).mkdir(parents=True, exist_ok=True)
        for path, _, _, _, after, content in operations:
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.is_symlink() or path.exists():
                path.unlink()
            if after:
                if after["kind"] == "symlink":
                    path.symlink_to(os.fsdecode(content))
                else:
                    path.write_bytes(content)
                    path.chmod(after["mode"])
        print("Applied working-tree files; Git indexes, HEADs and history were not changed.")


INSTRUCTIONS = """# Private workspace transfer

This ZIP contains private data. Root *.zip and *.zip.sha256 files are ignored
by Git; keep them untracked. Export without an output argument creates a dated
archive in the project root and writes a companion SHA-256 checksum file.
Extract to a separate folder, not directly over your checkout. Initialize the
destination's public submodules first. Python 3.11+ and Git are required.

```bash
python3 workspace_transfer.py apply /path/to/transfer.zip --target /path/to/personal-os
python3 workspace_transfer.py apply /path/to/transfer.zip --target /path/to/personal-os --write
```

The first command previews and checks conflicts. If existing data differs,
review it and add --overwrite-data to both commands to replace snapshot files.
Extra destination data files are retained. A private before-image ZIP is saved
to the system temporary directory before writing; its manifest records absent
paths, modes and symlink targets as well as saved file content.

manifest.json records repository base/source commits and SHA-256 checksums.
Public submodule changes include committed differences from the parent's
recorded gitlink, flattened into working-tree changes. No commit history,
staging split or parent gitlink update is restored. Destination files must match
their base content (or already match the exported content); otherwise the
entire preflight refuses to write. Deletions, executable modes, binary files,
symlinks, untracked nonignored files and empty data directories are supported.
All data files including hidden/ignored data are included, except .git metadata.
Ignored files elsewhere, credentials, environments and build caches are omitted.
Existing private Git metadata is preserved; a restored plain data directory is
not automatically attached as a private repository. Follow SETUP.md Phase 2
before using features that require an attached private repository.
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    out = sub.add_parser("export")
    out.add_argument("output", type=Path, nargs="?", help="ZIP path; defaults to a dated ZIP in the project root")
    out.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    incoming = sub.add_parser("apply")
    incoming.add_argument("archive", type=Path)
    incoming.add_argument("--target", type=Path, required=True)
    incoming.add_argument("--write", action="store_true")
    incoming.add_argument("--overwrite-data", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "export":
            output = args.output or args.root / f"personal-os-transfer-{datetime.now():%Y%m%d-%H%M%S}.zip"
            export(args.root, output)
        else:
            apply(args.archive, args.target, args.write, args.overwrite_data)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Error: {error}\n")


if __name__ == "__main__":
    main()
