# web feature map

One file per user-facing feature. Each answers four questions from the owner's point of view:
what exists (`Sub-features`), how a user reaches it (`How to get to it (user POV)`), the exact
drive command (`Driving it with drive.mjs`), and what misleads a verifier (`Gotchas`).

Every entry point is in the top nav (`Main navigation`): Office, Finance, Home, Agent signals,
Skill evals, Flows, Design. `/` renders the Office page.

| Feature | Route | Data source | Last driven |
| --- | --- | --- | --- |
| [Office](office.md) | `/`, `/office`, `/office?mode=demo`, `/office?scene=town`, `/office?dept=finance`, `/office?dept=content`, `/posts` | Codex + Claude Code transcripts and private content via `/api/office/*`; demo = simulated | 2026-11-09 |
| [Finance](finance.md) | `/finance`, `/finance#cash|#stocks|#liabilities|#activity` | `scripts/wealth_check.py` over private `data/finance/` | 2026-11-09 |
| [Flows](flows.md) | `/flows` | `web/public/flows.json` from `make flows` | 2026-11-08 |
| [Agent signals](agent-signals.md) | `/eval-rollup` | `scripts/session_eval.py --rollup-history` | 2026-11-08 |
| [Design system](design-system.md) | `/design-system` | static fixtures in `web/app/design-system/` | 2026-11-08 |
| [Home](home.md) | `/home-design`, `/home-design/viewer` | owner's local `apartment.html` (gitignored) | 2026-11-08 |
| [Skill evals](skill-evals.md) | `/skill-regressions` | `scripts/skill_regressions.py --json` | 2026-11-08 |

Office characters (`/office/characters`) are covered by the Kenney Mini characters journey in [Office](office.md).

Sweep order for a full pass: Design system → Flows → Agent signals → Skill evals → Finance →
Home → Office (cheapest compile first; WebGL pages last).
