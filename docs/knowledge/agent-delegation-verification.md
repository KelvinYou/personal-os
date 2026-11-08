---
type: research
status: active
summary: What Lauren Tan (poteto) actually showed about scaling agent work through verification, feature maps and enforced corrections, with verified sources and how this repo adopts each idea.
updated: 2026-11-08
review_after: 2027-05-01
---

# Scaling agent work: verification before delegation

Source distillation of Lauren Tan's (@poteto) 2026 talks and the open-source `pstack` skills.
Claims are separated from interpretation; numbers are the speaker's own and unaudited.

## Verified claims

| Claim | Source | Note |
| --- | --- | --- |
| "here's how i shipped 2,500 PRs last month to production" | [X post](https://x.com/poteto/status/2102050467505430555) | Title says 2,500. "2,000" circulates as a second-hand paraphrase. A separate "Part 1" talk says "a thousand PRs" ([transcript](https://sozai.app/transcript/spacex-ai-engineer-lauren-tan-part-1/index.md)) |
| Maven session "How Cursor Turned AI Agents Into Better Engineers", 2026-08-12 | [Maven](https://maven.com/p/e23d9c/how-cursor-turned-ai-agents-into-better-engineers) | Co-hosted with Colin Matthews; presents pstack |
| Agents window performance work moved from manual traces to agents capturing traces and heap snapshots | Part 1 transcript ~04:17–05:08 | Timestamps in the 2,500-PR video were not independently verified |
| Electron main-process code is barred from the renderer; CI checks imports | Part 1 transcript ~41:37–41:55 | "Dune" is the architecture code name (~38:16) |
| Verification skill rules: real user path, action + resulting state, side effects, run the generated skill once | [`create-verification-skill`](https://github.com/cursor/plugins/tree/main/pstack/skills/create-verification-skill) | "A generated skill that was never executed is a draft, not a deliverable." |
| Feature map: per feature, Sub-features / How to get to it / Driving it / Gotchas | same skill; [example repo](https://github.com/poteto/verification-skill-example) | Example product (Atlas) is fictional; control CLI deliberately omitted |
| `/correct`: architecture → types → lint/CI → test → docs; prove each check fails on a real past mistake; keep a rule ↔ enforcer table | [`correct`](https://github.com/cursor/plugins/tree/main/pstack/skills/correct) | |

## Interpretation

The bottleneck in delegating to agents is the human review queue. Each idea shrinks it:

1. **Verification** lets an agent prove its own work, so more agents do not mean more manual QA.
2. **A feature map** turns a vague report ("that panel is stuck") into a reproducible journey.
3. **Enforced corrections** make one correction improve every later session; a docs-only rule
   leaves the same review cost in place.
4. **The codebase is the example agents copy**: one supported way per task, old ways deleted.

PR count is a throughput number. It says nothing about rework rate, incidents, or cost per useful
change; the public material has no ROI evidence.

## How this repo adopts it

| Idea | Here |
| --- | --- |
| Verification skill + feature map | [`verify-web`](../../.agents/skills/verify-web/SKILL.md) and its [feature map](../../.agents/skills/verify-web/features/README.md) |
| Correction ladder + rule table | AGENTS.md § "Learn from Corrected Outputs"; [`enforcement.md`](../../reports/corrections/enforcement.md) |
| Prove checks on real past mistakes | Existing precedent: travel lint rules map to `tests/fixtures/travel_known_defects.yaml` |
| One supported way | Existing: design primitives ratchet (`scripts/design_rules_check.py`) |

## Open questions

- Is the repeat-correction rate enough evidence? It is now measured
  (`python3 scripts/session_eval.py --corrections`, `/eval-rollup` → 纠错复发; baseline
  2026-10 31%, 2026-11 75%), but interventions per task are still unmeasured.
- Should `verify-web` evidence become a required line in `docs/dev-sop.md` final evidence?
