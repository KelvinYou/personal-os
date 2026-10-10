#!/usr/bin/env python3
# flow: eval
"""Read public synthetic skill runs; derive review counts once for CLI and web."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "reports/skill-regressions/cases.json"
RUNS = ROOT / "reports/skill-regressions/runs"
EVIDENCE_BYTE_LIMIT = 64 * 1024
STATUSES = {"pass", "fail", "unobserved"}


def derive_outcome(checks: list[dict], expected: set[str], reviewed: bool) -> str | None:
    if not reviewed:
        return None
    statuses = {c["id"]: c["status"] for c in checks}
    if "fail" in statuses.values():
        return "fail"
    if set(statuses) != expected or "unobserved" in statuses.values():
        return "inconclusive"
    return "pass"


def counts(runs: list[dict]) -> dict:
    total = Counter(r["outcome"] or "unreviewed" for r in runs)
    conclusive = total["pass"] + total["fail"]
    return {
        "runs": len(runs), "passed": total["pass"], "failed": total["fail"],
        "inconclusive": total["inconclusive"], "unreviewed": total["unreviewed"],
        "conclusive": conclusive,
        "pass_rate": total["pass"] / conclusive if conclusive else None,
    }


def check_counts(runs: list[dict], checks: list[dict]) -> dict:
    total = Counter()
    for run in runs:
        grades = {c["id"]: c["status"] for c in run["checks"]}
        for check in checks:
            total[grades.get(check["id"], "unreviewed" if run["outcome"] is None else "unobserved")] += 1
    return {"passed": total["pass"], "failed": total["fail"],
            "unobserved": total["unobserved"], "unreviewed": total["unreviewed"]}


def evidence(directory: Path, runs_root: Path) -> tuple[list[dict], list[str]]:
    docs, artifacts = [], []
    for relative in ("outputs/response.md", "execution.md", "reviewer-verification.txt"):
        path = directory / relative
        if path.is_file() and path.resolve().is_relative_to(runs_root.resolve()):
            data = path.read_bytes()
            docs.append({"path": relative, "text": data[:EVIDENCE_BYTE_LIMIT].decode("utf-8", errors="replace"),
                         "truncated": len(data) > EVIDENCE_BYTE_LIMIT})
    output = directory / "outputs"
    if output.is_dir():
        artifacts = [str(p.relative_to(directory)) for p in sorted(output.rglob("*"))
                     if p.is_file() and p.resolve().is_relative_to(runs_root.resolve())]
    return docs, artifacts


def build_report(corpus_path: Path = CORPUS, runs_root: Path = RUNS) -> dict:
    raw = corpus_path.read_bytes()
    corpus = json.loads(raw)
    if corpus.get("schema_version") != 1:
        raise ValueError("Unsupported skill corpus schema")
    cases = corpus["cases"]
    by_id = {case["id"]: case for case in cases}
    if len(by_id) != len(cases):
        raise ValueError("Duplicate case IDs")
    runs, errors, seen = [], [], set()
    corpus_hash = hashlib.sha256(raw).hexdigest()
    for path in sorted(runs_root.rglob("result.json")):
        try:
            if not path.resolve().is_relative_to(runs_root.resolve()):
                raise ValueError("Result symlink escapes run directory")
            # Prepared run records are not evidence that an execution happened.
            if not (path.parent / "execution.md").is_file():
                continue
            result = json.loads(path.read_text())
            if result.get("schema_version") != 1:
                raise ValueError("Unsupported result schema")
            case = by_id[result["case_id"]]
            run_id = result["run_id"]
            if not isinstance(run_id, str) or not run_id or run_id in seen:
                raise ValueError("Missing or duplicate run ID")
            if result["corpus_version"] != corpus["corpus_version"] or result["corpus_sha256"] != corpus_hash:
                raise ValueError("Run belongs to a different corpus; use its frozen corpus to review")
            checks = result["checks"]
            expected = {c["id"] for c in case["checks"]}
            ids = [c["id"] for c in checks]
            if len(set(ids)) != len(ids) or not set(ids).issubset(expected):
                raise ValueError("Duplicate or unknown check IDs")
            for check in checks:
                if check["status"] not in STATUSES or not isinstance(check["rationale"], str):
                    raise ValueError("Invalid review status or rationale")
                if not isinstance(check["evidence_refs"], list) or not all(isinstance(x, str) for x in check["evidence_refs"]):
                    raise ValueError("Invalid evidence references")
                if check["status"] in {"pass", "fail"} and not check["evidence_refs"]:
                    raise ValueError("Conclusive check has no evidence reference")
            reviewed = bool(result["reviewer"] and result["reviewed_at"])
            if not reviewed and (checks or result["outcome"] is not None):
                raise ValueError("Grades require reviewer identity and review date")
            outcome = derive_outcome(checks, expected, reviewed)
            if result["outcome"] != outcome:
                raise ValueError("Declared outcome disagrees with checks")
            documents, artifacts = evidence(path.parent, runs_root)
            configuration = path.parent.name
            runs.append({"run_id": run_id, "case_id": case["id"], "configuration": configuration,
                         "outcome": outcome, "checks": checks, "reviewer": result["reviewer"],
                         "reviewed_at": result["reviewed_at"], "harness": result["harness"],
                         "model": result["model"], "notes": result["notes"],
                         "path": str(path.relative_to(runs_root)),
                         "documents": documents, "artifacts": artifacts})
            seen.add(run_id)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            errors.append({"path": str(path.relative_to(runs_root)), "message": str(exc)})
    configurations = sorted({r["configuration"] for r in runs})
    return {
        "report_schema_version": 1, "corpus_version": corpus["corpus_version"],
        "generated_at": datetime.now(timezone.utc).isoformat(), "summary": counts(runs),
        "configurations": [{"name": name, **counts([r for r in runs if r["configuration"] == name])}
                           for name in configurations],
        "cases": [{"id": c["id"], "stage": c["stage"], "candidate_skills": c["candidate_skills"],
                   "source": c["source"], "checks": c["checks"],
                   "check_summary": check_counts([r for r in runs if r["case_id"] == c["id"]], c["checks"]),
                   "runs": [r for r in runs if r["case_id"] == c["id"]]} for c in cases],
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = build_report()
    if args.json:
        print(json.dumps(report, ensure_ascii=False))
    else:
        print(f'[Status: {"Warning" if report["errors"] else "OK"}] Skill regression evidence')
        print(json.dumps(report["summary"], indent=2))
        for item in report["errors"]:
            print(f'{item["path"]}: {item["message"]}')


if __name__ == "__main__":
    main()
