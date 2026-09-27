# Personal-OS Knowledge Base — Technical Design

**Author:** Codex research  **Status:** Draft  **Last updated:** 2026-09-22

## 1. Context

Personal-OS already uses `docs/` for direction, decisions, designs, analysis, plans, and drafts. The repository now has `docs/INDEX.md`, `docs/knowledge/README.md`, a three-note pilot, and deterministic check/index/eval/graph tooling. The pilot has 24 golden queries (21 positive, 3 negative) plus three answer-level samples. The baseline corpus contains roughly 29k words of Markdown; the new gates cover knowledge-note links, metadata, privacy paths, retrieval, answer coverage, and Mermaid portability, while the broader document tree remains intentionally unmigrated.

The driver is not to increase note volume. The driver is to let an agent find a small amount of trustworthy context with low token cost, while preserving Markdown + Git readability, Obsidian/GitHub visualisation, and reproducible evals.

**Out of scope**

- Moving daily logs, finance, travel, profile, or private idea records from `data/` into `docs/`.
- Making a database, vector index, or embedding store the source of truth.
- Adding frontmatter to every existing document or performing a bulk migration.
- Making an Obsidian graph, Canvas, or web dashboard a canonical data store.
- Building a complete personal search product in this change.

## 2. Scope

| # | Capability | Change | Owner |
|---|---|---|---|
| 1 | Knowledge routing | `docs/INDEX.md` describes document types, ownership, and agent read order | Human-maintained |
| 2 | Evergreen notes | `docs/knowledge/` stores cross-project reusable understanding | Markdown + Git |
| 3 | Note metadata | Only new `docs/knowledge/*.md` notes use the minimal frontmatter contract | `scripts/kb_check.py` |
| 4 | Compact retrieval | Metadata, titles, and headings produce compact catalog/search output | `scripts/kb_index.py` |
| 5 | Views | Markdown links and metadata generate Mermaid/HTML/Obsidian-readable views | Generated |
| 6 | Evals | Static contract checks plus a small golden-query set; LLM judging is sampled only | `scripts/kb_eval.py` |

Existing owners remain unchanged: `VISION.md`, `ROADMAP.md`, `DECISIONS.md`, `analysis/`, `design/`, `plans/`, and `drafts/` represent different lifecycles and should not be forced into one note format.

## 3. Current Architecture

```text
User / Agent
    ├── docs/VISION.md, personal-direction.md     direction
    ├── docs/DECISIONS.md                         settled decisions
    ├── docs/ROADMAP.md + docs/plans/             unfinished work
    ├── docs/design/                              implementation-ready designs
    ├── docs/analysis/                            time-bound evidence
    └── docs/drafts/                              not-yet-published prose

data/ (private) ── daily logs, profile, finance, travel, decisions
market/          ── externally observable facts
repos/notes/     ── public nutrition dataset and notes
```

Current limitations are concrete:

- The broader lifecycle tree still lacks a compact machine catalog; only the pilot `docs/knowledge/` notes are currently indexed.
- Document type is mostly expressed by directory and human convention, not by a checkable status, summary, or freshness signal. New knowledge notes now have those checks; existing lifecycle owners retain their current conventions.
- Mermaid portability is checked repo-wide; general Markdown links, metadata, stale references, and orphan notes are checked only for new knowledge notes so far.
- `docs/analysis/` contains time-bound evidence; without an explicit freshness signal, an old conclusion can look current.

## 4. Proposed Architecture

```text
                         [views / adapters]
                 ┌── Obsidian search + graph + backlinks
                 ├── GitHub Markdown + Mermaid
                 └── optional local knowledge browser
                                ▲
                                │ generated, disposable
        Markdown source ────────┼────────────────────────
        ┌───────────────────────┴───────────────────────┐
        │ docs/INDEX.md                                  │
        │ docs/knowledge/*.md  [NEW]                     │
        │ docs/DECISIONS.md / VISION / ROADMAP           │
        │ docs/design / plans / analysis / drafts        │
        └───────────────────────┬───────────────────────┘
                                │
             ┌──────────────────┼──────────────────┐
             │                  │                  │
        kb_index.py        kb_check.py         kb_eval.py
        compact catalog    links/schema/       golden queries
        + ranked search    freshness/privacy   retrieval metrics
```

