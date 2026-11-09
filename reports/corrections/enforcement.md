# Correction enforcement table

Pairs each standing rule with what enforces it, and audits the correction history for
recurring mistake classes. Ladder (AGENTS.md § "Learn from Corrected Outputs"):
architecture → types/schema → lint/hook/CI → behavior test → docs last.

A class counts once it has happened twice. A rule that recurs while only docs enforce it is a
repeat: escalate it. Drop a rule once its mistake can no longer happen.

Every queue entry carries `**Class:** <slug>`. `python3 scripts/session_eval.py --corrections`
(and the `corrections` block in each `make eval-rollup` file, shown on `/eval-rollup`) counts per
month how many entries reuse an earlier class. A falling repeat rate after an escalation is the
evidence that the escalation worked; a flat one means it didn't.

## Rule → enforcer

| Rule | Enforced by | Level | Proven on a real past mistake? |
| --- | --- | --- | --- |
| `web/` UI uses design primitives; no native controls, page hex colours | `scripts/design_rules_check.py` ratchet in `make design-check` / `make test`; `scripts/design_hook.sh` Pre/PostToolUse hook | lint + hook | Yes — baseline holds the 2026-11-04 office/home violations; new ones fail |
| Daily-log frontmatter matches the template | `scripts/lib/schema.py` | schema | Not recorded |
| AGENTS.md directory block points at real paths | `make doctor` (`test -e` per line) | CI-style check | Not recorded |
| Travel plan internal consistency | `make travel-lint`; each rule maps to `tests/fixtures/travel_known_defects.yaml` | lint + fixture | Yes — rules are derived from known defects |
| Knowledge notes follow the contract | `make kb-check` | lint | Not recorded |
| `web/public/flows.json` matches the Makefile/scripts | `make doctor` drift warning | check (warning) | Not recorded |
| A `web/` change is proven in the real app before "done" | `verify-web` skill + feature map | docs (skill) | n/a — new; no automated gate |
| Shared 3D style: decks include real 3D artwork | `make deck-lint` DECK-ART rule (`scripts/lib/deck.py`); 3D finish and topic fit remain docs (`docs/artifact-design-guide.md`, `docs/presentation-guide.md`) | lint + docs | Yes — fails the 2026-11-06 deck (12 slides, 0 pictures) |
| Each content slide has one dominant element (≥ 3× body text or ≥ 25% visual) | `make deck-lint` FOCAL rule; thresholds under `presentation:` | lint | Yes — fails v4 slides 4 / 11 / 12 and v3 slides 4 / 11 |
| Slide body text ≥ 18 pt (footer band excluded) | `make deck-lint` BODY rule; `body_min_pt` under `presentation:` | lint | Yes — fails the 11-06 deck (8 slides at 15–17.25 pt), v3 (7 slides) and a 12–16 pt nutrition handbook (9 slides); v4 (22–24 pt) passes |
| Deck composition rhythm (no 3 consecutive same layout; ≤ 1/3 per layout) | `make deck-lint` RHYTHM rule; layout derived from PPTX geometry (not self-reported) | lint | Yes — fails v4 (`art-C/text-C` 7/11, slides 5–8 in a row), v3 (`art-R/text-L` 6/11) and the 11-06 deck (`text/text-C` 10/11) |
| A failing deck is not delivered | `scripts/deck_hook.py` Claude Code Stop hook: lints every `.pptx` changed this session and blocks the stop once; exemptions only via `deck_lint.exempt` + `reason` in `production.json` | hook | Yes — blocks a fresh copy of the v4 deck (selftest 2026-11-08). Also wired globally in `~/.claude/settings.json` (`--global`: scans the session's project, skips personal-os) so decks built in other repos are gated too. Gap: Codex has no equivalent hook yet |
| Standalone HTML reuses the design system | `make ui-build` (embeds current `design-controls.css` + `templates/ui/standalone.css` with digests) and `make ui-check` (fails missing / edited / stale / out-of-order assets, network code, missing local files); routed by `ui-design-rules`, `docs/dev-sop.md`, AGENTS.md | lint (CLI) | Yes — fails all four real 10-27 pages (comment-only reuse claim, untagged stale copy) and a labelled reconstruction of the original olive page. Gap: no hook yet, so an agent that skips the CLI is not caught |
| Post pinned comment asks for the next topic | memory + pending queue entry | docs | No — see class D |
| Tool state and evidence never live in a test runner's output folder (Playwright deletes `web/test-results/` on every run) | Architecture: defaults are `web/.verify-web/` and `web/.scene-preview/`; `web/tests/tool-state-paths.test.ts` in `make test` fails if a verify-web script, `drive.mjs` or `scene_workflow.py` default moves under Playwright's `outputDir` | architecture + test | Yes — fails on the pre-2026-11-09 `cleanup.sh` and `drive.mjs` defaults (`web/test-results/verify-web`). Gap: only checks the listed tools; a new tool must be added to the test |

## Mistake classes (audit 2026-11-08, pending.md + archive.md)

| Class | Evidence (entry dates) | Count | Current level | Recommended level | Why not higher |
| --- | --- | --- | --- | --- | --- |
| A. `design-bypass` — generated UI/artifact bypasses the design system or shared style | 10-04 travel UI style; 10-04 flattened emphasis; 10-27 standalone HTML; 11-04 office native controls; 11-06 PPT with zero 3D artwork | 5 | lint+hook inside `web/`; docs elsewhere | **lint** for the two docs-only gaps: (1) a PPTX check that fails when the cover or mechanism slides contain no picture element; (2) the standalone-HTML builder/checker already designed in `docs/design/ui-artifact-enforcement.md` | Architecture (one renderer for every artifact) would be stronger but spans PPT, travel HTML and ad-hoc pages; a check is the smallest step that fails on the 11-06 deck (12 slides, 0 pictures) |
| B. `scope-truncation` — stopped before covering the required scope | 10-09 backtest omitted allocator/hybrid; 10-09 hotel shortlist not re-searched | 2 | docs (skill checklists) | **test** for backtest: assert the comparison output lists every strategy family the pipeline produced (in `repos/ai-stock-analysis`); hotel search stays **docs** | Hotel coverage needs live browsing judgment; no artefact to check mechanically |
| C. `content-loss` — edits destroyed existing content beyond the request | 10-08 nutrient table removed; 10-06 Markdown deletion lost unique records | 2 | docs | **hook (warning)**: PostToolUse on Write/Edit under `data/` that reports removed Markdown tables or >30% removed lines, so the agent must justify it | Blocking is wrong: some removals are requested. A warning that names the loss is the highest level that doesn't block legitimate edits |
| D. `post-conventions` — social-post conventions missed | 11-05 no Malaysian slang; 11-05 pinned comment not next-topic | 2 (different rules) | memory + pending | **lint** for the pinned comment (mechanically checkable in `publish.txt`); slang stays **docs** | Slang quality is a judgment call; no check can score "moderate" |
| E. `claimed-not-executed` — claimed work underway without executing | 10-27 video re-edit | 1 | docs | — (not a class yet) | Single occurrence |

Single occurrences (not classes yet): grocery format (10-08), image style + archive path (10-28),
travel photography scope (09-29), restaurant radius (10-01), `disposable-output-state` (11-09:
verify-web kept its pid file and evidence in `web/test-results/`; a concurrent `make scene-check`
deleted the pid, so cleanup orphaned the server, and evidence cited in `office-world.md` /
`finance-workbench.md` is gone. Found by the agent, not an owner correction. `.scene-preview`
had avoided this by design on 11-08, so the lesson existed but was not carried over; escalated
straight to architecture + test above because the check is cheap).

## Next escalations (owner approval needed; one change each)

1. ~~Class A — PPTX artwork check.~~ Done: `make deck-lint` DECK-ART. Re-checked 2026-11-08:
   errors on the 11-06 v1 and v2 decks ("no artwork pictures in the deck"), silent on v3-3d.
   ~~Standalone HTML~~ done 2026-11-08: `make ui-build` / `make ui-check`. Remaining class A gap:
   delivery hook for standalone HTML (design §5 requires a runtime trial first).
2. Class D — `publish.txt` pinned-comment lint. Prove it fails on the double-11 draft before its fix.
3. Class C — `data/` destructive-edit warning hook. Prove it fires on the 10-08 nutrient-table edit.
