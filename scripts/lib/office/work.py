"""Validation of private owned execution evidence (not raw protocol records)."""
from __future__ import annotations
from datetime import datetime


def validate_record(record):
    def string(value):
        return isinstance(value, str)

    def timestamp(value):
        if not string(value):
            return False
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
            return True
        except ValueError:
            return False

    fields = {"schema_version", "task", "status", "result", "agents", "artifacts", "updated_at", "error"}
    if not isinstance(record, dict) or set(record) != fields or record["schema_version"] != 1:
        raise ValueError("invalid_run")
    task = record["task"]
    task_fields = {"id", "instruction", "collaboration", "status", "started_at", "skill_id"}
    if (not isinstance(task, dict) or set(task) != task_fields
            or not string(task["id"]) or not task["id"] or len(task["id"]) > 100
            or not string(task["instruction"]) or not task["instruction"].strip()
            or task["collaboration"] not in {"solo", "team"}
            or task["status"] not in {"running", "completed", "incomplete", "interrupted", "error"}
            or not timestamp(task["started_at"])
            or not (task["skill_id"] is None or string(task["skill_id"]))):
        raise ValueError("invalid_run_task")
    if (record["status"] not in {"starting", "working", "waiting", "stopping", "idle", "interrupted", "error"}
            or not string(record["result"]) or not timestamp(record["updated_at"])
            or not (record["error"] is None or string(record["error"]))
            or not isinstance(record["agents"], list)
            or not isinstance(record["artifacts"], list)
            or not all(string(p) and p and "\x00" not in p for p in record["artifacts"])):
        raise ValueError("invalid_run_evidence")
    fields = {"id", "task_id", "thread_id", "parent_id", "role", "assignment", "status", "result", "updated_at"}
    for agent in record["agents"]:
        if (not isinstance(agent, dict) or set(agent) != fields
                or not all(string(agent[k]) for k in {"id", "task_id", "thread_id", "assignment"})
                or agent["task_id"] != task["id"]
                or agent["role"] not in {"coordinator", "worker"}
                or agent["status"] not in {"working", "waiting", "completed", "interrupted", "error", "unknown"}
                or not (agent["parent_id"] is None or string(agent["parent_id"]))
                or not (agent["result"] is None or string(agent["result"]))
                or not timestamp(agent["updated_at"])):
            raise ValueError("invalid_run_agent")
