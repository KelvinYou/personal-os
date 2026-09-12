---
name: design-doc
description: Turns a feature request, Jira ticket, or rough idea into the right planning document — an implementation plan, a lite or full technical design doc for architect review, or an ADR — sizing the document to the change instead of always producing the same template. Use this skill whenever the user mentions a design doc, tech spec, technical design, RFC, architect review, implementation plan, ADR, or asks "how should I build this", "help me plan this feature", "write this up for review", or hands over a requirement/ticket and wants it structured before coding. Also use it when reviewing or improving an existing design doc for missing sections and unanswered architect questions.
---

# Design & Planning Documents

A design doc exists to get a decision, not to look complete. The reader — usually an architect, tech lead, or your future self — should be able to answer four questions fast:

**What are we changing? Why? What's the proposed design? What are the risks and trade-offs?**

Everything else in a template is optional scaffolding. Your job is to pick the smallest document that answers those four questions for *this* change, then add back exactly the sections this change actually needs.

## Workflow

1. **Gather** — read the ticket/requirement and, if a codebase is present, look at the code the change touches. A design doc written without reading the current code is guesswork, and architects can tell.
2. **Triage** — pick a tier (below). Say which tier you picked and why, in one line, before writing.
3. **Compose** — start from the tier's template in `references/templates/`, then run the signal scan to add or drop sections.
4. **Self-review** — run the architect challenge pass (below). This is where the document actually gets good.
5. **Write** to `docs/design/<slug>.md` (create the directory if needed). Tell the user the path. Match the language of the user's input — Chinese requirement in, Chinese doc out.

## Triage: pick a tier

Ask what the reader needs, not how big the ticket feels.

| Tier | Use when | Template | Length |
|---|---|---|---|
| **Plan** | One component, no new API contract, no schema change, no cross-team dependency. The "how" is obvious; only the sequencing needs writing down. | `templates/implementation-plan.md` | ~1 page |
| **Design-Lite** | Multiple components or a new/changed API contract, but the approach is fairly settled and only 1–2 real trade-offs exist. This is the default for most feature enhancements. | `templates/design-lite.md` | 2–4 pages |
| **Design-Full** | Any of: cross-service, data migration, money/compliance/regulatory, security-sensitive, a genuinely contested design choice, or an external consumer whose contract breaks. | `templates/design-full.md` | 5–15 pages |
| **ADR** | The output is one decision, not a plan. "Should we do X or Y?" An ADR records the choice and stays true after the code changes. | `templates/adr.md` | 1 page |

When you're between two tiers, pick the smaller one and add the specific sections the bigger one would have contributed. A tight 3-page doc that gets read beats a 12-page doc that gets skimmed.

Design-Lite and Design-Full both get a **frontend and/or backend addendum** when the change is deep on one side — see `templates/addendum-frontend.md` and `templates/addendum-backend.md`. Attach an addendum only when it would carry real content; an addendum full of "N/A" is worse than no addendum.

## Signal scan: add sections the change earns

Templates are a starting inventory, not a checklist to fill. Scan the change for these signals and let them drive which sections exist. If a signal isn't present, **delete the section** rather than writing "N/A" — empty sections train readers to skim.

| Signal in the change | Section the doc must have |
|---|---|
| New or changed API contract | API Changes, with concrete request/response JSON and a backward-compatibility verdict |
| Existing external consumers of that API | Backward Compatibility + migration/deprecation path |
| Schema change, new table/column/index | Data Changes + migration required (yes/no) + backfill plan |
| Money, limits, balances, entitlements | Business Logic written as explicit rules (pseudocode or a decision table), not prose |
| Auth, PII, KYC, regulatory rules | Security & Compliance, naming the specific control and where it's enforced |
| Two or more clients (Web + Mobile) | Where the rule lives, and how the clients stay consistent |
| A real alternative you rejected | Alternatives Considered with a recommendation and reasoning |
| Behaviour depends on state (country, tier, verification) | A matrix or decision table, not bullet prose |
| Touches a flow that already exists in production | Impact & Risks + explicit regression scope |
| Anything can fail, time out, or partially succeed | Error Handling table: scenario → expected behaviour |
| Rollout can't be instant or reversed cheaply | Rollout: feature flag, migration, rollback strategy |

Conversely, drop these when they'd be filler: Alternatives (when there was genuinely one sane approach — but say so in one line rather than silently omitting), Testing Strategy (when it's the team's ordinary unit + e2e coverage), Rollout (for a change that ships behind an existing flag), Current Architecture (when the reader already lives in this system daily — a two-line recap beats a diagram they drew themselves).

Read `references/section-catalog.md` for what "enough detail" looks like in each section, plus the specific failure modes that make architects send a doc back.

## The architect challenge pass

Before writing the file, re-read your draft as a skeptical staff engineer who has 10 minutes and did not write it. Ask:

1. Can I tell what's changing within 30 seconds? (If not, the Scope table is missing or buried.)
2. Does every "we will add X" say **why X and not the obvious simpler thing**?
3. Where is the business rule enforced, and could a client bypass it?
4. What happens on the unhappy path — timeout, partial write, retry, concurrent request?
5. What existing behaviour could this break, and who consumes it today?
6. Which numbers are asserted without evidence? (limits, volumes, latency)
7. What am I assuming that nobody confirmed?

Every question you can't answer from the draft becomes either a new section, a sharper sentence, or an entry in **Open Questions**. Open Questions is not an admission of weakness — it's the highest-value section in an architect review, because it's where you convert your unknowns into their decisions. Every design doc ships with it, phrased as decisions you need from the reviewer:

> - Should the withdrawal limit be configurable per country, or is a global default acceptable for v1?
> - Do existing API consumers need backward compatibility, or can we version the endpoint?

Never fabricate specifics to fill a section. If you don't know the current schema, the actual endpoint shape, or the real error codes, either read the code to find out or mark it explicitly as an assumption in Open Questions. A confident wrong detail costs more review time than an honest gap.

## Diagrams

Architecture sections need a diagram, and the diagram needs to mark what's **NEW** vs **MODIFIED** — that's the single highest-signal thing in the doc. Plain ASCII is fine and renders everywhere:

```text
                    ┌── POST /withdrawals/validate  [NEW]
                    │
Frontend ───────────┤
                    │
                    ↓
             Withdrawal Service  [MODIFIED]
                    │
          ┌─────────┼─────────┐
          ↓         ↓         ↓
     Rule Engine  Payment   Database
        [NEW]     Service
```

Follow the diagram with one sentence naming the design intent ("the proposed design introduces a centralized validation layer so withdrawal rules aren't duplicated across Web and Mobile"). The sentence is what the architect quotes back; the boxes just support it.

Use Mermaid instead when the target is a wiki that renders it, or when the flow is sequential enough that a `sequenceDiagram` reads better than boxes.

## Reviewing an existing doc

When the user brings a doc rather than a requirement, don't rewrite it immediately. First report what's missing: run the signal scan against the change it describes, run the challenge pass, and list gaps as concrete questions. Then offer to revise. Identifying the three unanswered questions is worth more than a prettier version of the same document.

## Reference files

- `references/section-catalog.md` — per-section guidance: what belongs, what "enough detail" means, common failure modes
- `references/writing-guide.md` — phrasing patterns for architect review, diagram conventions, English wording for non-native writers
- `references/templates/` — `implementation-plan.md`, `design-lite.md`, `design-full.md`, `adr.md`, `addendum-frontend.md`, `addendum-backend.md`
