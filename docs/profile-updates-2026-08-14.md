# Profile Updates — LinkedIn + JobStreet (2026-08-14)

> Companion doc to the resume update in `repos/portfolio-website/src/constants/data.ts`
> (DTCPay experience + Personal-OS project entries). Copy manually, verify numbers
> before publishing — nothing here should be pasted blind.

## Status

- [x] Resume (portfolio site + PDF export) — updated, build verified
  - Added PTIB back into Selected Projects (was missing — the report's own P0 item)
  - Summary now cites 9,000+ users
  - Removed duplicate `Solidity` from core Languages, condensed old Techtics bullets, trimmed AMM project description
- [x] **2026-08-17 second pass** — repositioning off frontend-only, driven by the
      RM 11k band analysis in [ROADMAP.md §4](ROADMAP.md#4-技能缺口2026-08-17-招聘数据复盘):
  - Title is now `AI-native Full-stack Engineer · Fintech Payments & Agent Systems`
    in all three locales. **`(Frontend-focused)` was dropped on purpose** — every
    RM 10-15k posting in `market/jobs/` is titled full-stack, and the qualifier
    was arguing against the thing being applied for.
  - dtcpay bullet 1 is now the Kotlin backend work (FX quote lock,
    largest-remainder allocation, CAS-on-status duplicate guard), with the two
    Kotlin blog posts linked from the experience card
  - Skills gained a `Cloud & Delivery` group; Kotlin and React Native were only
    in experience data and invisible to ATS
  - Stock Analysis card now carries measured backtest numbers instead of
    architecture counts
- [ ] LinkedIn headline
- [ ] LinkedIn About
- [ ] LinkedIn Experience — DTCPay bullets
- [ ] LinkedIn Skills reorder
- [ ] JobStreet headline / summary
- [ ] JobStreet Experience — DTCPay bullets

## 1. Headline

Use the same string on both platforms:

```
AI-native Full-stack Engineer | React, TypeScript, Kotlin, Python, LLMs, MCP | Fintech Payments
```

JobStreet has a shorter headline field on some templates — if it truncates, use:

```
AI-native Full-stack Engineer | React, TypeScript, Kotlin, Python, LLMs
```

> Kotlin is in the headline deliberately: it is the only backend language with
> production evidence behind it, and backend ownership shows up in 58% of the
> MY job descriptions for the target band.

## 2. About / Summary

```
I build AI-native products that turn complex workflows into usable software—from fintech payment platforms to LLM-powered developer tools.

I'm a Frontend Engineer at dtcpay, where I build web and mobile experiences for a live payments platform serving 9,000+ active users, including bulk payment, swap, eKYC, and transaction record flows. I led a Flutter-to-React Native migration that unified our mobile and web codebases onto a single stack, cutting duplicate maintenance so the team could focus on quality instead of platform parity.

Outside my current role, I build across Python/Node.js APIs, PostgreSQL-backed applications, LLM integrations, MCP tools, and multi-agent workflows.

Recent work includes:
- Personal-OS: a multi-agent operating system with 12 Claude Code skills (daily logging, wealth management, weekly review, decision tracking, profile optimization), running weekly to replace manual self-planning with structured, data-driven review.
- Claude API + MCP tooling for Playwright spec generation, auto-debug loops, and PRD/Figma conflict detection before development.
- Simpletruss: 40% faster development velocity and 60 KB smaller bundles via a TypeScript component library.
- Beyondsoft/Tencent: sub-3s, 60fps analytics views for 500K-row datasets.
- PTIB: a multi-tenant SaaS for a 200-student tuition center, saving 5 hours/week and generating $500 MRR from 3 pilot centers.

I'm interested in AI-native full-stack and product engineering roles where frontend quality, reliable API integration, and applied LLM systems come together.
```

JobStreet's summary field is usually plain text with a lower character cap — trim the bullet list to the top 2 (Personal-OS + PTIB) if it doesn't fit.

## 3. DTCPay Experience — replace existing bullets

**Old** (currently live on LinkedIn/JobStreet — drop these):
- "Shipping merchant-facing web and end-user mobile app frontends on a live payment platform."
- "React JS→TS migration: ESLint setup, folder structure rewrite, type-safe API boundaries."
- "Reusable component patterns and shared UI primitives for cross-product consistency."

**New**:
- Built bulk payment, swap, eKYC onboarding, and transaction record flows for a live fintech platform serving 9,000+ active users.
- Led a full Flutter-to-React Native migration, unifying mobile and web onto a single React/TypeScript codebase to cut duplicate maintenance and free engineering time for quality-focused work.
- Reusable component patterns and shared UI primitives for cross-product consistency.

Note: the JS→TS migration bullet is intentionally dropped — it was a minor, largely AI-assisted task and the Flutter→RN migration is a stronger full-stack/ownership signal.

## 4. Skills reorder (LinkedIn "Skills" section, top of list)

```
React, TypeScript, Python, Next.js, Node.js, React Native, LLM Integration, Agentic AI, MCP, API Integration, PostgreSQL, CI/CD, Docker, Playwright
```

Move `Solidity`, `MetaMask`, `Blockchain`, `Java`, `Go` further down — they're real but not the target-role signal.

## 5. Things to verify before publishing (do not skip)

- [ ] "Led" is accurate for the Flutter→React Native migration — confirm this matches your actual role/ownership level, not just participation.
- [ ] 9,000+ active users figure — confirm you're allowed to share this externally (check with your manager/DTCPay comms policy if unsure about disclosing platform user counts).
- [ ] Simpletruss (40%/60KB/35%) and Beyondsoft (sub-3s/60fps/500K rows) numbers are unchanged from your existing profile — re-verify they still hold before reposting.
- [ ] PTIB numbers ($500 MRR / 3 pilot centers / 5 hrs/week) — confirm still current.

## Source

Generated from a profile-optimizer + job-market review session on 2026-08-14
(`market/jobs/trends.json`, 60 Indeed JDs MY/SG). See `.agents/skills/profile-optimizer`
for the underlying skill if you want to rerun this analysis in 4-6 weeks.
