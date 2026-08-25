---
name: diagram-flow
description: >
  Own the diagram layer across Personal-OS and its submodules — Mermaid blocks in
  Markdown docs, Mermaid in MDX blog posts, and JSON-first pipeline diagrams with
  derived SVG. Use this skill whenever the user asks to add, edit, review, fix, or
  unify a flowchart, architecture diagram, sequence diagram, ER diagram, pipeline
  graph, or Mermaid block; when a diagram renders wrong or renders differently on
  GitHub than locally; when deciding whether a diagram needs a structured source of
  truth instead of hand-written Mermaid; or when setting up diagram validation in CI.
  Also trigger on "the diagram rendering is broken", "add a flowchart",
  "why doesn't this mermaid diagram show up", "let's unify how we draw diagrams".
  Diagram correctness and portability only — it does not own
  commit writing (git-commit) or submodule integration (repo-orchestrator).
allowed-tools: Bash, Read, Glob, Grep, Edit, Write
---

# Diagram & Flow

Two separate questions, answered in this order:

1. **Portability** — will this diagram render correctly where it is consumed?
   Applies to *every* diagram, including one-off ones.
2. **Source of truth** — does this diagram need a structured model behind it?
   Applies once there is a second real consumer or an explicit synchronization
   requirement.

Most real failures in this codebase have been (1), not (2). Do not skip to the
architecture question when the actual bug is a label that renders a literal `\n`.

## Ownership boundary

This skill owns diagram authoring rules, renderer portability, source-of-truth
judgement, and where validation belongs. It does not own commits, submodule
pointers, or domain content.

- Deterministic syntax checking belongs in a **repo-local script + that repo's
  CI**, never in this skill. CI must not depend on an agent being invoked.
  This skill decides *when to run* the checker and *how to read its output*.
- Committing the fix, or bumping a submodule pointer afterwards → hand off to
  `git-commit` / `repo-orchestrator`.
- Never auto-convert a hand-written Mermaid diagram into JSON, and never
  auto-rewrite a complex diagram. Propose; let the user decide.

## Where diagrams live

Inventory snapshot verified 2026-08-18. Re-discover paths, counts, and commands
before relying on them; this table is orientation, not a contract.

| Repo | Diagrams | Renderer | Validation |
| --- | --- | --- | --- |
| `personal-os` | 9 Mermaid fences (`ARCHITECTURE.md` ×7, `README.md`, `docs/VISION.md`) | GitHub server-side Mermaid | `make check-mermaid` (`scripts/check_mermaid.py`), wired into `make test`. No `.github/workflows/` exists, so this is local-only |
| `repos/portfolio-website` | 5 Mermaid blocks across 4 blog MDX files | client-side `mermaid@11`, `securityLevel: "strict"` | `ci.yml` runs tsc/eslint/build — **does not touch Mermaid** |
| `repos/ai-stock-analysis` | 1, generated | `pipeline.json` → layout/load (`web/lib/pipeline.ts`) → SVG (`web/components/about/pipeline-diagram.tsx`) + Mermaid (`architecture.md`) | `architecture-check.yml` runs `sync_architecture.py --check` |

`portfolio-website` is now the one repo with no diagram gate at all: a syntax
error there surfaces only when a reader loads the page and hits the source-code
fallback in `mermaid-diagram.tsx`. `personal-os` is covered by `make test` but
not by CI, because the repo has no CI.

Run `make check-mermaid` before shipping any diagram edit in `personal-os`.
Deliberately a lint, not a parser — see the module docstring for why
`mermaid.parse()` is not the gate here.

## Portability rules

These are the failure modes that have actually shipped here.

- **No `\n` inside a quoted node label.** GitHub's Mermaid does not interpret it
  and renders the literal backslash-n. Use `<br/>`. This shipped broken in
  `personal-os` README (commit `8a38009`, seven skill nodes) and was found by eye,
  not by tooling.
- **In `portfolio-website`, keep label markup to `<br/>`.** Its renderer uses
  `securityLevel: "strict"`, so richer HTML may be stripped or break the parse.
  Do not generalize this rule to every target: the generated
  `ai-stock-analysis/architecture.md` currently uses `<b>...</b>` labels, so
  follow the actual contract of the renderer that consumes the diagram.
- **Every class referenced must have a `classDef`.** A node assigned to an
  undeclared class renders unstyled and looks like a different kind of node. Same
  commit shipped this too (`DEC` missing from the `data` classDef).
- **A diagram destined for GitHub must be checked as GitHub renders it**, not
  only in a local preview. GitHub pins its own Mermaid version; newer syntax can
  fail there while working locally.
- **portfolio-website diagrams have no build-time gate.** A syntax error is
  caught at runtime and hidden behind the source-code fallback in
  `mermaid-diagram.tsx`. Parse-check before shipping a post.

## Source of truth

```text
canonical JSON → SVG/UI renderer
               → Mermaid/document renderer
```

Never make Mermaid the canonical source. Do not build a Mermaid → JSON parser as
the default workflow: Mermaid syntax is presentation-oriented and can lose
domain semantics, layout intent, or metadata. If a Mermaid-only diagram must be
migrated, manually reconstruct and review the structured model, then regenerate
the Mermaid from it.

A minimal canonical model looks like this — domain meaning only, no coordinates:

```json
{
  "schemaVersion": 1,
  "stages": [
    { "id": "ingest", "label": "Ingest" },
    { "id": "score", "label": "Score" }
  ],
  "nodes": [
    { "id": "raw_prices", "stage": "ingest", "label": "Raw prices", "tone": "data" },
    { "id": "risk_checker", "stage": "score", "label": "RiskChecker", "tone": "agent" }
  ],
  "edges": [
    { "from": "raw_prices", "to": "risk_checker", "kind": "flow" }
  ]
}
```

