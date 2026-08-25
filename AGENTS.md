# Personal-OS — AI Agent Collaboration Protocol

> This file is the single owner of collaboration conventions for all harnesses (Claude Code / Codex / …).
> `CLAUDE.md` only imports this file — do not add content there.

## Project Overview
A personal management system that drives data-driven self-management through structured logs + AI agents. Core loop: daily logging → logic-engine alerts → weekly synthesis analysis → next-week scheduling.

## Directory Structure
> This block is validated line-by-line via `test -e` by `make doctor` (entries under `data/` are exempt when it isn't checked out).
> If you change the layout, update this too — this file is force-injected into every session, and a wrong path here makes an agent read the wrong file outright.
```
/config/                  — my threshold settings + regulatory constants (thresholds / wealth_rules.yaml)
/market/                  — externally observable market facts (interest_rates / fx.yaml, jobs/); public, no personal info
/data/                    — private submodule (personal-os-data); not checked out without permission
/data/daily/              — daily engineer logs (YYYY-MM-DD.md); 90-day hot window, older entries folded by make archive
/data/archive/            — cold-data archive (YYYY-Qn.md weekly summaries + body.csv full body-composition series)
/data/protocol/           — standing protocol; standard_week.md is the single human-readable schedule, not re-shuffled weekly; standard_week.yaml is only a Calendar-anchors projection
/data/finance/            — financial holdings (savings / portfolio / policy.yaml)
/data/reports/            — weekly report archive + weekly delta (only generated when there are exceptions)
/data/reports/evals/      — session eval records (produced by make eval; audits the agent itself, not me)
/data/user_profile.md     — global user profile (routine/diet/training preferences)
/docs/                    — long-form docs; three owners: VISION (direction) / ROADMAP (to-do) / DECISIONS (decided, not revisited)
/docs/voice-guide.md      — my writing voice (reverse-engineered from 34 published blog posts); read before writing any outward-facing text
/ARCHITECTURE.md          — system architecture + invariants; read before changing data flow/contracts
/SETUP.md                 — first-time bootstrap flow; the top comment block is an interactive script for the agent
/templates/               — blank template files
/scripts/                 — automation scripts (Python 3)
/tests/                   — unit tests + fixtures (never read real private data)
/web/                     — local wealth dashboard (Next.js, localhost only)
/.agents/skills/          — AI agent skills (weekly-review / wealth-manager / ...)
/repos/                   — external project submodules, managed centrally + read by skills
/repos/portfolio-website  — personal website (unified entry point for career-related content)
/repos/ai-stock-analysis  — stock analysis tool; also the sole owner of stock price data
/repos/notes    — public notes submodule; sole owner of the nutrition dataset
/scripts/nutrition.py     — nutrition query adapter (reads repos/notes; see docs/plan-public-knowledge-integration.md)
/scripts/lib/nutrition/   — shared implementation for the nutrition adapter (basis conversion, macro/cost derivation)
```

## Key Conventions
- Daily log filename format: `YYYY-MM-DD.md`
- YAML frontmatter must validate against `scripts/lib/schema.py`; the field list must stay in parity with the template (optional fields may be left blank)
- All thresholds are read from `config/thresholds.yaml` — no hardcoded magic numbers in scripts
- Scripts use Python 3, dependencies in `requirements.txt` (`make setup` installs into `.venv/`)
- All output must conform to the CommonMark standard

## Common Commands
- `make setup` — create `.venv` and install dependencies
- `make setup-private` — check out the private `data` submodule (requires repo permission)
- `make doctor` — environment self-check; distinguishes error / expected (e.g. data not checked out due to missing permission) / warning
- `make test` — Python tests + web typecheck
- `make today` — generate today's log template
- `make check` — run the logic engine against all logs
- `make weekly` — aggregate this week's data, generate the weekly-report prompt
- `make report` — one-shot full weekly report (aggregate + call AI)
- `make wealth` — Tracked Assets: cash/maturities/rates + stock valuation (NAV-priced products still excluded)
- `make eval` — convert the most recent Claude Code session into an eval record (`SESSION=recent-3` to select one)
- `make eval-rollup` — monthly agent-signal rollup; `/meta-coach` reads this, not individual evals

## AI Agent Collaboration Notes
- When generating a schedule, always reference the routine/diet preferences in `data/user_profile.md`
- The scoring framework uses four weighted dimensions (Output 40 / Health 30 / Mental 20 / Habits 10)
- Log style: engineer's-eye view, marked with `[Status: OK/Warning/Critical]`
- All content — logs, reports, and skills alike — is written in English
- Read `docs/voice-guide.md` before writing any **outward-facing text** (blog / LinkedIn / README prose / commit body). Internal repo reports are not governed by it — keep using the `[Status: ...]` convention.

## Give Three Next Steps When Wrapping Up
After answering a request, proactively offer 3 optional next steps — don't ask "anything else you need?":
- **The first one must be something I wouldn't have thought of but would find useful** — an opportunity visible from this context, not a restatement of what I just said.
- The 2nd and 3rd are natural follow-ups (what command to run, which file to change).
- One line each, with a concrete command or path. If you can't figure it out, don't guess.

Exceptions — skip this when: I'm issuing rapid consecutive instructions (meaning I already have a sequence in mind, and inserting suggestions would interrupt); or this turn is itself me answering your question.

## Audit the Agent Itself After a Session Ends
`make eval` converts a transcript into a record under `data/reports/evals/`: facts + mechanical
signals (write-before-read / unverified-mutation / tool-error-loop / user-correction …),
each signal annotated with "what evidence would falsify it."

- The `judgement` / `agents_md_change` / `notes` fields are **always null at generation time**.
  An auditor that scores itself is equivalent to giving the audited party write access —
  that's the same pitfall as in `/decision-log`. A human or `/meta-coach` fills these in afterward.
- Regenerating never overwrites already-filled review fields (unless `--force`).
- A single eval proves nothing; the distribution from `make eval-rollup` is the evidence. If the
  same signal fires in over half the sessions in a month → that's a bug in AGENTS.md, not in that session.
