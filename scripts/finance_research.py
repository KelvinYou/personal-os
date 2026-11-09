#!/usr/bin/env python3
# flow: wealth
"""Finance manager research proposals: read, what-if, review, validate.

Default: read the snapshot of private proposals under data/finance/research/.
`apply` reads one JSON command from stdin:
  {"op": "whatif", "id": ..., "inputs": {...partial inputs}}  -> recomputed result, never saved
  {"op": "review", "id": ..., "decision": ..., "note": ..., "written_for": ...}  -> append-only review
  {"op": "post_idea", "id": ...}  -> file an accepted proposal's public scenario as a Content Lab idea
`validate FILE` checks a proposal the Finance manager wrote and prints its fingerprint.
--demo reads the synthetic fixture and refuses reviews. Never moves money.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.clock import now_kl
from lib.wealth.research_post import file_post_idea
from lib.wealth.research import POSTS_DIR, RESEARCH_DIR, Proposal, ResearchError, append_review, load_rules, project, read_snapshot, whatif

ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = ROOT / "tests" / "fixtures" / "finance_research"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("operation", nargs="?", choices=["read", "apply", "validate"], default="read")
    parser.add_argument("file", nargs="?", type=Path)
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--research-dir", type=Path, help="explicit offline/test root; the web bridge never passes a path")
    args = parser.parse_args()
    try:
        rules = load_rules()
        today = now_kl().date()
        if args.operation == "validate":
            if not args.file:
                raise ResearchError("file_required")
            proposal = Proposal.model_validate(yaml.safe_load(args.file.read_text(encoding="utf-8")))
            result = project(proposal.inputs, rules)
            base = result.scenarios[result.base_index]
            print(json.dumps({"ok": True, "id": proposal.id, "inputs_fingerprint": result.inputs_fingerprint,
                              "recommendation_matches_inputs": proposal.recommendation.written_for == result.inputs_fingerprint,
                              "base_final_gap": round(base.final_gap), "first_buy_ahead_year": base.first_buy_ahead_year,
                              "breakeven_property_growth": result.breakeven_property_growth}))
            return 0
        directory = DEMO_DIR if args.demo else (args.research_dir.resolve() if args.research_dir else RESEARCH_DIR)
        source = "demo" if args.demo else ("private" if directory.is_dir() else "missing")
        posts = None if args.demo else POSTS_DIR
        snapshot = read_snapshot(directory if directory.is_dir() else None, today, rules, source, posts)
        if args.operation == "read":
            print(snapshot.model_dump_json())
            return 0
        command = json.load(sys.stdin)
        if not isinstance(command, dict):
            raise ResearchError("invalid_command")
        target = next((v for v in snapshot.proposals if v.proposal.id == command.get("id")), None)
        if command.get("op") == "whatif" and set(command) <= {"op", "id", "inputs"} and isinstance(command.get("inputs"), dict):
            if target is None:
                raise ResearchError("proposal_not_found", 404)
            print(whatif(target.proposal, command["inputs"], rules).model_dump_json())
            return 0
        if command.get("op") == "review" and set(command) <= {"op", "id", "decision", "note", "written_for"}:
            if args.demo or source != "private":
                raise ResearchError("review_needs_private_data", 409)
            append_review(directory, command.get("id", ""), command.get("decision", ""), command.get("note", ""), command.get("written_for", ""), snapshot.proposals)
            print(read_snapshot(directory, today, rules, source, posts).model_dump_json())
            return 0
        if command.get("op") == "post_idea" and set(command) <= {"op", "id"}:
            if args.demo or source != "private":
                raise ResearchError("review_needs_private_data", 409)
            if target is None:
                raise ResearchError("proposal_not_found", 404)
            post_id = file_post_idea(target, rules, today)
            print(json.dumps({"ok": True, "post_id": post_id}))
            return 0
        raise ResearchError("invalid_command")
    except ResearchError as exc:
        print(json.dumps({"error": {"code": exc.code, "status": exc.status}}))
    except OSError:
        print(json.dumps({"error": {"code": "research_unavailable", "status": 503}}))
    except (ValueError, KeyError, TypeError, yaml.YAMLError) as exc:
        if args.operation == "validate":
            print(json.dumps({"ok": False, "error": str(exc)[:2000]}))
            return 1
        print(json.dumps({"error": {"code": "invalid_or_unavailable_research", "status": 400}}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
