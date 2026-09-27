# Knowledge Notes

This directory contains evergreen, cross-project notes that are useful after the immediate task has ended. It is intentionally shallow; use note metadata and links before adding more folders.

## What belongs here

- Concepts, explanations, references, verified how-to procedures, research distillations, and field notes.
- One primary question or concept per note.
- Claims separated from evidence, interpretation, and open questions.

## What does not belong here

- Daily logs, personal profile, finance, travel details, or private idea records; those belong in `data/`.
- Unresolved implementation checklists; those belong in `docs/ROADMAP.md` or `docs/plans/`.
- Time-bound evidence that has not been distilled; keep it in `docs/analysis/` and link to it.

## Minimal frontmatter

New notes use this small contract:

```yaml
---
type: concept
status: draft
summary: One sentence describing what this note answers
updated: 2026-09-22
# review_after: 2027-01-01
---
```

Supported types are `concept`, `howto`, `reference`, `explanation`, `research`, and `field-note`. Supported statuses are `draft`, `active`, and `superseded`.

Use standard relative Markdown links. Keep indexes, graphs, and dashboards generated or disposable; the note remains the source of truth.

Run `make kb-check` before publishing a note, `make kb-index` to refresh the
local catalog, `make kb-eval` after changing note titles, summaries, or routing
rules, and `make kb-graph` to refresh the disposable Mermaid view.

The retrieval fixture lives at `tests/fixtures/kb_queries.yaml`. Positive cases
use `expected_paths`; intentional abstentions use `expect_no_match: true`. A
small answer sample may additionally declare `answer`, `required_claims`,
`required_citations`, and repository-relative `scope` for deterministic
coverage checks.
