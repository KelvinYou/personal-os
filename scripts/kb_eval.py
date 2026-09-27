#!/usr/bin/env python3
"""Evaluate deterministic knowledge retrieval against a small golden set."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from kb_index import DEFAULT_MIN_TERM_COVERAGE, KNOWLEDGE_DIR, load_notes, search_notes  # noqa: E402
from lib.knowledge import KnowledgeNote, local_links  # noqa: E402


DEFAULT_QUERIES = ROOT / "tests" / "fixtures" / "kb_queries.yaml"


@dataclass(frozen=True)
class EvalReport:
    total: int
    route_at_1: int
    hit_at_3: int
    misses: tuple[dict[str, Any], ...]
    positive_total: int = 0
    no_answer_total: int = 0
    no_answer_correct: int = 0
    answer_total: int = 0
    answer_passed: int = 0
    claim_total: int = 0
    claim_passed: int = 0
    citation_total: int = 0
    citation_passed: int = 0
    answer_misses: tuple[dict[str, Any], ...] = ()


def _relative_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _string_list(query: dict[str, Any], key: str) -> list[str]:
    raw = query.get(key, [])
    if raw is None:
        return []
    if not isinstance(raw, list) or not all(isinstance(item, str) and item.strip() for item in raw):
        raise ValueError(f"query {query.get('id', '<unknown>')} {key} must be a list of non-empty strings")
    return [item.strip() for item in raw]


def _normalise_text(value: str) -> str:
    return " ".join(value.casefold().split())


def _evaluate_answer(query: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, int]]:
    answer_fields = ("answer", "required_claims", "required_citations", "scope")
    if not any(field in query for field in answer_fields):
        return None, {"answers": 0, "claims": 0, "claim_hits": 0, "citations": 0, "citation_hits": 0}

    answer = query.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError(f"query {query.get('id', '<unknown>')} answer must be non-empty text")
    claims = _string_list(query, "required_claims")
    citations = _string_list(query, "required_citations")
    scope = set(_string_list(query, "scope"))
    if scope and not set(citations).issubset(scope):
        raise ValueError(f"query {query.get('id', '<unknown>')} required_citations must be inside scope")

    normalised_answer = _normalise_text(answer)
    missing_claims = [claim for claim in claims if _normalise_text(claim) not in normalised_answer]
    cited_paths = {path for path, _ in local_links(answer)}
    missing_citations = [citation for citation in citations if citation not in cited_paths and citation not in answer]
    out_of_scope = sorted(cited_paths - scope) if scope else []
    miss = None
    if missing_claims or missing_citations or out_of_scope:
        miss = {
            "id": query.get("id", "<unknown>"),
            "missing_claims": missing_claims,
            "missing_citations": missing_citations,
            "out_of_scope": out_of_scope,
        }
    return miss, {
        "answers": 1,
        "claims": len(claims),
        "claim_hits": len(claims) - len(missing_claims),
        "citations": len(citations),
        "citation_hits": len(citations) - len(missing_citations),
    }


def evaluate_queries(
    queries: list[dict[str, Any]],
    notes: tuple[KnowledgeNote, ...] | list[KnowledgeNote],
    *,
    root: Path = ROOT,
    limit: int = 3,
    min_term_coverage: float = DEFAULT_MIN_TERM_COVERAGE,
) -> EvalReport:
    route_at_1 = 0
    hit_at_3 = 0
    positive_total = 0
    no_answer_total = 0
    no_answer_correct = 0
    misses: list[dict[str, Any]] = []
    answer_misses: list[dict[str, Any]] = []
    answer_total = 0
    answer_passed = 0
    claim_total = 0
    claim_passed = 0
    citation_total = 0
    citation_passed = 0

    for query in queries:
        question = query.get("query")
        if not isinstance(question, str) or not question.strip():
            raise ValueError(f"query {query.get('id', '<unknown>')} query must be non-empty text")
        expected = set(_string_list(query, "expected_paths"))
        expect_no_match = query.get("expect_no_match", False)
        if not isinstance(expect_no_match, bool):
            raise ValueError(f"query {query.get('id', '<unknown>')} expect_no_match must be boolean")
        if expect_no_match and expected:
            raise ValueError(f"query {query.get('id', '<unknown>')} cannot combine expect_no_match with expected_paths")
        if not expect_no_match and not expected:
            raise ValueError(f"query {query.get('id', '<unknown>')} has no expected_paths")
        results = search_notes(
            question,
            list(notes),
            limit=limit,
            min_term_coverage=min_term_coverage,
        )
        result_paths = [_relative_path(result.note.path, root) for result in results]

        if expect_no_match:
            if any(field in query for field in ("answer", "required_claims", "required_citations", "scope")):
                raise ValueError(f"query {query.get('id', '<unknown>')} cannot define an answer for no-match")
            no_answer_total += 1
            if not result_paths:
                no_answer_correct += 1
            else:
                misses.append(
                    {
                        "id": query.get("id", "<unknown>"),
                        "expected": ["<no-match>"],
                        "results": result_paths,
                    }
                )
            continue

        positive_total += 1
        top_hit = bool(result_paths and result_paths[0] in expected)
        any_hit = bool(expected.intersection(result_paths))
        route_at_1 += top_hit
        hit_at_3 += any_hit
        if not top_hit or not any_hit:
            misses.append(
                {
                    "id": query.get("id", "<unknown>"),
                    "expected": sorted(expected),
                    "results": result_paths,
                }
            )

        answer_miss, answer_stats = _evaluate_answer(query)
        answer_total += answer_stats["answers"]
        claim_total += answer_stats["claims"]
        claim_passed += answer_stats["claim_hits"]
        citation_total += answer_stats["citations"]
        citation_passed += answer_stats["citation_hits"]
        if answer_miss:
            answer_misses.append(answer_miss)
        elif answer_stats["answers"]:
            answer_passed += 1

    return EvalReport(
        total=len(queries),
        route_at_1=route_at_1,
        hit_at_3=hit_at_3,
        misses=tuple(misses),
        positive_total=positive_total,
        no_answer_total=no_answer_total,
        no_answer_correct=no_answer_correct,
        answer_total=answer_total,
        answer_passed=answer_passed,
        claim_total=claim_total,
        claim_passed=claim_passed,
        citation_total=citation_total,
        citation_passed=citation_passed,
        answer_misses=tuple(answer_misses),
    )


def load_queries(path: Path = DEFAULT_QUERIES) -> list[dict[str, Any]]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    if not isinstance(raw, list) or not all(isinstance(item, dict) for item in raw):
        raise ValueError("knowledge eval fixture must be a YAML list of mappings")
    return raw


def render_report(report: EvalReport) -> str:
    route_pct = report.route_at_1 / report.positive_total * 100 if report.positive_total else None
    hit_pct = report.hit_at_3 / report.positive_total * 100 if report.positive_total else None
    no_answer_pct = (
        report.no_answer_correct / report.no_answer_total * 100 if report.no_answer_total else None
    )
    route_text = f"{route_pct:.0f}%" if route_pct is not None else "n/a"
    hit_text = f"{hit_pct:.0f}%" if hit_pct is not None else "n/a"
    no_answer_text = f"{no_answer_pct:.0f}%" if no_answer_pct is not None else "n/a"
    answer_pct = report.answer_passed / report.answer_total * 100 if report.answer_total else None
    claim_pct = report.claim_passed / report.claim_total * 100 if report.claim_total else None
    citation_pct = report.citation_passed / report.citation_total * 100 if report.citation_total else None
    answer_text = f"{answer_pct:.0f}%" if answer_pct is not None else "n/a"
    claim_text = f"{claim_pct:.0f}%" if claim_pct is not None else "n/a"
    citation_text = f"{citation_pct:.0f}%" if citation_pct is not None else "n/a"
    status = "Warning" if report.misses or report.answer_misses else "OK"
    lines = [
        f"[Status: {status}] kb eval: route@1={route_text} hit@3={hit_text} "
        f"no-answer={no_answer_text} answer={answer_text} claims={claim_text} citations={citation_text} "
        f"(positive={report.positive_total} negative={report.no_answer_total} answers={report.answer_total})"
    ]
    for miss in report.misses:
        lines.append(
            f"[Status: Warning] {miss['id']}: expected={','.join(miss['expected'])} results={','.join(miss['results']) or '<none>'}"
        )
    for miss in report.answer_misses:
        lines.append(
            f"[Status: Warning] {miss['id']}: "
            f"missing_claims={','.join(miss['missing_claims']) or '<none>'} "
            f"missing_citations={','.join(miss['missing_citations']) or '<none>'} "
            f"out_of_scope={','.join(miss['out_of_scope']) or '<none>'}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queries", type=Path, default=DEFAULT_QUERIES)
    parser.add_argument("--directory", type=Path, default=KNOWLEDGE_DIR)
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--min-term-coverage", type=float, default=DEFAULT_MIN_TERM_COVERAGE)
    parser.add_argument("--min-hit-at-3", type=float, default=0.9)
    parser.add_argument("--min-no-answer", type=float, default=1.0)
    parser.add_argument("--min-answer-pass", type=float, default=1.0)
    parser.add_argument("--min-claim-coverage", type=float, default=1.0)
    parser.add_argument("--min-citation-coverage", type=float, default=1.0)
    args = parser.parse_args(argv)

    report = evaluate_queries(
        load_queries(args.queries),
        load_notes(args.directory),
        root=ROOT,
        limit=args.limit,
        min_term_coverage=args.min_term_coverage,
    )
    print(render_report(report))
    hit_rate = report.hit_at_3 / report.positive_total if report.positive_total else 1.0
    no_answer_rate = report.no_answer_correct / report.no_answer_total if report.no_answer_total else 1.0
    answer_rate = report.answer_passed / report.answer_total if report.answer_total else 1.0
    claim_rate = report.claim_passed / report.claim_total if report.claim_total else 1.0
    citation_rate = report.citation_passed / report.citation_total if report.citation_total else 1.0
    return int(
        not (
            hit_rate >= args.min_hit_at_3
            and no_answer_rate >= args.min_no_answer
            and answer_rate >= args.min_answer_pass
            and claim_rate >= args.min_claim_coverage
            and citation_rate >= args.min_citation_coverage
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
