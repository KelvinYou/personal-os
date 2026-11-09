"""Single owner of content-lab records and bounded, private post projection."""
from __future__ import annotations

import os
import re
import stat
import fcntl
import hashlib
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, RootModel, model_validator

POST_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,168}-\d{4}-\d{2}-\d{2}$")
IMAGE = re.compile(r"^\d{2,}[-_][a-zA-Z0-9_-]+\.(png|jpe?g|webp)$", re.I)
TEXT_LIMIT = 512 * 1024
IMAGE_LIMIT = 32 * 1024 * 1024
POST_LIMIT = 500
Text = Annotated[str, Field(min_length=1, max_length=4000)]
Count = Annotated[int, Field(ge=0, le=9007199254740991, strict=True)]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False,
                              str_strip_whitespace=True,
                              json_schema_serialization_defaults_required=True)


class GateResult(Model):
    question: int = Field(ge=1, le=5, strict=True)
    result: Literal["pass", "fail", "unknown"]
    note: str = Field(default="", max_length=4000)


class Evidence(Model):
    reference: Text
    observed_at: AwareDatetime
    observation: Text
    qualification: str = Field(default="", max_length=4000)


class Experiment(Model):
    hypothesis: str = Field(default="", max_length=4000)
    changed_variable: str = Field(default="", max_length=4000)
    gate: list[GateResult] = Field(default_factory=list, max_length=5)
    demand_evidence: list[Evidence] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def distinct_questions(self):
        if len({g.question for g in self.gate}) != len(self.gate):
            raise ValueError("experiment.gate: duplicate question")
        return self


class Readiness(Model):
    factual: Literal["unknown", "passed", "failed"] = "unknown"
    visual: Literal["unknown", "passed", "failed"] = "unknown"
    owner_review: Literal["pending", "accepted", "changes_requested"] = "pending"
    # When the owner last decided; the runner preserves it. Measures review latency (review_waits).
    reviewed_at: AwareDatetime | None = None


class Publication(Model):
    platform: Literal["xhs"]
    published_at: AwareDatetime
    url: str = Field(pattern=r"^https://(?:www\.)?(?:xiaohongshu\.com|xhslink\.com)/\S+$", max_length=2000)


class Measurement(Model):
    observed_at: AwareDatetime
    source: Text
    traffic: Literal["organic", "paid", "mixed", "unknown"] = "unknown"
    views: Count | None = None
    likes: Count | None = None
    saves: Count | None = None
    comments: Count | None = None
    shares: Count | None = None
    follows: Count | None = None


class Production(Model):
    minutes: float | None = Field(default=None, ge=0, strict=True)
    cost: float | None = Field(default=None, ge=0, strict=True)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")

    @model_validator(mode="after")
    def cost_unit(self):
        if (self.cost is None) != (self.currency is None):
            raise ValueError("production.cost: cost and currency must be recorded together")
        return self


class Feedback(Model):
    at: AwareDatetime
    note: Annotated[str, Field(min_length=1, max_length=2000)]


class PipelineRun(Model):
    started_at: AwareDatetime
    finished_at: AwareDatetime | None = None
    outcome: Literal["running", "succeeded", "failed"]
    reason: str = Field(default="", max_length=4000)
    log: str = Field(default="", pattern=r"^[A-Za-z0-9._-]{0,200}$")


class Pipeline(Model):
    """Autonomous production state; the runner owns it, the owner only queues or stops work."""
    status: Literal["idle", "queued", "running", "failed"] = "idle"
    requested_at: AwareDatetime | None = None
    feedback: list[Feedback] = Field(default_factory=list, max_length=100)
    runs: list[PipelineRun] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def queued_has_time(self):
        if self.status in ("queued", "running") and self.requested_at is None:
            raise ValueError("pipeline.requested_at: queued or running work needs a request time")
        return self


