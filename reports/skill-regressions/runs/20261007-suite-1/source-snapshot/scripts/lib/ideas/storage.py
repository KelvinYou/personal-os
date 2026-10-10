"""Human-readable, append-only storage for private idea evaluation state."""
from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import Any

import yaml

from .canonical import sha256_hex
from .models import (
    EvaluationInput,
    EvidenceItem,
    RunArtifact,
    TestConfirmation,
    TestResult,
)


class StorageError(ValueError):
    """Raised when a private idea artifact cannot be safely written or read."""


_SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_RUN_ID = re.compile(r"^run-[0-9a-f]{32}$")
_EVENT_TYPE = re.compile(r"^[a-z][a-z0-9-]*$")


def _yaml(value: Any) -> str:
    return yaml.safe_dump(
        value,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )


def _frontmatter(text: str, path: Path) -> dict[str, Any]:
    if not text.startswith("---\n"):
        raise StorageError(f"{path}: missing YAML frontmatter")
    parts = text.split("\n---\n", 1)
    if len(parts) != 2:
        raise StorageError(f"{path}: malformed YAML frontmatter")
    try:
        value = yaml.safe_load(parts[0][4:]) or {}
    except yaml.YAMLError as exc:
        raise StorageError(f"{path}: invalid YAML frontmatter: {exc}") from exc
    if not isinstance(value, dict):
        raise StorageError(f"{path}: frontmatter must be a mapping")
    return value


def _drop_keys(value: Any, keys: set[str]) -> Any:
    if isinstance(value, dict):
        return {
            key: _drop_keys(item, keys)
            for key, item in value.items()
            if key not in keys
        }
    if isinstance(value, list):
        return [_drop_keys(item, keys) for item in value]
    return value


