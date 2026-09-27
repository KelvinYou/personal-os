# Personal-OS Documentation Index

This directory is the durable, agent-readable knowledge layer of Personal-OS. It is not the owner of private personal state; private facts remain under `data/`.

## Start here

- System direction: [`VISION.md`](VISION.md); owner preferences live in `data/reference/personal-direction.md` when provided
- Architecture and invariants: [`../ARCHITECTURE.md`](../ARCHITECTURE.md)
- Settled decisions: [`DECISIONS.md`](DECISIONS.md)
- Unfinished work: [`ROADMAP.md`](ROADMAP.md) and [`plans/`](plans/)
- Implementation-ready designs: [`design/`](design/)
- Time-bound evidence: [`analysis/`](analysis/); check each document's re-verification date before citing it
- Evergreen, cross-project notes: [`knowledge/`](knowledge/)
- External facts: [`../market/`](../market/) and public submodules; do not copy private values here
- Stock pipeline, individual-ticker research, and backtest results: [`../repos/ai-stock-analysis/docs/`](../repos/ai-stock-analysis/docs/) and [`../repos/ai-stock-analysis/reports/analysis/`](../repos/ai-stock-analysis/reports/analysis/)

## Source-of-truth matrix

| Question | Canonical owner | Do not duplicate into `docs/` |
|---|---|---|
| System invariants and data-flow contracts | `ARCHITECTURE.md` | Design prose that contradicts them |
| Product direction | `docs/VISION.md` | A second active direction document |
| Settled trade-offs | `docs/DECISIONS.md` | Reopening them without a new decision |
| Unfinished implementation work | `docs/ROADMAP.md` and linked plans | A second checklist in a design doc |
| Public external facts | `market/` or owning public submodule | Personal holdings, targets, or transactions |
| Stock pipeline code, ticker analyses, and backtest records | `repos/ai-stock-analysis/` | Duplicate stock research artifacts in Personal-OS `reports/analysis/` |
| Personal wealth and cross-asset allocation analysis | `data/analysis/` and `.agents/skills/wealth-manager` | Recasting portfolio planning as stock-pipeline research |
| Daily state, profile, finance, travel, ideas | Owner's independent private `data/` repository | Any copy of the private source text |
| Evergreen understanding | `docs/knowledge/` | Time-series logs or stale research without provenance |

## Agent read order

1. Read this index and choose the owner.
2. Search the owner's directory by title, summary, or heading.
3. Read only the relevant heading or the smallest complete note.
4. Return the source path, document status, and freshness/re-verification date when present.
5. If no authoritative source exists, say that the knowledge is missing and propose research; do not infer a new contract from a nearby document.

## Knowledge-note contract

New files under `docs/knowledge/` are small, concept-oriented notes. They require `type`, `status`, `summary`, and `updated` frontmatter. Add `review_after` only when the note can expire. Use standard relative Markdown links so GitHub, local tools, and Obsidian can read the same source.

Existing root documents and lifecycle directories keep their current owners. Do not bulk-migrate them just to make the tree look uniform.

## Privacy and lifecycle

- `docs/` is shareable repository knowledge. Older analyses and plans may describe the original author; never treat those examples as a fork owner's facts or goals.
- Private personal facts belong in `data/`; public abstractions may link to them conceptually without copying the values.
- Drafts are not evergreen knowledge until their claims are resolved and their owner is clear.
- Superseded notes should point to their replacement rather than silently disappearing.

## Views

Obsidian search/graph/backlinks and generated Mermaid or HTML pages are views. Markdown files and their links remain the source of truth; generated views must be disposable and reproducible.