class LabRecord(Model):
    schema_version: Literal[1] = 1
    stage: Literal["idea", "research", "production", "review", "ready", "published", "archived"] = "research"
    experiment: Experiment = Field(default_factory=Experiment)
    task_ids: list[Annotated[str, Field(pattern=r"^[a-zA-Z0-9_-]{1,100}$")]] = Field(default_factory=list, max_length=100)
    readiness: Readiness = Field(default_factory=Readiness)
    publication: Publication | None = None
    measurements: list[Measurement] = Field(default_factory=list, max_length=1000)
    production: Production = Field(default_factory=Production)
    pipeline: Pipeline = Field(default_factory=Pipeline)

    @model_validator(mode="after")
    def coherent(self):
        if self.stage == "ready" and (self.readiness.factual != "passed" or self.readiness.visual != "passed" or self.readiness.owner_review != "accepted"):
            raise ValueError("readiness: ready requires factual/visual passes and owner acceptance")
        if self.stage == "published" and self.publication is None:
            raise ValueError("publication: published requires an explicit publication record")
        if self.measurements and self.publication is None:
            raise ValueError("measurements: publication evidence is required")
        if self.publication and any(m.observed_at < self.publication.published_at for m in self.measurements):
            raise ValueError("measurements.observed_at: cannot precede publication")
        if len({m.observed_at for m in self.measurements}) != len(self.measurements):
            raise ValueError("measurements.observed_at: duplicate observation")
        return self


class LabItem(Model):
    post_id: str
    record: LabRecord | None
    revision: str | None = None


class LabCollection(Model):
    schema_version: Literal[1] = 1
    items: list[LabItem]
    partial: bool


class ResultsCommand(Model):
    action: Literal["record_results"]
    post_id: str = Field(pattern=POST_ID.pattern, max_length=180)
    expected_revision: str | None = Field(pattern=r"^[a-f0-9]{64}$")
    publication: Publication
    measurement: Measurement


class ReviewCommand(Model):
    action: Literal["review_content"]
    post_id: str = Field(pattern=POST_ID.pattern, max_length=180)
    expected_revision: str | None = Field(pattern=r"^[a-f0-9]{64}$")
    decision: Literal["accepted", "changes_requested"]
    # A change request with a note re-queues the package for the autonomous pipeline.
    note: str = Field(default="", max_length=2000)


class WorkCommand(Model):
    action: Literal["approve_idea", "archive", "requeue"]
    post_id: str = Field(pattern=POST_ID.pattern, max_length=180)
    expected_revision: str | None = Field(pattern=r"^[a-f0-9]{64}$")


class LabWriteCommand(RootModel[Annotated[ResultsCommand | ReviewCommand | WorkCommand, Field(discriminator="action")]]):
    pass


class ContentWriteError(ValueError):
    def __init__(self, code: str, status: int = 422):
        super().__init__(code)
        self.code, self.status = code, status


_UNREAD = object()