def _validate_test_event(event: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize the typed payload stored in tests.md."""
    if not isinstance(event, dict):
        raise StorageError("test event must be a mapping")
    event_type = event.get("event_type")
    if not isinstance(event_type, str) or not _EVENT_TYPE.fullmatch(event_type):
        raise StorageError(f"unsafe test event type: {event_type!r}")
    payload = dict(event)
    payload.pop("event_type", None)
    try:
        if event_type == "confirmation":
            validated = TestConfirmation.model_validate(payload)
        elif event_type == "result":
            validated = TestResult.model_validate(payload)
        else:
            raise StorageError(f"unsupported test event type: {event_type!r}")
    except StorageError:
        raise
    except Exception as exc:
        raise StorageError(f"invalid {event_type} test event: {exc}") from exc
    return {"event_type": event_type, **validated.model_dump(mode="json")}


class IdeaStore:
    """Store idea records below one explicitly supplied root directory."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def _idea_dir(self, idea_id: str, *, create: bool = False) -> Path:
        if not _SAFE_ID.fullmatch(idea_id):
            raise StorageError(f"unsafe idea_id: {idea_id!r}")
        if create:
            self.root.mkdir(parents=True, exist_ok=True)
        root = self.root.resolve()
        raw_path = root / idea_id
        if raw_path.is_symlink():
            raise StorageError(f"idea directory is a symlink: {raw_path}")
        path = raw_path.resolve(strict=False)
        if path.parent != root:
            raise StorageError("idea path escapes the configured private root")
        if path.exists() and not path.is_dir():
            raise StorageError(f"idea path is not a directory: {path}")
        if create:
            path.mkdir(parents=False, exist_ok=True)
        return path

    @staticmethod
    def _file(idea_dir: Path, name: str) -> Path:
        path = idea_dir / name
        if path.is_symlink():
            raise StorageError(f"private artifact is a symlink: {path}")
        return path

    @staticmethod
    def _runs_dir(idea_dir: Path, *, create: bool = False) -> Path:
        path = idea_dir / "runs"
        if path.is_symlink():
            raise StorageError(f"runs directory is a symlink: {path}")
        if path.exists() and not path.is_dir():
            raise StorageError(f"runs path is not a directory: {path}")
        if create:
            path.mkdir(exist_ok=True)
        return path

    def save_input(self, input_: EvaluationInput) -> Path:
        """Create the initial brief/evidence files; never overwrite them."""
        try:
            input_ = EvaluationInput.model_validate(input_)
        except Exception as exc:
            raise StorageError(f"invalid idea input: {exc}") from exc
        idea_dir = self._idea_dir(input_.idea_id, create=True)
        brief_path = self._file(idea_dir, "brief.md")
        evidence_path = self._file(idea_dir, "evidence.yaml")
        tests_path = self._file(idea_dir, "tests.md")
        if brief_path.exists() or evidence_path.exists():
            raise StorageError(
                f"idea {input_.idea_id} already exists; use append_evidence for new evidence"
            )

        brief = input_.model_dump(mode="json", exclude={"evidence"})
        brief_text = "---\n" + _yaml(brief) + "---\n\n"
        brief_text += f"# {input_.idea_id}\n\nPrivate idea brief. Edit the structured frontmatter before a new run.\n"
        evidence = {
            "schema_version": "1",
            "evidence": [item.model_dump(mode="json") for item in input_.evidence],
        }
        self._write_new(brief_path, brief_text)
        self._write_new(evidence_path, _yaml(evidence))
        if not tests_path.exists():
            self._atomic_write(tests_path, "# Test events\n\n")
        return idea_dir

    def load_input(self, idea_id: str) -> EvaluationInput:
        idea_dir = self._idea_dir(idea_id)
        brief_path = self._file(idea_dir, "brief.md")
        evidence_path = self._file(idea_dir, "evidence.yaml")
        if not brief_path.is_file() or not evidence_path.is_file():
            raise StorageError(f"idea {idea_id} is missing brief.md or evidence.yaml")
        brief = _frontmatter(brief_path.read_text(encoding="utf-8"), brief_path)
        if brief.get("idea_id") != idea_id:
            raise StorageError("idea identity does not match its private brief path")
        try:
            evidence_doc = yaml.safe_load(evidence_path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            raise StorageError(f"{evidence_path}: invalid YAML: {exc}") from exc
        if not isinstance(evidence_doc, dict) or not isinstance(evidence_doc.get("evidence"), list):
            raise StorageError(f"{evidence_path}: expected an evidence list")
        brief["evidence"] = evidence_doc["evidence"]
        try:
            return EvaluationInput.model_validate(brief)
        except Exception as exc:
            raise StorageError(f"{brief_path}: invalid idea input: {exc}") from exc

    def append_evidence(self, idea_id: str, items: list[dict[str, Any]]) -> None:
        """Append new evidence items while keeping prior observations immutable."""
        if not items:
            raise StorageError("at least one evidence item is required")
        idea_dir = self._idea_dir(idea_id)
        path = self._file(idea_dir, "evidence.yaml")
        if not path.is_file():
            raise StorageError(f"idea {idea_id} has no evidence.yaml")
        try:
            document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            raise StorageError(f"{path}: invalid YAML: {exc}") from exc
        existing = document.get("evidence") if isinstance(document, dict) else None
        if not isinstance(existing, list):
            raise StorageError(f"{path}: expected an evidence list")
        existing_ids = {item.get("evidence_id") for item in existing if isinstance(item, dict)}
        try:
            existing_items = {
                item.evidence_id: item for item in
                [EvidenceItem.model_validate(item) for item in existing]
            }
        except Exception as exc:
            raise StorageError(f"existing evidence is invalid: {exc}") from exc
        try:
            validated_items = [EvidenceItem.model_validate(item) for item in items]
        except Exception as exc:
            raise StorageError(f"new evidence is invalid: {exc}") from exc
        new_ids = [item.evidence_id for item in validated_items]
        if len(set(new_ids)) != len(new_ids):
            raise StorageError("new evidence items require unique evidence_id values")
        duplicates = sorted(set(new_ids) & existing_ids)
        if duplicates:
            raise StorageError(f"evidence IDs already exist: {', '.join(duplicates)}")
        for item in validated_items:
            if item.supersedes_evidence_id is None:
                existing_items[item.evidence_id] = item
                continue
            previous = existing_items.get(item.supersedes_evidence_id)
            if previous is None:
                raise StorageError(
                    f"evidence {item.evidence_id} supersedes unknown evidence "
                    f"{item.supersedes_evidence_id}"
                )
            if previous.retrieved_at >= item.retrieved_at:
                raise StorageError(
                    f"evidence {item.evidence_id} must supersede an older evidence item"
                )
            existing_items[item.evidence_id] = item
        document["evidence"] = existing + [
            item.model_dump(mode="json") for item in validated_items
        ]
        self._atomic_write(path, _yaml(document))

    def append_test_event(self, idea_id: str, event: dict[str, Any]) -> None:
        normalized = _validate_test_event(event)
        idea_dir = self._idea_dir(idea_id)
        path = self._file(idea_dir, "tests.md")
        if not path.exists():
            self._atomic_write(path, "# Test events\n\n")
        current = path.read_text(encoding="utf-8")
        event_type = normalized["event_type"]
        timestamp = str(
            normalized.get("recorded_at")
            or normalized.get("confirmed_at")
            or "unknown"
        )
        if "\n" in timestamp or "\r" in timestamp:
            raise StorageError("test event timestamp must be a single line")
        block = f"## {event_type} — {timestamp}\n\n````yaml\n{_yaml(normalized)}````\n\n"
        self._atomic_write(path, current + block)

    def load_run(self, idea_id: str, run_id: str) -> RunArtifact:
        if not _RUN_ID.fullmatch(run_id):
            raise StorageError(f"unsafe run_id: {run_id!r}")
        idea_dir = self._idea_dir(idea_id)
        path = self._file(self._runs_dir(idea_dir), f"{run_id}.md")
        if not path.is_file():
            raise StorageError(f"run does not exist: {path}")
        try:
            content = path.read_text(encoding="utf-8")
            payload = _frontmatter(content, path)
            artifact = RunArtifact.model_validate(payload)
            if artifact.idea_id != idea_id or artifact.run_id != run_id:
                raise StorageError("run identity does not match its requested path")
            model_payload = artifact.model_dump(
                mode="json", exclude={"integrity_hash"}
            )
            raw_payload = dict(payload)
            raw_payload.pop("integrity_hash", None)
            legacy_payload = _drop_keys(
                model_payload,
                {
                    "model_excerpt_or_observation",
                    "proposed_priority",
                    "supersedes_test_id",
                    "debate",
                },
            )
            valid_hashes = {
                sha256_hex(model_payload),
                sha256_hex(legacy_payload),
                sha256_hex(raw_payload),
                sha256_hex(
                    _drop_keys(
                        raw_payload,
                        {
                            "model_excerpt_or_observation",
                            "proposed_priority",
                            "supersedes_test_id",
                            "debate",
                        },
                    )
                ),
            }
            if artifact.integrity_hash not in valid_hashes:
                raise StorageError("run integrity hash does not match its content")
            return artifact
        except Exception as exc:
            if isinstance(exc, StorageError):
                raise
            raise StorageError(f"{path}: invalid run artifact: {exc}") from exc

    def test_events(self, idea_id: str) -> list[dict[str, Any]]:
        idea_dir = self._idea_dir(idea_id)
        path = self._file(idea_dir, "tests.md")
        if not path.is_file():
            return []
        text = path.read_text(encoding="utf-8")
        events: list[dict[str, Any]] = []
        event_pattern = re.compile(
            r"(?P<fence>`{3,4})yaml\n(?P<body>.*?)(?P=fence)",
            flags=re.DOTALL,
        )
        for match in event_pattern.finditer(text):
            block = match.group("body")
            try:
                value = yaml.safe_load(block) or {}
            except yaml.YAMLError as exc:
                raise StorageError(f"{path}: invalid test event YAML: {exc}") from exc
            if not isinstance(value, dict):
                raise StorageError(f"{path}: test event must be a mapping")
            events.append(_validate_test_event(value))
        return events

    def prior_claim_ids(self, idea_id: str) -> set[str]:
        """Return claim IDs from immutable prior runs for supersedes checks."""
        idea_dir = self._idea_dir(idea_id)
        runs_dir = self._runs_dir(idea_dir)
        if not runs_dir.exists():
            return set()
        claim_ids: set[str] = set()
        for path in sorted(runs_dir.glob("run-*.md")):
            if path.name.endswith(".partial.md"):
                continue
            run_id = path.stem
            artifact = self.load_run(idea_id, run_id)
            claim_ids.update(claim.claim_id for claim in artifact.claims)
        return claim_ids

    def prior_test_ids(self, idea_id: str) -> set[str]:
        """Return test IDs from immutable prior runs for supersedes checks."""
        idea_dir = self._idea_dir(idea_id)
        runs_dir = self._runs_dir(idea_dir)
        if not runs_dir.exists():
            return set()
        test_ids: set[str] = set()
        for path in sorted(runs_dir.glob("run-*.md")):
            if path.name.endswith(".partial.md"):
                continue
            run_id = path.stem
            artifact = self.load_run(idea_id, run_id)
            if artifact.ledger is not None:
                test_ids.update(
                    row.test_id
                    for row in [
                        *artifact.ledger.rows,
                        *artifact.ledger.appendix_rows,
                    ]
                )
        return test_ids

    def has_confirmation(self, idea_id: str, run_id: str, test_id: str) -> bool:
        return any(
            event.get("event_type") == "confirmation"
            and event.get("run_id") == run_id
            and event.get("test_id") == test_id
            for event in self.test_events(idea_id)
        )

    def has_result(self, idea_id: str, run_id: str, test_id: str) -> bool:
        return any(
            event.get("event_type") == "result"
            and event.get("run_id") == run_id
            and event.get("test_id") == test_id
            for event in self.test_events(idea_id)
        )

    def write_run(self, artifact: RunArtifact, *, final: bool = True) -> Path:
        if final:
            expected_hash = sha256_hex(
                artifact.model_dump(mode="json", exclude={"integrity_hash"})
            )
            if artifact.integrity_hash != expected_hash:
                raise StorageError("final run artifact must carry a valid integrity hash")
        idea_dir = self._idea_dir(artifact.idea_id, create=True)
        runs_dir = self._runs_dir(idea_dir, create=True)
        suffix = ".md" if final else ".partial.md"
        path = self._file(runs_dir, f"{artifact.run_id}{suffix}")
        if final and path.exists():
            raise StorageError(f"run already exists: {path}")
        from .render import render_run

        self._atomic_write(path, render_run(artifact))
        if final:
            partial = runs_dir / f"{artifact.run_id}.partial.md"
            if partial.is_symlink():
                raise StorageError(f"partial run artifact is a symlink: {partial}")
            if partial.exists():
                partial.unlink()
        return path

    def _write_new(self, path: Path, content: str) -> None:
        if path.is_symlink():
            raise StorageError(f"refusing to write through symlink: {path}")
        if path.exists():
            raise StorageError(f"refusing to overwrite existing file: {path}")
        self._atomic_write(path, content)

    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        temp_path = Path(temp_name)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, path)
        finally:
            if temp_path.exists():
                temp_path.unlink()
