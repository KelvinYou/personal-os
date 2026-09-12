---
name: diagram-flow
description: >
  Own the diagram layer in any repository — Mermaid blocks in Markdown, Mermaid in
  MDX or other JSX-flavored docs, and model-first pipeline diagrams with derived
  SVG. Use this skill whenever the user asks to add, edit, review, fix, or unify a
  flowchart, architecture diagram, sequence diagram, ER diagram, pipeline graph, or
  Mermaid block; when a diagram renders wrong, renders differently on GitHub than
  locally, or renders differently in CI than in a local preview; when deciding
  whether a diagram needs a structured source of truth instead of hand-written
  Mermaid; or when setting up diagram validation in CI. Also trigger on "the
  diagram rendering is broken", "add a flowchart", "why doesn't this mermaid
  diagram show up", "the arrows are wrong", "let's unify how we draw diagrams",
  and on any request to change a file that contains a ```mermaid fence, even when
  the user does not use the word "diagram". Diagram correctness and portability
  only — it does not own commit writing or submodule integration.
allowed-tools: Bash, Read, Glob, Grep, Edit, Write
---

# Diagram & Flow

Two separate questions, answered in this order:

1. **Portability** — will this diagram render correctly where it is consumed?
   Applies to *every* diagram, including one-off ones.
2. **Source of truth** — does this diagram need a structured model behind it?
   Applies only once there is a second real consumer or an explicit
   synchronization requirement.

Most real diagram failures are (1), not (2). Do not escalate to the architecture
question when the actual bug is a label that renders a literal `\n`.

## Ownership boundary

This skill owns diagram authoring rules, renderer portability, source-of-truth
judgement, and where validation belongs. It does not own commits, submodule
pointers, or domain content.

- Deterministic syntax and rule checking belongs in a **repo-local script plus
  that repo's CI**, never in this skill. CI must not depend on an agent being
  invoked. This skill decides *when to run* the checker and *how to read* its
  output. `scripts/check_mermaid.py` is bundled here to be **copied into** a
  target repo, not to be run across a repo boundary.
- Committing the fix, or bumping a submodule pointer afterwards, hands off to
  the repository's commit skill (`git-commit` where available).
- Never auto-convert a hand-written Mermaid diagram into a structured model, and
  never auto-rewrite a complex diagram. Propose; let the user decide.

## Step 1 — Establish the render target

Every portability rule below is conditional on **which renderer consumes the
diagram**. Never apply a rule without knowing the target. Determine it before
editing anything.

Check for a declared inventory first:

```bash
cat .agents/diagram-inventory.md 2>/dev/null
```

If that file exists, it is the repository's own record of where diagrams live,
which renderer consumes each one, what gates them, and which source-of-truth
decisions have already been settled. **Treat settled decisions as settled** — do
not re-litigate a migration the inventory says was already considered and
declined.

If it does not exist, discover the target:

```bash
# Where are the diagrams?
grep -rln '```mermaid' --include='*.md' --include='*.mdx' . | grep -v node_modules

# Which renderer consumes them?
grep -rn 'mermaid' package.json 2>/dev/null           # client-side render → check version + securityLevel
grep -rn 'securityLevel\|mermaid.initialize' -r src app components 2>/dev/null

# What gates them?
ls .github/workflows/ 2>/dev/null
grep -rn 'mermaid' Makefile .github/workflows/ 2>/dev/null
```

Then classify the target against `references/renderer-contracts.md`, which gives
the label-markup contract, version pinning behaviour, and failure mode for each
renderer family. Read that file before applying any rule marked target-specific.

When a repo has diagrams and **no gate of any kind**, say so once and offer to
install `scripts/check_mermaid.py` into that repo plus its CI. Do not silently
rely on eyeballs, and do not reach across a repository or submodule boundary to
a checker that lives somewhere else — CI cannot follow that path.

## Step 2 — Portability rules

These are observed failure modes, not theory. Each has shipped in real
repositories.

**Universal — apply to every target:**

- **No `\n` inside a quoted node label.** Server-side renderers do not interpret
  it and emit a literal backslash-n. Use `<br/>`. This class of bug is
  syntactically valid Mermaid, so a `mermaid.parse()` gate will not catch it.
- **Every class referenced must have a `classDef`.** A node assigned to an
  undeclared class renders unstyled and reads as a different kind of node. Also
  syntactically valid, also invisible to a parser gate.
- **Check the diagram as its consumer renders it**, not only in a local preview.
  Renderers pin their own Mermaid version; newer syntax can fail on the target
  while working locally.
- **Match label markup to the renderer's contract, not to habit.** `<br/>` is
  safe everywhere. Richer HTML (`<b>`, `<i>`, entities) is target-specific — see
  `references/renderer-contracts.md`. Never generalize one target's tolerance to
  another target in the same repository.

**Target-specific — look up before applying:**

- A client-side renderer configured with `securityLevel: "strict"` may strip or
  fail on markup a server-side renderer accepts.
- A renderer behind a source-code fallback hides syntax errors at runtime: the
  page still loads, showing raw source instead of a diagram. Parse-check before
  shipping.
- A generated Mermaid block is read-only output. Edit its model, never the block.

## Step 3 — Source of truth

```text
canonical model → SVG/UI renderer
                → Mermaid/document renderer
