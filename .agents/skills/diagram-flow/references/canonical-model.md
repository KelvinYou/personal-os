# Canonical model

Read this only after the source-of-truth test in `SKILL.md` Step 3 has selected
the model-first path — that is, the diagram has a second real consumer or must
stay synchronized with code. For a one-off diagram, this file is the wrong
answer.

## Contents

- [Shape](#shape)
- [What never goes in the model](#what-never-goes-in-the-model)
- [Validation](#validation)
- [Migrating an existing Mermaid diagram](#migrating-an-existing-mermaid-diagram)
- [Rendering](#rendering)
- [Keeping abstraction proportional](#keeping-abstraction-proportional)

---

## Shape

Domain meaning only, no coordinates:

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

Adapt the vocabulary to the project's domain — `stages` might be `layers`,
`phases`, or `swimlanes`. Reuse the names the codebase already uses rather than
importing this file's terms.

`tone` is semantic, not visual: `data`, `agent`, `external`, `deprecated`. Each
renderer maps tone to its own styling. A node must never carry a utility CSS
class or a Mermaid `classDef` name.

`kind` on an edge carries semantics: `flow`, `conditional`, `bidirectional`,
`async`. Fan-out, convergence, and dashed edges are explicit in the model, never
inferred from geometry at render time.

**Schema versioning.** Add `schemaVersion` to a new persisted or shared model.
For an existing model, read its compatibility contract first and plan any
versioning migration as its own change — never introduce versioning as
incidental work inside a small diagram edit.

## What never goes in the model

| Belongs in the model | Belongs in the renderer |
| --- | --- |
| `id`, `label`, `stage` | x/y coordinates |
| `tone` / `role` | CSS classes, `classDef` names |
| edge `kind` | arrow shape, dash pattern |
| domain invariants | node shape, corner radius |
| ordering that is domain-meaningful | row/column index |

Storing a row index or a color in the model is the failure that makes a
model-first setup no better than hand-written Mermaid — the model stops being
the domain description and becomes a second, worse layout language.

## Validation

Check in this order:

1. Model file parses.
2. Required fields present on every node, stage, edge.
3. IDs unique within their collection.
4. Every `edge.from` / `edge.to` and every `node.stage` resolves.
5. Domain invariants — no orphan nodes, no cycles where the domain forbids them,
   every stage populated.

Add runtime schema validation when there are multiple consumers or frequent
edits. Do not invent a broad generic schema for a single consumer.

## Migrating an existing Mermaid diagram

**Never automate this.** Mermaid is presentation-oriented; a parser round-trip
loses domain semantics, intended grouping, and metadata that was never encoded
in the syntax to begin with.

1. Read the Mermaid block and write the model by hand.
2. Have the user confirm the domain reading — especially stage assignment and
   edge kinds, which are exactly the information Mermaid does not carry.
3. Generate Mermaid from the model.
4. Diff generated output against the original. Differences are expected;
   confirm each is an improvement or neutral, not a lost distinction.
5. Replace the original and mark it generated.
6. Add the generator's `--check` mode to CI in the same change, or the two
   representations drift immediately.

Do not build a Mermaid → model parser as a reusable tool. Migration is a
one-time manual act per diagram.

## Rendering

One pure layout function; one renderer per output. Neither renderer owns the
source data, and the two may legitimately lay out differently.

For a first-party SVG or UI renderer:

- emit `<title>` and `<desc>` for accessibility;
- expose each canonical node `id` as a stable DOM anchor, for example
  `data-node-id`, so tests and deep links can target it;
- prefer automatic layout over hand-tuned coordinates once the graph changes
  with any regularity.

For a Mermaid-generated SVG, the renderer owns the DOM. Provide the accessible
name and description at the wrapper or figure level, and require per-node
anchors only when the renderer supports a reliable canonical-ID mapping.

## Keeping abstraction proportional

With one consumer, keep types and layout local to that consumer. After a second
real consumer appears, extract only the proven, framework-independent
model-and-layout seam into a package. Framework bindings, design-system tones,
and product-specific concerns stay in adapters.

Do not extract a shared renderer package across repositories at small scale —
the coupling costs more than it saves, and the test for extracting the skill's
own abstractions is the same test it applies to diagrams.