> Design intent: use a small routing layer to lead the agent to a few candidate Markdown sections; indexes, graphs, and dashboards are disposable projections that can be deleted, regenerated, and tested.

### 4.1 Content model

`docs/knowledge/` remains flat initially. Directory structure expresses lifecycle; metadata expresses content shape:

| `type` | Purpose | Example |
|---|---|---|
| `concept` | A reusable concept or mental model | source of truth, retrieval budget |
| `howto` | A verified procedure | how to run a repository audit |
| `reference` | Stable facts, conventions, or interfaces | the document routing table |
| `explanation` | Why the system is designed this way | why DB is not the source of truth |
| `research` | A short evidence-backed distillation | a tool or direction assessment |
| `field-note` | An observation, experiment, or belief change | a result from a real trial |

This borrows Diátaxis as a content-shape classifier, not as a rigid folder tree. Diátaxis distinguishes tutorials, how-to guides, reference, and explanation because they serve different information needs, and recommends iterative improvement rather than designing a perfect structure up front. [Diátaxis](https://diataxis.fr/start-here/)

### 4.2 Minimal metadata

New knowledge notes require only:

| Field | Required | Meaning |
|---|---:|---|
| `type` | yes | The content shape above |
| `status` | yes | `draft` / `active` / `superseded` |
| `summary` | yes | One sentence describing the question answered; used for compact retrieval |
| `updated` | yes | Last human confirmation date |
| `review_after` | no | Only for notes that can expire |

Do not require `tags`, `aliases`, `id`, `related`, or nested objects by default. Add them only if the golden eval shows that title, summary, and full-text search are insufficient. This keeps writing from becoming schema entry.

Body rules:

1. Lead with the current answer or understanding.
2. Keep one primary question or concept per note; split notes that are too broad to retrieve independently.
3. Separate facts, personal interpretation, hypotheses, and open questions.
4. Research notes retain sources, retrieval date, and re-verification conditions.
5. Use standard relative Markdown links, not Obsidian-only block references. Obsidian supports both Markdown links and Wikilinks, but documents block references as non-standard Markdown, which harms interoperability. [Obsidian internal links](https://obsidian.md/help/Linking%2Bnotes%2Band%2Bfiles/Internal%2Blinks)

## 5. Agent Retrieval Contract

Default read path:

```text
question
  → docs/INDEX.md: route to the owner
  → compact catalog / kb search: return top 3 candidates
  → read only matched headings or files
  → answer with source path, status, and freshness
```

Initial token policy:

- Do not read all of `docs/` by default.
- Keep `docs/INDEX.md` to one screen; it contains routing and ownership, not long explanations.
- Search output contains only `path | title | type | status | summary | score`.
- Expand at most three candidate notes by default; expand only when evidence conflicts or comparison is required.
- For long source documents, read the matched heading before reading the whole file.
- If no authoritative note is found, say that the knowledge is missing or needs research; do not substitute a similar but unverified note.

Long-context research found that model performance can degrade when relevant information is placed in the middle of a long context; adding documents is not equivalent to adding usable knowledge. The design therefore prefers routing, small context, and cited sources over injecting the whole knowledge base into a prompt. [Lost in the Middle](https://direct.mit.edu/tacl/article/doi/10.1162/tacl_a_00638/119630/Lost-in-the-Middle-How-Language-Models-Use-Long)

## 6. Operational Modules

### `scripts/kb_index.py` — compact index and search

- Read metadata, titles, and headings from `docs/knowledge/*.md`.
- Generate `docs/knowledge/_catalog.md`; this is a generated artifact, not a hand-edited source.
- Provide compact search output; the first version uses deterministic weighting of filename, title, summary, heading, and body without an embedding dependency.
- Ignore a small English stopword list so natural-language questions do not match every note on words such as `what`, `is`, or `the`.
- Require at least 50% of the query's non-stopword terms to overlap before returning a candidate; this lets near-miss queries abstain when they share only generic words.
- If lexical retrieval fails on the golden set, SQLite FTS5 may be added as a query cache; Markdown remains the source of truth.

### `scripts/kb_check.py` — deterministic contract checks

Implemented in the pilot:

- Parse frontmatter and validate required fields and enums.
- Resolve relative Markdown links; warn when a heading anchor is missing.
- Require a replacement link for `status: superseded`.
- Warn when `review_after` has passed; do not silently treat the note as current.
- Reject direct Markdown links into private `data/` paths; semantic copying of private values remains a review responsibility.

Deferred beyond the current graph phase:

- Warn on orphan notes rather than failing; some reference notes legitimately have one-way entry points.

### `scripts/kb_graph.py` — disposable views

- Generate a small Mermaid concept map or link inventory from standard Markdown links.
- Show top-level routes, themes, and key relationships; do not render every note by default.
- Write the ignored `docs/knowledge/_graph.md`; run `make kb-graph` to regenerate and portability-check it.
- Version Mermaid source with Markdown; keep the existing `scripts/check_mermaid.py` / `make check-mermaid` portability gate.
- Treat Obsidian Graph, Backlinks, Properties, and Search as optional adapters, not writing contracts. [Properties](https://obsidian.md/help/Editing%2Band%2Bformatting/Properties) · [Backlinks](https://obsidian.md/help/Plugins/Backlinks) · [Graph view](https://obsidian.md/help/Plugins/Graph%2Bview) · [Search](https://obsidian.md/help/Plugins/Search)

## 7. Trade-offs

| Option | Token / speed | Maintenance | Visualisation | Evals | Decision |
|---|---|---|---|---|---|
| Keep `docs/` + `rg` only | Lowest cost; fast enough for a small corpus | Very low, but memory-dependent | GitHub/Obsidian available | Basic static checks only | v0 baseline |
| Deep folders + frontmatter everywhere | Predictable routing | High migration and schema tax | Easy static-site navigation | Easy to format-check, less value-checking | Reject |
| Pure Zettelkasten / graph-first | Strong discovery | Link upkeep, orphans, and graph noise | Best graph experience | Harder deterministic evals | Not primary structure |
| Vector DB / GraphRAG now | Potential semantic recall | More dependencies, indexing, cost, and opacity | Rich views possible | Requires retrieval benchmarks and index maintenance | Defer |
| **Shallow typed Markdown + route/index + generated views** | **Small candidate context** | **Minimal schema only for new notes** | **Markdown links + Mermaid + Obsidian** | **Static contracts + golden set** | **Recommend** |

Keep graph visualisation as a benefit without making it the only organisation method. GitHub's documentation guidance treats diagrams as complements to text and asks for a clear audience, scope, and acceptance criteria; the graph should therefore be a view, not a second body of truth. [GitHub diagram guidance](https://docs.github.com/en/contributing/writing-for-github-docs/creating-diagrams-for-github-docs)

## 8. Impact, Risks, and Evaluation

| Risk | Mitigation |
|---|---|
| `docs/knowledge/` becomes another dumping ground | Require `type`, `status`, and `summary`; keep exclusions in `INDEX.md` |
| Frontmatter becomes writing tax | Constrain only new knowledge notes; do not migrate existing docs |
| Summary drifts from body | Require `updated`; treat catalog as routing, not fact; sample-review notes |
| Graph becomes dense but unhelpful | Generate local/theme views; warn on orphans; never maintain duplicate graph data |
| Research is cited after expiry | Use `review_after` and return freshness; warn instead of silently deleting |
| LLM judge gives attractive but unstable scores | Use deterministic CI checks; keep LLM eval sampled and diagnostic |
| Private facts are copied into public docs | Enforce source-of-truth and path/privacy checks; keep sensitive facts in `data/` |

### Evals

Do not build a full RAG platform for v1. The current pilot uses `tests/fixtures/kb_queries.yaml` with `query` and `expected_paths`; set `expect_no_match: true` when a query should return no authoritative note. Positive queries may add an `answer`, `required_claims`, `required_citations`, and a repository-relative `scope` of allowed citations. The evaluator checks claim coverage by normalized substring, citation presence by local Markdown link or source path, and scope violations deterministically; it does not pretend this proves truthfulness.

Evaluate in three layers:

1. **Static contract:** metadata, links, freshness, privacy, and generated catalog.
2. **Retrieval:** `route@1`, `hit@3`, no-answer accuracy, source-citation coverage, and avoidance of superseded notes.
3. **Deterministic answer coverage:** required claims, required citations, and citation scope for a small answer fixture.
4. **Answer sample:** a small set of real agent questions scored for context relevance, faithfulness, and answer relevance; these dimensions match the useful separation in RAG evaluation literature without adding RAGAS/ARES as a runtime dependency. [ARES](https://arxiv.org/abs/2311.09476) · [RAG evaluation survey](https://arxiv.org/abs/2405.07437)

The current pilot gate is zero static errors, 100% `route@1` / `hit@3` on 21 positive queries, 100% no-answer accuracy on 3 negative queries, and 100% answer/claim/citation coverage on 3 answer samples. Treat the metric as an initial baseline, not a stable benchmark; continue adding queries from real agent work. The working target is at least 90% `hit@3` plus no confident false matches on negative queries. These are local working thresholds, not external standards. If retrieval fails, improve routing, summaries, titles, and note granularity before adding embeddings.

## 9. Rollout

### Phase 0 — contract cleanup — complete

- Add `docs/INDEX.md` with the source-of-truth matrix and agent read order.
- Remove or update stale references to the deleted public-knowledge plan.
- Keep `.obsidian/` as local view configuration unless a later decision explicitly selects stable settings for sharing.

### Phase 1 — pilot — complete

- Add `docs/knowledge/`.
- Write only 3–5 new notes; do not bulk-migrate old documents.
- Add 3 pilot notes and observe whether queries route to three candidates using title, summary, and deterministic lexical search.

### Phase 2 — deterministic tooling — complete

- Implement `kb_check.py`, `kb_index.py`, and `make kb-check` / `make kb-index`.
- Implement `kb_eval.py` and `make kb-eval` for the pilot golden set.
- Include negative golden queries so missing knowledge is reported as no result rather than a similar-note match.
- Add `kb-check` to `make test`; warnings do not block, while privacy/link/schema errors do.
- Implement `kb_graph.py` and `make kb-graph` for a disposable Mermaid view.

### Phase 3 — eval loop — complete

- Expand the pilot from 3 to 24 golden queries, including near-miss negative queries.
- Run `make kb-eval` when notes or routing contracts change.
- Add deterministic answer-level checks for required claims, citations, and allowed citation scope.

### Phase 4 — scale trigger — deferred

- Evaluate SQLite FTS5 only after the lexical baseline fails measurably; evaluate embeddings only after FTS5 fails.

## 10. Open Questions

1. Should `.obsidian/` remain local and untracked? **Recommendation: yes.** If shared later, commit only reviewed stable settings, not workspace state.
2. Should `docs/INDEX.md` be fully generated? **Recommendation: hand-maintain routing; generate catalog and graph.**
3. Should `DECISIONS.md` become one file per decision? **Recommendation: no for now.** Reopen only if retrieval eval proves the single-file owner is a bottleneck.
4. When should SQLite FTS5 be introduced? **Recommendation: after measured golden-query failure, not because search feels attractive.**
5. Should knowledge notes be bilingual? **Recommendation: follow the repository's English content convention; translate outward-facing content later under `docs/voice-guide.md`.**

## Sources and local evidence

- [Diátaxis — four kinds of documentation](https://diataxis.fr/start-here/)
- [ADR GitHub organization](https://adr.github.io/)
- [Lost in the Middle](https://direct.mit.edu/tacl/article/doi/10.1162/tacl_a_00638/119630/Lost-in-the-Middle-How-Language-Models-Use-Long)
- [GitHub — making content findable in search](https://docs.github.com/en/contributing/writing-for-github-docs/making-content-findable-in-search)
- [Obsidian — Markdown internal links](https://obsidian.md/help/Linking%2Bnotes%2Band%2Bfiles/Internal%2Blinks)
- [Personal-OS architecture and read contracts](../../ARCHITECTURE.md)
- [Personal direction and public knowledge contract](../personal-direction.md)
- [Existing Mermaid portability gate](../../scripts/check_mermaid.py)
- [Existing knowledge-browser plan](../plans/wealth-dashboard.md)
