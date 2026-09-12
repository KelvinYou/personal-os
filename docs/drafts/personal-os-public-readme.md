# Personal-OS (public mirror draft)

> Draft README for a sanitized public mirror of this repo — framework only,
> excluding the private `data/` submodule (daily logs, finance, health data).
> Not yet published anywhere. Review and edit before creating the actual
> public repo/mirror.

## What this is

A production multi-agent system for personal self-management, built on
Claude Code's skill architecture and MCP servers. It replaces ad-hoc manual
weekly planning with structured, auditable agent workflows across health,
finance, career, and learning — 12 skills running on a weekly cadence.

This is not a chatbot wrapper. The core engineering problem it solves is:
**how do you let an LLM make recommendations against real personal data
(sleep, training load, portfolio holdings) without letting a plausible-
sounding but wrong model output override a real safety or financial
constraint?**

## The guardrail problem, concretely

Health and fitness data is noisy — a 7-day rolling sleep-debt trend is a
lagging, easily-gamed signal, but a single acute bad-sleep night is a real,
immediate risk signal. Treating both the same way produces one of two
failure modes:

- Too strict: the agent recommends a deload/rest week every time the rolling
  average dips, even when real-time HRV shows the person has recovered —
  "crying wolf" until the user ignores the system entirely.
- Too loose: the agent lets a genuinely bad night get smoothed over by a
  healthy rolling average and misses real acute risk.

Personal-OS resolves this with an explicit, hard-coded precedence rule
instead of leaving it to model judgment on every run:

- **Acute short-sleep on a single night is a non-negotiable hard line** —
  the recommendation engine cannot be talked out of flagging it, regardless
  of what the LLM's narrative reasoning concludes that week.
- **The rolling 7-day debt trend is soft** — real-time HRV is explicitly
  allowed to override an automated deload call here, because it's a lagging
  metric and the user's actual recovery state is the better signal.

The rule lives in code/config, not in a prompt — the LLM narrates and
contextualizes, but does not have authority to override the hard line. This
is the same shape of problem as guardrails in any agentic system operating
on real user data: decide up front which decisions are allowed to be
"vibes-based" (LLM judgment) and which must be deterministic and
un-overridable, then enforce that boundary in code.

## Architecture

- **Skill registry**: hot-reloadable Claude Code skills, each a self-contained
  workflow (daily logging, weekly review, wealth management, decision
  tracking, profile optimization, learning/job-market tracking, coaching).
- **MCP servers**: Figma, Google Calendar — external tool access via
  structured tool schemas, not free-form API calls.
- **Structured outputs everywhere**: every skill that produces a
  recommendation returns a typed, schema-validated result — not raw
  freeform text — so downstream code (and the next agent run) can reason
  about it without re-parsing prose.
- **Circuit breakers**: skills that touch financial or health guardrails
  fail closed, not open — a broken data source or malformed model response
  blocks the recommendation rather than producing a silently wrong one.

## Stack

Python, TypeScript, Claude Code, MCP, structured tool schemas.

## What's intentionally not in this repo

The private `data/` submodule (actual daily logs, portfolio holdings,
health metrics) is excluded. This mirror is the framework only — skill
definitions, orchestration logic, and config schema — with no personal data
and no real financial or health figures.

---

**TODO before publishing:**
- [ ] Confirm no thresholds/config in the mirrored code leak specific
      personal numbers (exact sleep-debt hour thresholds, portfolio size,
      etc.) — keep the README's framing generic, as above.
- [ ] Add a `demo/` or `examples/` directory with synthetic/fixture data so
      a visitor can see the skill flow without needing the private submodule.
- [ ] Decide on a repo name and add the actual GitHub link to
      `resume-profile.ts` / `data.ts` project entry once live.
