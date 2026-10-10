# Skill regression cases

[Status: Warning] Eight candidate cases extracted from correction records.
The first [record-preservation pair](runs/20261007T071251Z/reviewer-notes.md)
has independent reviews: final content survives, but process chronology lacks
independent evidence. The [complete first suite](runs/20261007-suite-1/README.md)
covers all eight cases with sixteen paired executions and independent reviews.
Open [the portable review](review.html), or use the local dashboard.

`cases.json` owns versioned inputs and observable acceptance checks.
`result-template.json` owns the review format. Human reviewers or a separate
review session consume both; the agent executing a case leaves grades null.
`scripts/skill_regressions.py` validates completed run records and owns all
aggregate counts. Run `make skill-evals` or `make skill-evals JSON=1`.
The local `/skill-regressions` dashboard renders that report without recalculating
review outcomes. Prepared records without `execution.md` are not counted as
executed runs. Corrupt or mismatched records are visibly excluded.
The original correction queue remains the owner of historical evidence and
instruction approval. Cases never approve or merge pending proposals.

## Correction provenance after queue review

On 2026-10-07 the owner approved archiving the source corrections into
[`reports/corrections/archive.md`](../corrections/archive.md). `cases.json` and
completed runs remain frozen: their source paths and statuses describe the
queue at corpus capture, not its current state. Look up the same source heading
in the archive for the current disposition. The restaurant entry was extracted
from its template comment during this review; it remains outside this corpus.
Archiving a correction does not upgrade any regression grade or prove missing
execution/visual evidence.

## Evidence and scope

All scenarios are synthetic English adaptations of public
`reports/corrections/pending.md` and `archive.md`, not verbatim transcripts.
Source headings identify provenance; candidate skill associations are inferred,
not measured invocations. Several cases test shared agent behavior rather than
a single skill. Do not attribute their results exclusively to one skill.

The September 29 photography correction is scoped to its scenario. The October
1 restaurant entry occurs inside an HTML comment/template and is excluded.
The October 6 HTML-only proposal was superseded: preservation and the final
approved Markdown-to-HTML workflow are tested instead. Other pending entries
are candidate failure examples, not standing instructions; the case's supplied
user messages establish its acceptance requirements.

Inputs contain no real trip dates, destinations, personal metrics or holdings.
Use disposable synthetic fixtures, never real `data/`. Keep raw transcripts,
screenshots and outputs containing personal information under private
`data/reports/skill-regressions/`; public result files may contain only reviewed,
sanitized summaries and references.

## Run a case

1. Freeze `cases.json` and the harness, model, relevant AGENTS.md, skills,
   references, scripts and assets. Record Git revision plus a content hash for
   dirty/untracked relevant files; a commit alone does not identify this tree.
2. Start a fresh isolated session with normal project instructions and the
   relevant skill. Supply only the selected case's `input`, prepare its
   synthetic fixtures in a disposable workspace, and deliver messages in order.
   Do not show acceptance checks to the execution agent. Mock the integration
   evidence in the integration case so comparisons do not depend on live web
   results. Do not grant writes to real records or contact external services.
3. Save the actual response, tool trace, changed files and screenshots where
   required. Copy `result-template.json` for a unique run; fill identity and
   evidence fields, leaving review fields null until independent review.
4. A human or separate review session assigns every check `pass`, `fail`, or
   `unobserved`, with an evidence reference and short rationale. Tool trace and
   artifacts establish actions; a promise in the final answer does not.
5. Compare before/after versions using the same cases, fixtures, model and
   harness. Repeat runs when behavior varies; retain individual results rather
   than selecting the best one. Hold out additional paraphrases when tuning to
   avoid merely memorizing these eight inputs.

In a reviewed result, `checks` contains one entry per case check:

```json
{
  "id": "render-evidence",
  "status": "unobserved",
  "evidence_refs": [],
  "rationale": "No desktop or mobile screenshots were retained."
}
```

Use the check IDs from the selected case. `evidence_refs` points to saved
artifacts or trace event IDs; do not embed raw private content in public results.
Missing checks make the run inconclusive unless another check already failed.

## Scoring

- `pass`: all checks pass with evidence.
- `fail`: any check fails.
- `inconclusive`: no failed checks, but at least one is unobserved.
- `null`: not reviewed. Never convert this to zero or failure.

Report passed / reviewed-conclusive runs, failed runs, inconclusive runs and
unreviewed runs separately. Show counts alongside percentages. This small,
travel-heavy sample cannot establish overall skill quality or a leaderboard.
Visual quality checks require rendered screenshots and independent assessment;
string matching or HTML validation alone cannot establish a comfortable UI.

## Contract review

| Contract | Owner | Consumer | Version / migration | Verification | Result |
|---|---|---|---|---|---|
| Historical correction / approval | correction queue | case provenance | Queue unchanged | Source headings and later decisions checked | OK |
| Scenario and checks | `cases.json` | execution harness / independent reviewer | Version 1; freeze per experiment | JSON shape, unique IDs, source references | OK |
| Run review | `result-template.json` | independent reviewer / future dashboard | Version 1; grades start null | JSON parse and empty-review check | OK |
| Review aggregation | `scripts/skill_regressions.py` | CLI, `web/lib/skill-regressions.ts`, `/skill-regressions` | Report schema 1; existing session evals unchanged | Synthetic outcome, denominator, corpus, evidence-boundary tests; web typecheck | OK |
| Public / private boundary | this README | fixture and result authors | Synthetic inputs; raw personal evidence private | No private data read or copied | OK |

GO for manually executed, independently reviewed regressions and local dashboard
inspection. Existing session eval formats and skills are unchanged. No automatic
model execution, certified trace capture, token/cost attribution or automatic
quality scoring is claimed. The standalone first-pair viewer uses the existing
skill-creator generator with a run-local adapter for neutral unobserved grades;
shared agent behavior instructions were not changed.

The cases supplement `tests/fixtures/travel_known_defects.yaml`, which continues
to own travel-content/lint defects. They test execution behavior, ownership and
response to corrections.