Layout coordinates, theme classes (color/tone → CSS), and Mermaid node shapes are
all derived from this at render time — never stored back into it. A schema version
is appropriate for a new persisted/shared model; for an existing model, inspect
its compatibility contract and plan any versioning migration separately from a
small diagram edit.

### Stay with plain Mermaid when

A one-off diagram with no reuse and no expected edits (a single Mermaid block in
a README or a blog post explaining a concept once) doesn't need a JSON source of
truth — draw the Mermaid directly, and apply the portability rules above. Reach
for the canonical-model workflow once a diagram has a second consumer (UI + docs)
or must stay synchronized with code. Repeated edits alone are a signal to inspect
the boundary, not an automatic migration trigger.

By this test, **every current `personal-os` and `portfolio-website` diagram
correctly stays plain Mermaid.** Do not propose migrating them. Do not extract a
shared Mermaid renderer package across the three repos — the coupling costs more
than it saves at this scale.

## Workflow

1. **Inspect before designing.** Find the existing JSON, types, renderer,
   Mermaid/document generator, generated files, and CI checks. Reuse the
   project's domain vocabulary and conventions.
2. **Establish the canonical model.** Give nodes and stages stable IDs. Keep
   domain meaning (labels, roles, states, edge semantics) separate from
   renderer-specific coordinates and theme classes. For a new persisted/shared
   model, add a schema version; for an existing model, preserve its contract and
   do not introduce versioning as incidental diagram work.
3. **Validate the model.** Check JSON syntax, required fields, unique IDs,
   references, and any domain invariants. Add runtime schema validation when
   there are multiple consumers or frequent edits; do not invent a broad
   generic schema for a single consumer.
4. **Render each output from the model.** Prefer a pure layout function and a
   renderer that owns its theme and accessibility. The SVG/UI renderer and the
   Mermaid renderer may have different layout details, but neither owns the
   source data.
5. **Synchronize and verify.** Run the project's generator, then its check mode
   (for example, `--check`). Run focused type/tests and inspect the rendered UI
   when visual changes matter. Add a read-only CI check for generated docs when
   drift would be costly.
6. **Keep abstraction proportional.** With one consumer, keep types and layout
   local. After a second real consumer appears, extract only the proven,
   framework-independent model/layout seam into a package. Keep React, Next.js,
   Tailwind, and product-specific tones in adapters.

## Review output

For a review or fix, report the target file and consuming renderer first, then:

1. portability findings and their severity;
2. the source-of-truth decision and the canonical file to edit;
3. exact validation commands and their results;
4. changed/generated files, plus any `git-commit` or `repo-orchestrator`
   handoff.

Keep the report scoped to diagram correctness. Do not turn a diagram review into
a domain-content review or a commit operation.

## Editing rules

- Edit the canonical JSON, not generated Mermaid or SVG output.
- Keep IDs deterministic and labels escaped by the target renderer.
- Make fan-out, convergence, bidirectional exchange, and dashed/conditional
  edges explicit in the model instead of inferring them from coordinates.
- Prefer automatic layout over hand-tuned coordinates when the graph changes.
- A first-party SVG/UI renderer should emit a `<title>` and `<desc>` and expose
  each canonical node `id` as a stable DOM anchor (for example,
  `data-node-id`) so tests and deep links can target it. A Mermaid-generated SVG
  is renderer-owned: provide the accessible name/description at its wrapper or
  figure level, and only require per-node DOM anchors when that renderer supports
  a reliable canonical-ID mapping.
- Do not add a parser, package, schema, or visual QA harness solely because it
  sounds reusable; tie each addition to a real consumer or failure mode.

## Anti-patterns

- Hand-authoring long SVG path data for a graph that has automatic layout
  available — regenerate paths from the model instead of hand-tuning points.
- Encoding layout position (x/y, row/column index) as domain state in the
  canonical JSON — position is a render concern, derived by the layout
  function, not stored.
- Baking a specific renderer's theme classes (Tailwind classes, Mermaid
  `classDef` names) into node objects — store a semantic `tone`/`role` and let
  each renderer map it to its own styling.
- Writing a bespoke Mermaid string parser to "sync back" edits made directly
  in generated `.md` files — edits belong in the JSON; treat generated Mermaid
  as read-only output.
- Proposing a structured source of truth for a diagram that has exactly one
  consumer and no sync requirement.

## Per-repo maintenance loops

`ai-stock-analysis` — the one repo already on the JSON-first path:

```text
edit pipeline.json
→ render the SVG in PipelineDiagram (web/components/about/pipeline-diagram.tsx)
→ run scripts/sync_architecture.py
→ run scripts/sync_architecture.py --check
→ inspect/test the affected output
```

Never hand-edit the Mermaid block in `architecture.md` or the diagram component.

`personal-os` — plain Mermaid, so the loop is the portability rules plus
`make check-mermaid` (also runs inside `make test`).

`portfolio-website` — plain Mermaid in MDX with **no check of any kind**. If the
user is editing a diagram there, say so once and offer to port
`scripts/check_mermaid.py` into that repo's `ci.yml`, rather than silently
relying on eyeballs. The checker must be a repo-local file there too — CI cannot
reach across a submodule boundary into `personal-os/scripts/`. The current
checker defaults to tracked `*.md`; a portfolio copy must also discover `*.mdx`
or pass the blog MDX paths explicitly, otherwise it will silently miss these
diagrams.

Filenames and commands drift. Discover them in the repo rather than copying this
section literally.
