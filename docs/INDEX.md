# Personal-OS Documentation Index

This directory is the durable, agent-readable knowledge layer of Personal-OS. It is not the owner of private personal state; private facts remain under `data/`.

## Start here

- System direction: [`VISION.md`](VISION.md); owner preferences live in `data/reference/personal-direction.md` when provided
- Architecture and invariants: [`../ARCHITECTURE.md`](../ARCHITECTURE.md)
- Settled decisions: [`DECISIONS.md`](DECISIONS.md)
- Unfinished work: [`ROADMAP.md`](ROADMAP.md) and [`plans/`](plans/)
- Interface design: [`design-system.md`](design-system.md); applications and skills own their implementation assets; start reuse with [the catalog](design/interface-patterns.md) and the local `/design-system` reference
- Travel source/build contract: [`design/travel-md-html-build.md`](design/travel-md-html-build.md); content remains in private `data/travel/`
- Skill regression evidence: [`../reports/skill-regressions/README.md`](../reports/skill-regressions/README.md); synthetic cases, independent reviews and the local `/skill-regressions` view
- Implementation-ready designs: [`design/`](design/)
- Office collaboration: [task, handoff and managed-team contract](design/office-collaboration.md); private board, advisory resource claims and fresh read-only teams
- Virtual office: [role wardrobes and character preview](design/office-character-styles.md), [modern garden town](design/office-garden-town.md), [courtyard studio and skill neighborhoods](design/office-courtyard.md), [host movement and cameras](design/office-player-controls.md), [action inbox and persistent results](design/office-workbench.md), [implementation phases](plans/virtual-office.md), [observation design](design/ai-office-monitor.md) and [direct web tasks](design/office-direct-tasks.md) and [fixed skill employees](design/office-skill-employees.md); local Codex records, separate demo mode and opt-in owned execution
- Office posts: [private carousel reader and library board](design/office-posts.md); content remains under `data/posts/`, accessed only through local private endpoints
- Time-bound evidence: [`analysis/`](analysis/); check each document's re-verification date before citing it
- Evergreen, cross-project notes: [`knowledge/`](knowledge/)
- 3D scenes: [scene standard](design/3d-scene-standard.md) (units, colour, lighting, palettes, acceptance) for any runtime 3D change; [AI assisted asset workflow](knowledge/ai-3d-asset-workflow.md) for generating an asset; private scene evidence remains in the project record
- Video editing reference: [`workflow and creative acceptance`](knowledge/video-editing-workflow.md), then [`HDR to SDR and export checks`](knowledge/hdr-to-sdr-video.md); personal cases belong under `data/reference/video-editing/`
- Authored artifacts: [shared design and delivery](artifact-design-guide.md), with private `data/reference/artifact-style.md` for selected appearance; [presentation format](presentation-guide.md) for PPT. Post identity is not inherited by other media.
- Social post graphics: [visual guide](social-post-visual-guide.md) for XHS and TikTok identity, platform layouts, page types, restraint rules and review criteria; workflow in the `social-post` skill; inherits shared artifact design; private copy and examples remain under `data/posts/`
- External facts: [`../market/`](../market/) and public submodules; do not copy private values here
- Stock pipeline, individual-ticker research, and backtest results: [`../repos/ai-stock-analysis/docs/`](../repos/ai-stock-analysis/docs/) and [`../repos/ai-stock-analysis/reports/analysis/`](../repos/ai-stock-analysis/reports/analysis/)

## Source-of-truth matrix

| Question | Canonical owner | Do not duplicate into `docs/` |
|---|---|---|
| System invariants and data-flow contracts | `ARCHITECTURE.md` | Design prose that contradicts them |
| COROS live connection and evidence normalization | [`design/coros-official-mcp.md`](design/coros-official-mcp.md), official provider/client schemas | Password-client setup or a second live health source |
| Authored artifact design and delivery | [`artifact-design-guide.md`](artifact-design-guide.md); private appearance in `data/reference/artifact-style.md` | Duplicate palette/style rules in medium adapters |
| Presentation format | [`presentation-guide.md`](presentation-guide.md) | Social account identity or portrait carousel constraints |
| Post format and identity | [`social-post-visual-guide.md`](social-post-visual-guide.md); private `data/posts/brand.md` and `README.md` | Account identity in general-purpose artifact defaults |
| Shared interface design | [`design-system.md`](design-system.md) | Repeated principle lists in individual skills; personal preferences |
| 3D scene conventions and palettes | [`design/3d-scene-standard.md`](design/3d-scene-standard.md) | Per-design-doc lighting, colour or unit rules |
| Proposed UI artifact enforcement | [`design/ui-artifact-enforcement.md`](design/ui-artifact-enforcement.md) — draft review; not an active gate | Claiming configured hooks or provenance metadata prove runtime enforcement |
| Product direction | `docs/VISION.md` | A second active direction document |
| Settled trade-offs | `docs/DECISIONS.md` | Reopening them without a new decision |
| Unfinished implementation work | `docs/ROADMAP.md` and linked plans | A second checklist in a design doc |
| Public external facts | `market/` or owning public submodule | Personal holdings, targets, or transactions |
| Stock pipeline code, ticker analyses, and backtest records | `repos/ai-stock-analysis/` | Duplicate stock research artifacts in Personal-OS `reports/analysis/` |
| Personal wealth and cross-asset allocation analysis | `data/analysis/` and `.agents/skills/wealth-manager` | Recasting portfolio planning as stock-pipeline research |
| Finance dashboard and transaction evidence | [`design/finance-overview.md`](design/finance-overview.md); balances and journal under private `data/finance/` | Inferring investment returns from balance growth |
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
