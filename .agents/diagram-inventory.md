# Diagram inventory — personal-os workspace

Read by the `diagram-flow` skill at Step 1. This file is the repo-specific layer
that the universal skill deliberately does not carry: where diagrams live here,
which renderer consumes them, what gates them, and which source-of-truth
decisions are already settled.

**Orientation, not contract.** Verified 2026-08-28 by running the skill's
bundled checker against each repo. Filenames, counts, and commands drift —
re-verify before relying on an entry.

## Where diagrams live

| Repo | Diagrams | Renderer family | Gate |
| --- | --- | --- | --- |
| `personal-os` | 9 Mermaid fences in 3 files (`ARCHITECTURE.md` ×7, `README.md`, `docs/VISION.md`) | A — GitHub server-side | `make check-mermaid` (`scripts/check_mermaid.py`), wired into `make test`. No `.github/workflows/`, so local-only |
| `repos/portfolio-website` | **25 Mermaid blocks across 17 MDX files** | B/C — client-side `mermaid@11`, `securityLevel: "strict"`, MDX | **none.** `ci.yml` runs tsc/eslint/build and does not touch Mermaid |
| `repos/ai-stock-analysis` | 1, generated | E — model-owned | `architecture-check.yml` runs `sync_architecture.py --check` |

Renderer families are defined in the skill's `references/renderer-contracts.md`.

### Correction, 2026-08-28

The previous inventory recorded portfolio-website as "5 Mermaid blocks across 4
blog MDX files." The real count is 25 across 17. The old figure was hand-counted
against blog posts only and had drifted. Counts in this table now come from the
checker, not from eye.

## Settled decisions — do not re-litigate

- **Every `personal-os` and `portfolio-website` diagram correctly stays plain
  Mermaid.** They have one consumer each and no synchronization requirement. Do
  not propose migrating them to a structured model.
- **No shared Mermaid renderer package across the three repos.** At this scale
  the coupling costs more than it saves. This was evaluated and declined.
- **`scripts/check_mermaid.py` stays a lint, not a parser wrapper.** The two
  bugs that actually shipped here (commit `8a38009`: a literal `\n` in seven
  README skill nodes, and `DEC` assigned to a `classDef` that did not declare
  it) were both syntactically valid Mermaid. `mermaid.parse()` would have passed
  both. See the module docstring.

## Open gaps

- **`portfolio-website` has no diagram gate at all.** A syntax error there
  surfaces only when a reader loads the page and hits the source-code fallback
  in `mermaid-diagram.tsx`. Fix: copy the skill's
  `scripts/check_mermaid.py` into that repo and add it to `ci.yml` — **with
  `--ext md,mdx`**, or it will match zero files and report clean while checking
  nothing. The checker must be a repo-local file; CI cannot reach across the
  submodule boundary into `personal-os/scripts/`.
- **`ai-stock-analysis/architecture.md` emits 18 `<b>` label warnings.** This is
  expected, not a bug: the generator targets a renderer that accepts `<b>`.
  Never copy that markup into a hand-written diagram in another repo — the
  strict-mode renderer in portfolio-website will strip it.

## Per-repo maintenance loops

`ai-stock-analysis` — the one repo on the model-first path:

```text
edit pipeline.json
→ render the SVG in PipelineDiagram (web/components/about/pipeline-diagram.tsx)
→ run scripts/sync_architecture.py
→ run scripts/sync_architecture.py --check
→ inspect/test the affected output
```

Never hand-edit the Mermaid block in `architecture.md` or the diagram component.

`personal-os` — plain Mermaid; the loop is the portability rules plus
`make check-mermaid` (also runs inside `make test`).

`portfolio-website` — plain Mermaid in MDX with no check of any kind. If the
user is editing a diagram there, say so once and offer the gate above rather
than silently relying on eyeballs.