def bounded_read(file: Path, root: Path, limit: int = TEXT_LIMIT) -> bytes:
    """Reject escapes, symlinks, special files and oversized reads before allocation."""
    resolved = file.resolve(strict=True)
    if not resolved.is_relative_to(root.resolve(strict=True)) or file.is_symlink():
        raise ValueError("file: escaped private post root or symbolic link")
    fd = os.open(file, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            raise ValueError("file: unsupported or oversized")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            data = stream.read(limit + 1)
        if len(data) > limit:
            raise ValueError("file: oversized")
        return data
    finally:
        os.close(fd)


def validate_post(post: Path, root: Path, _record_bytes=_UNREAD) -> LabRecord | None:
    try:
        if not POST_ID.fullmatch(post.name) or post.is_symlink() or not post.resolve(strict=True).is_relative_to(root.resolve(strict=True)):
            raise ValueError("post_id: invalid or escaped folder")
        datetime.strptime(post.name[-10:], "%Y-%m-%d")
        record_path = post / "lab.yaml"
        if _record_bytes is _UNREAD:
            _record_bytes = bounded_read(record_path, root) if record_path.exists() or record_path.is_symlink() else None
        if _record_bytes is None:
            return None
        record = LabRecord.model_validate(yaml.safe_load(_record_bytes.decode("utf-8")))
        if record.stage == "ready":
            try:
                copy = bounded_read(post / "publish.txt", root).decode("utf-8")
                if not copy.strip() or "\0" in copy:
                    raise ValueError()
            except (OSError, ValueError) as exc:
                raise ValueError("publish.txt: ready requires readable nonempty copy") from exc
            try:
                images = post / "images"
                if images.is_symlink() or not images.resolve(strict=True).is_relative_to(post.resolve()):
                    raise ValueError()
                names = sorted(p for p in images.iterdir() if IMAGE.fullmatch(p.name))
                if not names:
                    raise ValueError()
                for file in names:
                    data = bounded_read(file, root, IMAGE_LIMIT)
                    ext = file.suffix.lower()
                    valid = (ext == ".png" and data.startswith(b"\x89PNG\r\n\x1a\n")) or (ext in (".jpg", ".jpeg") and data.startswith(b"\xff\xd8\xff")) or (ext == ".webp" and data[:4] == b"RIFF" and data[8:12] == b"WEBP")
                    if not valid:
                        raise ValueError()
            except (OSError, ValueError) as exc:
                raise ValueError("images: ready requires readable numbered PNG/JPEG/WebP images") from exc
        return record
    except (OSError, ValueError, yaml.YAMLError) as exc:
        raise ValueError(f"{post.name}: {exc}") from exc


def read_item(post: Path, root: Path) -> LabItem:
    file = post / "lab.yaml"
    try:
        raw = bounded_read(file, root)
    except FileNotFoundError:
        if file.is_symlink():
            raise ValueError(f"{post.name}: lab.yaml: broken symbolic link")
        raw = None
    return LabItem(post_id=post.name, record=validate_post(post, root, raw),
                   revision=hashlib.sha256(raw).hexdigest() if raw is not None else None)


@contextmanager
def record_lock(root: Path):
    """Serialise every lab.yaml writer (browser commands and the pipeline runner)."""
    if not root.is_dir():
        raise ContentWriteError("content_lab_unavailable", 503)
    fd = os.open(root / ".content-lab.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ContentWriteError("content_lab_unavailable", 503)
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


def commit(post: Path, root: Path, values: dict) -> LabItem:
    """Validate a whole candidate record (including cross-file rules), then replace lab.yaml atomically."""
    updated = LabRecord.model_validate(values)
    encoded = yaml.safe_dump(updated.model_dump(mode="json"), allow_unicode=True, sort_keys=False).encode("utf-8")
    if len(encoded) > TEXT_LIMIT:
        raise ContentWriteError("record_too_large")
    try:
        validate_post(post, root, encoded)  # The same ready gate runs before any mutation.
    except ValueError as exc:
        raise ContentWriteError("record_invalid") from exc
    file_fd, filename = tempfile.mkstemp(prefix=".lab-", suffix=".tmp", dir=post)
    try:
        with os.fdopen(file_fd, "wb") as output:
            output.write(encoded)
            output.flush()
            os.fsync(output.fileno())
        os.replace(filename, post / "lab.yaml")
    finally:
        Path(filename).unlink(missing_ok=True)
    return LabItem(post_id=post.name, record=updated, revision=hashlib.sha256(encoded).hexdigest())


def _transition(record: LabRecord, command, now: datetime) -> dict | None:
    """The new record values, or None when the command is an exact retry."""
    values = record.model_dump()
    pipeline = values["pipeline"]
    queue = lambda: pipeline.update(status="queued", requested_at=now)
    if isinstance(command, ResultsCommand):
        if record.publication == command.publication and command.measurement in record.measurements:
            return None
        values.update(publication=command.publication, measurements=[*record.measurements, command.measurement], stage="published")
    elif isinstance(command, ReviewCommand):
        note = command.note.strip()
        last = record.pipeline.feedback[-1].note if record.pipeline.feedback else None
        if record.readiness.owner_review == command.decision and (not note or (note == last and record.pipeline.status == "queued")):
            return None
        values["readiness"] = {**record.readiness.model_dump(), "owner_review": command.decision, "reviewed_at": now}
        if command.decision == "changes_requested" and note:
            pipeline["feedback"] = [*pipeline["feedback"], {"at": now, "note": note}]
            values["readiness"].update(factual="unknown", visual="unknown")
            values["stage"] = "production"
            queue()
        else:
            values["stage"] = "published" if record.publication else ("ready" if command.decision == "accepted" and record.readiness.factual == record.readiness.visual == "passed" else "review")
    elif command.action == "approve_idea":
        if record.stage == "research" and record.pipeline.status == "queued":
            return None
        if record.stage != "idea":
            raise ContentWriteError("invalid_transition")
        values["stage"] = "research"
        queue()
    elif command.action == "requeue":
        if record.pipeline.status == "queued":
            return None
        if record.pipeline.status != "failed":
            raise ContentWriteError("invalid_transition")
        queue()
    else:  # archive
        if record.stage == "archived" and record.pipeline.status == "idle":
            return None
        values["stage"] = "archived"
        pipeline["status"] = "idle"
    return values


def apply_command(root: Path, raw: dict, now: datetime | None = None) -> LabItem:
    """Local, narrow metadata writes; never publish, rewrite post content or overwrite stale edits."""
    command = LabWriteCommand.model_validate(raw).root
    now = now or datetime.now(timezone.utc)
    if not root.is_dir():
        raise ContentWriteError("content_lab_unavailable", 503)
    root = root.resolve(strict=True)
    with record_lock(root):
        post = root / command.post_id
        # A write may only target an existing post, never create a folder or follow one outside root.
        if post.is_symlink() or not post.is_dir() or not post.resolve().is_relative_to(root):
            raise ContentWriteError("post_not_found", 404)
        try:
            bounded_read(post / "post.md", root)
            item = read_item(post, root)
        except (OSError, ValueError) as exc:
            raise ContentWriteError("record_invalid") from exc
        record = item.record or LabRecord()
        if record.pipeline.status == "running":
            raise ContentWriteError("pipeline_running", 409)
        # Exact retries are harmless, including a repeated click after a successful response.
        values = _transition(record, command, now)
        if values is None:
            return item
        if item.revision != command.expected_revision:
            raise ContentWriteError("record_changed", 409)
        return commit(post, root, values)


def read_collection(root: Path) -> tuple[LabCollection, list[str]]:
    if not root.is_dir():
        raise ValueError("content_lab_unavailable")
    folders = sorted((p for p in root.iterdir() if POST_ID.fullmatch(p.name) or (p.is_dir() and ((p / "lab.yaml").exists() or (p / "lab.yaml").is_symlink()))), key=lambda p: p.name, reverse=True)
    errors: list[str] = []
    items = []
    for post in folders[:POST_LIMIT]:
        try:
            if not post.is_dir():
                raise ValueError(f"{post.name}: post_id: expected a directory")
            items.append(read_item(post, root))
        except ValueError as exc:
            errors.append(str(exc))
    if len(folders) > POST_LIMIT:
        errors.append("posts: collection exceeds bounded read limit")
    return LabCollection(items=items, partial=bool(errors)), errors


def review_waits(record: LabRecord) -> list[dict]:
    """How long each finished package waited for the owner (docs/design/office-world.md "Town attention").

    A succeeded run opens a wait; the first later owner decision closes it: a
    change-request note (`pipeline.feedback[].at`) or the last decision
    (`readiness.reviewed_at`). Kinds: `closed` (seconds), `open` (still in review,
    seconds measured by the caller), `unmeasured` (decided before reviewed_at was
    recorded, or archived without a review). A note-free change request
    followed by another decision only keeps the later time, so that cycle reads long.
    """
    decisions = sorted([f.at for f in record.pipeline.feedback] + ([record.readiness.reviewed_at] if record.readiness.reviewed_at else []))
    finished = [run.finished_at for run in record.pipeline.runs if run.outcome == "succeeded" and run.finished_at]
    waits = []
    for index, opened in enumerate(finished):
        closed = next((at for at in decisions if at >= opened), None)
        last = index == len(finished) - 1
        if closed is not None:
            waits.append({"opened": opened, "kind": "closed", "seconds": (closed - opened).total_seconds()})
        elif last and record.stage == "review" and record.pipeline.status == "idle":
            waits.append({"opened": opened, "kind": "open", "seconds": None})
        else:
            waits.append({"opened": opened, "kind": "unmeasured", "seconds": None})
    return waits
