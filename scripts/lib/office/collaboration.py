"""Transactional private task and resource ownership, shared by CLI and web."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import sqlite3
import time
import uuid


class Conflict(ValueError):
    pass


def text(value, name, maximum=8192, optional=False):
    if optional and value is None:
        return ""
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"invalid_{name}")
    return value.strip()


def resource_name(value):
    value = text(value, "resource", 240)
    kind, separator, name = value.partition(":")
    if not separator or kind not in {"path", "port", "build"}:
        raise ValueError("invalid_resource")
    if kind == "port":
        if not name.isdigit() or not 1 <= int(name) <= 65535:
            raise ValueError("invalid_port")
        return f"port:{int(name)}"
    p = PurePosixPath(name)
    if not name or p.is_absolute() or ".." in p.parts or "\\" in name:
        raise ValueError("invalid_resource_path")
    return f"{kind}:{p}"


def overlaps(left, right):
    lk, ln = left.split(":", 1)
    rk, rn = right.split(":", 1)
    if lk == "port" or rk == "port":
        return left == right
    lp, rp = PurePosixPath(ln), PurePosixPath(rn)
    return lp == rp or lp in rp.parents or rp in lp.parents


class Board:
    def __init__(self, file: Path, lease_seconds: int, now=time.time):
        self.file, self.lease_seconds, self.now = file, lease_seconds, now
        file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self.connection() as db:
            if db.execute("PRAGMA user_version").fetchone()[0] not in {0, 1}:
                raise ValueError("unsupported_collaboration_store")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS owned_runs(id TEXT PRIMARY KEY, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS resources(name TEXT PRIMARY KEY, owner TEXT NOT NULL, task_id TEXT, expires REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY, at REAL NOT NULL, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS requests(id TEXT PRIMARY KEY, digest TEXT NOT NULL, result TEXT NOT NULL);
                PRAGMA user_version=1;
            """)
        os.chmod(file, 0o600)

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.file, timeout=10, isolation_level=None)
        db.row_factory = sqlite3.Row
        try:
            yield db
        finally:
            db.close()

    def get(self, db, task_id):
        row = db.execute("SELECT body FROM tasks WHERE id=?", (text(task_id, "task_id", 100),)).fetchone()
        if not row:
            raise ValueError("task_not_found")
        return json.loads(row[0])

    def put(self, db, task):
        db.execute("INSERT OR REPLACE INTO tasks VALUES (?,?)", (task["id"], json.dumps(task)))

    def event(self, db, kind, task_id, actor, note=""):
        db.execute("INSERT INTO events(at,body) VALUES (?,?)", (self.now(), json.dumps({"kind": kind, "task_id": task_id, "actor": actor, "note": note})))

    def reserve(self, db, name, owner, task_id):
        name = resource_name(name)
        for row in db.execute("SELECT * FROM resources WHERE expires>?", (self.now(),)):
            if overlaps(name, row["name"]) and (row["owner"] != owner or row["task_id"] != task_id):
                raise Conflict("resource_in_use")
        db.execute("INSERT OR REPLACE INTO resources VALUES (?,?,?,?)", (name, owner, task_id, self.now() + self.lease_seconds))

    def apply(self, payload):
        if not isinstance(payload, dict):
            raise ValueError("invalid_payload")
        rid = text(payload.get("request_id"), "request_id", 100)
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                old = db.execute("SELECT digest,result FROM requests WHERE id=?", (rid,)).fetchone()
                if old:
                    if old[0] != digest:
                        raise Conflict("request_id_reused")
                    db.commit()
                    return json.loads(old[1])
                result = self.mutate(db, payload)
                db.execute("INSERT INTO requests VALUES (?,?,?)", (rid, digest, json.dumps(result)))
                db.commit()
                return result
            except BaseException:
                db.rollback()
                raise

    def mutate(self, db, p):
        action = p.get("action")
        if action in {"create", "team"}:
            dependencies = p.get("depends_on", [])
            resources = p.get("resources", [])
            if action == "team" and (dependencies or resources):
                raise ValueError("invalid_team_constraints")
            if not isinstance(dependencies, list) or not isinstance(resources, list) or len(dependencies) > 20 or len(resources) > 20:
                raise ValueError("invalid_dependencies_or_resources")
            for dependency in dependencies:
                self.get(db, dependency)
            task = {"id": str(uuid.uuid4()), "title": text(p.get("title"), "title", 160),
                    "description": text(p.get("description"), "description", optional=True),
                    "status": "queued", "revision": 0, "assignee": None, "recipient": None,
                    "depends_on": list(dict.fromkeys(dependencies)), "resources": [resource_name(r) for r in resources],
                    "result": "", "parent_id": None, "managed": action == "team", "role": "coordinator" if action == "team" else None,
                    "thread_id": None, "runner_pid": None, "created_at": self.now(), "updated_at": self.now()}
            self.put(db, task)
            self.event(db, action, task["id"], "user")
            return task
        owner = text(p.get("session_id"), "session_id", 100)
        if action in {"resource", "release"}:
            name = resource_name(p.get("resource"))
            if action == "resource":
                self.reserve(db, name, owner, None)
            else:
                row = db.execute("SELECT owner FROM resources WHERE name=?", (name,)).fetchone()
                if row and row[0] != owner:
                    raise Conflict("not_resource_owner")
                db.execute("DELETE FROM resources WHERE name=?", (name,))
            self.event(db, action, None, owner, name)
            return {"resource": name, "owner": owner, "action": action}
        task = self.get(db, p.get("task_id"))
        if type(p.get("revision")) is not int or p["revision"] != task["revision"]:
            raise Conflict("stale_revision")
        if task["managed"] and action != "cancel":
            raise Conflict("managed_task")
        if action == "claim":
            if task["status"] not in {"queued", "review"}:
                raise Conflict("task_already_claimed")
            if task["recipient"] and task["recipient"] != owner:
                raise Conflict("handoff_recipient_only")
            if any(self.get(db, dep)["status"] != "done" for dep in task["depends_on"]):
                raise Conflict("dependency_incomplete")
            for resource in task["resources"]:
                self.reserve(db, resource, owner, task["id"])
            task.update(status="running", assignee=owner, recipient=None)
        elif action == "renew":
            if task["status"] != "running" or task["assignee"] != owner:
                raise Conflict("not_task_owner")
            for resource in task["resources"]:
                self.reserve(db, resource, owner, task["id"])
        elif action in {"handoff", "finish"}:
            if task["status"] != "running" or task["assignee"] != owner:
                raise Conflict("not_task_owner")
            task["result"] = text(p.get("result"), "result", 32768)
            task.update(status="done" if action == "finish" else "review", recipient=None if action == "finish" else text(p.get("recipient"), "recipient", 100))
            db.execute("DELETE FROM resources WHERE task_id=?", (task["id"],))
        elif action == "cancel":
            if task["managed"] and task["parent_id"]:
                raise Conflict("cancel_parent_team")
            if task["status"] in {"done", "cancelled"}:
                raise Conflict("task_terminal")
            task["status"] = "cancelled"
            db.execute("DELETE FROM resources WHERE task_id=?", (task["id"],))
            if task["managed"]:
                self.settle_children(db, task["id"], "cancelled", "Parent team cancelled")
        else:
            raise ValueError("unknown_action")
        task.update(revision=task["revision"] + 1, updated_at=self.now())
        self.put(db, task)
        self.event(db, action, task["id"], owner, task["result"] if action in {"finish", "handoff"} else "")
        return task

    def snapshot(self):
        with self.connection() as db:
            db.execute("BEGIN")
            tasks = [json.loads(row[0]) for row in db.execute("SELECT body FROM tasks ORDER BY rowid DESC")]
            resources = [{**dict(row), "active": row["expires"] > self.now()} for row in db.execute("SELECT * FROM resources ORDER BY name")]
            events = [{"id": row["seq"], "at": row["at"], **json.loads(row["body"])} for row in db.execute("SELECT * FROM events ORDER BY seq DESC LIMIT 100")]
            db.commit()
            return {"schema_version": 1, "tasks": tasks, "resources": resources, "events": events}

    def update(self, task_id, **changes):
        """Runner-only update; cancellation always wins over late model output."""
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            task = self.get(db, task_id)
            if task["status"] not in {"done", "cancelled"}:
                task.update(changes, revision=task["revision"] + 1, updated_at=self.now())
                self.put(db, task)
                self.event(db, "runtime", task_id, task.get("role") or "runner", changes.get("result", "")[:32768])
            db.commit()
            return task

    def begin_team(self, task_id, pid, maximum):
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            task = self.get(db, task_id)
            if not task["managed"] or task["parent_id"] or task["status"] != "queued":
                db.commit()
                return False
            running = [json.loads(row[0]) for row in db.execute("SELECT body FROM tasks")]
            def alive(pid):
                if not pid:
                    return False
                try:
                    os.kill(pid, 0)
                    return True
                except ProcessLookupError:
                    return False
                except PermissionError:
                    return True
            if sum(t["managed"] and not t["parent_id"] and alive(t["runner_pid"]) for t in running) >= maximum:
                raise Conflict("team_capacity")
            task.update(status="running", runner_pid=pid, revision=task["revision"] + 1, updated_at=self.now())
            self.put(db, task)
            self.event(db, "team_started", task_id, "runner")
            db.commit()
            return True

    def task(self, task_id):
        with self.connection() as db:
            return self.get(db, task_id)

    def child(self, parent, title, description):
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            if self.get(db, parent)["status"] != "running":
                raise Conflict("team_cancelled")
            task = self.mutate(db, {"action": "create", "title": title, "description": description})
            task.update(parent_id=parent, managed=True, role="worker")
            self.put(db, task)
            db.commit()
            return task

    def recover_lost(self, task_id, expected_pid):
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            task = self.get(db, task_id)
            if task["status"] == "running" and task["runner_pid"] == expected_pid:
                try:
                    os.kill(expected_pid, 0)
                except ProcessLookupError:
                    task.update(status="blocked", result="runtime_runner_lost", runner_pid=None,
                                revision=task["revision"] + 1, updated_at=self.now())
                    self.put(db, task)
                    if not task["parent_id"]:
                        self.settle_children(db, task_id, "blocked", "runtime_runner_lost")
                    self.event(db, "runtime_lost", task_id, "runner")
                except PermissionError:
                    pass
            db.commit()

    def settle_children(self, db, parent_id, status, result):
        children = [json.loads(row[0]) for row in db.execute("SELECT body FROM tasks")]
        for child in children:
            if child["parent_id"] == parent_id and child["status"] not in {"done", "cancelled"}:
                child.update(status=status, result=result, revision=child["revision"] + 1, updated_at=self.now())
                self.put(db, child)
                db.execute("DELETE FROM resources WHERE task_id=?", (child["id"],))
                self.event(db, status, child["id"], "coordinator", result)

    def end_team(self, task_id):
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            task = self.get(db, task_id)
            task["runner_pid"] = None
            self.put(db, task)
            db.commit()

    def record_run(self, record):
        """Server-owned evidence only; not exposed through Board.apply."""
        from .work import validate_record
        validate_record(record)
        task_id = record["task"]["id"]
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT body FROM owned_runs WHERE id=?", (task_id,)).fetchone()
            prior = json.loads(row[0]) if row else None
            evidence = {k: v for k, v in (prior or {}).items() if k not in {"review", "revision", "reviewed_at"}}
            if evidence == record:
                db.commit()
                return prior
            if prior and prior["status"] not in {"starting", "working", "waiting", "stopping"}:
                raise Conflict("run_already_finished")
            saved = {**record, "revision": prior["revision"] + 1 if prior else 0,
                     "review": "pending", "reviewed_at": None}
            db.execute("INSERT OR REPLACE INTO owned_runs VALUES (?,?)", (task_id, json.dumps(saved)))
            db.commit()
            return saved

    def run(self, task_id):
        with self.connection() as db:
            row = db.execute("SELECT body FROM owned_runs WHERE id=?", (text(task_id, "task_id", 100),)).fetchone()
            if not row:
                raise ValueError("task_not_found")
            return json.loads(row[0])

    def runs(self, limit=None):
        with self.connection() as db:
            return [json.loads(row[0]) for row in db.execute("SELECT body FROM owned_runs ORDER BY rowid DESC LIMIT ?", (limit if limit is not None else -1,))]

    def review_run(self, task_id, revision, review):
        if review not in {"accepted", "rework"} or type(revision) is not int:
            raise ValueError("invalid_review")
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT body FROM owned_runs WHERE id=?", (text(task_id, "task_id", 100),)).fetchone()
            if not row:
                raise ValueError("task_not_found")
            record = json.loads(row[0])
            if record["revision"] != revision:
                raise Conflict("stale_revision")
            if record["status"] in {"starting", "working", "waiting", "stopping"}:
                raise Conflict("run_not_finished")
            if review == "accepted" and (record["task"]["status"] != "completed" or not record["result"].strip()):
                raise Conflict("result_incomplete")
            if record["review"] != review:
                record.update(review=review, reviewed_at=self.now(), revision=revision + 1)
                db.execute("UPDATE owned_runs SET body=? WHERE id=?", (json.dumps(record), task_id))
            db.commit()
            return record