```

Never make Mermaid the canonical source. Do not build a Mermaid → model parser
as the default workflow: Mermaid syntax is presentation-oriented and loses
domain semantics, layout intent, and metadata. If a Mermaid-only diagram must be
migrated, manually reconstruct and review the structured model, then regenerate
the Mermaid from it.

### The test

Stay with plain Mermaid when the diagram has **one consumer and no sync
requirement** — a single block in a README or a post explaining a concept once.
Draw it directly and apply the portability rules.

Reach for a canonical model once the diagram has **a second real consumer** (UI
plus docs) or **must stay synchronized with code**.

Repeated edits alone are a signal to inspect the boundary, not an automatic
migration trigger. Most diagrams in most repositories correctly stay plain
Mermaid. **Do not propose a migration that this test does not demand** — an
unprompted "you should move this to JSON" on a one-off README diagram is the
most common way this skill fails.

For the model shape, validation approach, and migration procedure, read
`references/canonical-model.md`. Read it only when the test above has actually
selected the model-first path.

## Step 4 — Workflow

For a **plain-Mermaid** target:

1. Establish the render target (Step 1).
2. Apply the portability rules (Step 2).
3. Run the repo's gate. If none exists, run the bundled checker directly and
   offer to install it:
   ```bash
   python3 <diagram-flow-skill>/scripts/check_mermaid.py [PATH ...]
   ```
4. Report findings (Step 5).

For a **model-first** target:

1. **Inspect before designing.** Find the existing model, types, renderer,
   document generator, generated files, and CI checks. Reuse the project's
   domain vocabulary and conventions.
2. **Establish the canonical model.** Stable IDs for nodes and stages. Domain
   meaning separate from renderer coordinates and theme classes.
3. **Validate the model.** Syntax, required fields, unique IDs, references,
   domain invariants.
4. **Render each output from the model.** A pure layout function plus a renderer
   that owns its theme and accessibility.
5. **Synchronize and verify.** Run the generator, then its check mode (for
   example `--check`). Run focused type checks and tests; inspect the rendered
   UI when visual changes matter.
6. **Keep abstraction proportional.** With one consumer, keep types and layout
   local. Extract a shared package only after a second real consumer appears,
   and only the proven framework-independent seam.

## Resolving `<diagram-flow-skill>`

Resolve in this order, first hit wins:

1. `${CLAUDE_PLUGIN_ROOT}/skills/diagram-flow` — installed as a plugin
2. `.agents/skills/diagram-flow` — project or user-level install
3. the directory this `SKILL.md` was loaded from

If none resolve, apply the rules by inspection; the checker is an optimisation,
not a dependency.

## Step 5 — Review output

Report the target file and its consuming renderer first, then:

1. portability findings and their severity;
2. the source-of-truth decision and the canonical file to edit;
3. exact validation commands and their results;
4. changed or generated files, plus any commit handoff.

Keep the report scoped to diagram correctness. Do not turn a diagram review into
a domain-content review or a commit operation.

## Editing rules

- Edit the canonical source, not generated Mermaid or SVG output.
- Keep IDs deterministic and labels escaped for the target renderer.
- Make fan-out, convergence, bidirectional exchange, and dashed/conditional
  edges explicit in the model instead of inferring them from coordinates.
- Prefer automatic layout over hand-tuned coordinates when the graph changes.
- A first-party SVG/UI renderer should emit `<title>` and `<desc>` and expose
  each canonical node `id` as a stable DOM anchor (for example `data-node-id`)
  so tests and deep links can target it. A Mermaid-generated SVG is
  renderer-owned: provide the accessible name and description at its wrapper or
  figure level, and require per-node anchors only when that renderer supports a
  reliable canonical-ID mapping.
- Do not add a parser, package, schema, or visual QA harness solely because it
  sounds reusable; tie each addition to a real consumer or failure mode.

## Anti-patterns

- Hand-authoring long SVG path data for a graph that has automatic layout
  available — regenerate paths from the model instead of hand-tuning points.
- Encoding layout position (x/y, row or column index) as domain state in the
  canonical model — position is a render concern, derived by the layout
  function, not stored.
- Baking a specific renderer's theme classes (utility CSS classes, Mermaid
  `classDef` names) into node objects — store a semantic `tone` or `role` and
  let each renderer map it to its own styling.
- Writing a bespoke Mermaid string parser to "sync back" edits made directly in
  generated files — edits belong in the model; generated Mermaid is read-only.
- Proposing a structured source of truth for a diagram that has exactly one
  consumer and no sync requirement.
- Copying a portability rule from one render target to another without checking
  that target's contract.
- Pointing a repository's CI at a checker that lives in a different repository
  or above a submodule boundary.

## Recording what you learn

When a repository's diagram layout, renderers, gates, or source-of-truth
decisions are worth remembering, write them to `.agents/diagram-inventory.md` in
that repository so the next invocation starts from Step 1 with real data.
Timestamp it and mark it as orientation, not contract — filenames and commands
drift, so re-verify before relying on any entry.
