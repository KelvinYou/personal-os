# First complete correction regression suite

[Status: Warning] Eight cases, sixteen executions, independently reviewed.
Three runs pass and thirteen are inconclusive; no failing checks were confirmed.
Across the paired cases, 35 of 56 checks pass and 21 are unobserved. These counts
include the earlier record-preservation pair in `../20261007T071251Z/`.

## Findings

- Both reusable-UI runs pass their three artifact-based checks: the reusable
  owner changed, generated output incorporates it, and unrelated source content
  remains intact. This does not establish superior visual quality.
- The final-workflow with-skill run passes all five checks. The baseline passes
  four; its instruction-review check is unobserved because the baseline control
  prohibited reading skill instructions. This experimental restriction is not
  an observed agent defect.
- Both preservation outputs retain the known history, source, original
  verification date and unresolved recheck. The with-skill output additionally
  archives a byte-identical source. Neither run establishes pre-deletion
  inspection/verification chronology independently.
- Warning outputs have independently observed desktop risk distinctions,
  clear actions and preserved conditional weather meaning. Executor inspection
  during refinement remains unobserved. Reviewer screenshot observations are
  in the tool transcript; precise regions are described in persisted notes,
  but screenshot pixel files could not be exported through documented CUA APIs.
- The visual-style pair has valid generated artifacts but no independently
  observed desktop/mobile screenshots. A later revisit failed before pixel
  capture. Those quality checks remain unobserved.
- Photography and integration responses satisfy their observable content
  checks. No-mutation and read-before-recommendation claims lack an independent
  execution trace. The integration and correction cases test shared behavior;
  no specific skill is attributed to them.
- Correction outputs repair the current artifact, identify the conflicting
  synthetic template, seek agreement for a minimal guidance change and leave
  that guidance unchanged. Verification-before-completion chronology remains
  unobserved.

The evidence supports improving trace capture before interpreting process
checks as skill defects. The explicit input hints, simple synthetic records,
one run per configuration, baseline instruction restrictions and unavailable
exact model identity prevent a causal claim about skill effectiveness.

## Method and retained evidence

Execution agents used fresh `fork_turns=none` contexts with no acceptance checks.
Separate reviewer agents inspected outputs and performed independent comparisons.
The same corpus and initial synthetic fixtures were used within each pair.
The warning fixture initially omitted its stated conditional route; the same
fixed synthetic weather condition was supplied to both configurations before
final output and preserved in `supplemental-input.json`. Acceptance checks and
the corpus were not changed after results.

`source-snapshot/` is an inert audit snapshot of public sources, not an active
skill copy. Its hashes match `manifest.json`. `harness/` preserves this run's
preparer and collector; these scripts are run-specific, not a general executor.
No private data was copied, real itinerary was edited, or live skill was changed.
Reviewer fields are distinct from executor facts. No timing, token counts or
exact model IDs were available; they were not estimated.

## Inspect

- Local dashboard: `/skill-regressions` (navigation: Skill evals).
- CLI: `make skill-evals` or `make skill-evals JSON=1`.
- Portable output review: `../../review.html`.
- Regenerate the portable review: `python3 reports/skill-regressions/build_review.py`.
- Each case directory contains original fixtures, delivered artifacts, executor
  logs, independent verification, check grades and reviewer notes.

## Dashboard validation

Seven synthetic contract tests cover unknown/unreviewed states, conclusive
denominators, false pass rejection, reviewer identity, corpus mismatch,
prepared-record exclusion and evidence symlink boundaries. Web typecheck passes.
The live Next route returns HTTP 200 and renders the reviewed data. Native Safari
observations verified case expansion, evidence details and the 390×844 layout;
the comparison table scrolls within its region and case labels wrap. Normal
viewport mode was restored. These are dashboard checks, not substitutes for
the individual itinerary visual checks.
