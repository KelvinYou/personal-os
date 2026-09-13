---
name: travel-plan
description: Produces and revises trip plans under data/travel/ at the repo's v4 standard on the first pass — a verification gate before any day is written, per-day timeline tables with dual map links, marker discipline (✅/⚠️/❓/🚨), and a share-ready HTML build. Use this skill whenever the user asks to plan, draft, review, revise, or "make more detailed" a trip, itinerary, travel plan, or 行程/旅行计划, or mentions a file under data/travel/. Also use it when turning an existing plan into a share version for a travel companion.
---

# Trip Plans

The repo already has two labelled records of what goes wrong: `tests/fixtures/travel_known_defects.yaml` (47 defects from the Shanghai plan's v2→v4 changelog, plus the Changsha v1→v4 round). Read the ratio before you start:

| class | count | who catches it |
|---|---|---|
| **verify** | 22+ | **nobody, unless you look it up before writing** |
| lint | 15+ | `make travel-lint`, mechanically |
| adjudicate / judgment / process | 10 | a human |

**Verify-class defects are the reason plans take four versions.** They are not stylistic — they are facts that were wrong, and no amount of re-reading the draft surfaces them. A plan that skips §1 and goes straight to writing days will be a v1 that needs a v4.

So the order is fixed: **verify, then write.** Not write, then review.

## Workflow

1. **Gate** — run the §1 verification sweep. Do not write a single day until it is done.
2. **Compose** — `templates/plan.md` + the structure contract in `references/structure.md`.
3. **Self-review** — the §3 pass.
4. **Lint** — `make travel-lint` must be clean before you hand it over.
5. **Share** (on request) — `references/share-html.md`.

Write to `data/travel/<cities>-YYYY-MM.md`. Chinese is fine here and usually correct — `data/travel/` is the documented language exception in AGENTS.md, because map queries, mini-program names and restaurant names have to stay in the local script to be usable on the ground.

---

## 1. The verification gate

Nine categories. Every one of them has produced a real defect in the corpus. Run them **before** drafting, and carry the answers into the draft as ✅ lines with sources.

If a lookup comes back empty, that is a result — mark it ❓ and say what would settle it (a phone number, an official page, "check at the counter"). **A ❓ you declared is fine. A fact you assumed is not.**

### 1.1 Calendar collisions — for every date in range, in every city

Public holidays, festivals, conventions, marathons, expos. Check the **national holiday notice** for the travel year, not a generic "when is X" answer — holidays move, and compensatory workdays move with them.

> Shanghai v3 moved the whole trip a week for 进博会. Changsha v1–v3 missed 中秋 entirely: three of twelve days sat inside a public holiday nobody had noticed, which changes ticket availability, room rates and station crowds.

Cross-check the holiday range against the day table and say, per affected day, what it means.

### 1.2 Venue closure days

Monday closures for museums, seasonal closures, maintenance days. The corpus calls closure-day collisions "the single most mechanical defect" — and it is still verify-class, because it needs a per-venue lookup.

### 1.3 Operating status of every mechanical conveyance

Cable cars, gondolas, lifts, funiculars, escalators, ferries, sightseeing trains. **These go out for months at a time and every blog post predates the outage.**

> Changsha v1–v3 routed a whole day through a cable car whose upper section had been closed for renovation for ten months. The route, the ticket price and the day's shape all changed once that was checked.

Ask specifically: is it running *right now*, and what is the fallback route when it is not?

### 1.4 "There is no direct route" claims

Before writing a long bus transfer or a multi-leg workaround, check whether a nearby station solves it. Do not inherit the claim from a guide.

> Changsha v1–v3 wrote a 3–4 h intercity bus with unverifiable departures, calling it "the only segment with no timetable". A high-speed station 30 km away turned it into a bookable 1 h train — on a road the itinerary already traversed two days earlier.

### 1.5 Booking windows

Advance-sale periods decide the whole booking calendar. Find the window (in days, and whether it includes the travel date), then compute the actual on-sale dates.

> 12306 is 15 days including the travel date — which made a single "book everything on 10/17" checkpoint infeasible and forced a four-date calendar. Panda-base tickets have two published windows (7 days, and 14 days including today) that disagree; the plan says both and names the hard one.

### 1.6 First and last service times at the edges of the day

Any leg that lands before ~07:00 or after ~21:00. Airport rail, metro, maglev, shuttle buses all stop earlier than people assume.

> A 01:10 landing means the maglev and the airport bus are both long finished — taxi is the only option, and that changes the arrival timeline and cost.

### 1.7 Ticket composition — what a combo ticket actually contains

Never write "combo ticket ¥X" without listing what is inside it and what is still extra.

> Changsha v1–v3 treated a ¥227 gate ticket and a ¥238 cable-car pass as two tiers of the same thing. They are different tickets: the gate ticket already includes the shuttle bus; the cable cars are never included. Getting this wrong either overspends or strands you.

### 1.8 Lodging-night arithmetic

Count nights, not days. Then check the two traps:

- **After-midnight arrival** — a 01:10 landing means the first room is booked for **the previous calendar date**. Booking it on the arrival date puts you in the lobby at 3am.
- **After-midnight departure** — the mirror image: the ticket says the next day, the traveller must be at the airport the evening before.

State the first and last night explicitly. `make travel-lint` checks both traps, but only if the dates are on the page.

### 1.9 Door-to-door time, not in-vehicle time

A transfer day's duration is station access + wait + ride + transfer + ride + onward access. Summing only the rides understates it by hours.

> "The whole trip is about 3.7 h including the transfer" was 2h58m + 40m with nothing else counted. Door-to-door was ~5.5 h. `make travel-lint` now catches a stated total that is less than the legs it sits next to.

---

## 2. What the document must contain

Full contract in `references/structure.md`. The short version:

- **Header** — version, re-verification deadline, **the verification date all data is stated as of**, marker legend.
- **A "do this now" block** — the two or three things that cannot be recovered if missed. Ranked by consequence, not by document order.
- **§0 one-page overview** — day table, plus explicit totals (days / stops / nights) that agree with each other.
- **§1 basics** · **§2 pre-departure, back-dated from deadlines** · **§3 the anchor activities**
- **§4 day-by-day** — this is the body of the document, see below.
- **§5 food** · **§6 pitfalls** · **§7 budget** · **§8 packing** · **§9 emergency** · **§10 re-verify checklist** · **§11 changelog** · **§12 sources**

### The per-day format

Every day gets: a `> **定位：**` one-line judgement of what the day *is*, then a five-column table, then any fallback blocks.

```markdown
### Day 4（周五 9/25）🚨 中秋当天 · 武陵源核心景区全天

> **定位：全天一个景区，不走回头路。**
> 🚨 中秋假期第一天 —— 07:00 就到门票站，晚一小时会多排半小时。

| 时间 | 安排 | 地图 | 门票 | 备注 |
|---|---|---|---|---|
| **07:00** | 到[吴家峪口门票站](高德链接) · [G](google链接) | 同上 | **¥227** ✅ | 含保险/含环保车/4天有效 |
```

Rules that make the format worth the effort:

- **Times are derived, not invented.** Build each day by chaining verified durations from a fixed anchor. If a duration is unknown, the time inherits ❓.
- **Dual map links on first mention** of every place — 高德 + Google. One of the two will be unreachable depending on the traveller's network; the pair is the redundancy.
- **Every day that can fail gets a fallback block** — weather, sold out, closed, too tired. Put it under that day, not in a distant appendix.
- **Fixed costs are in the 门票 column**, so the budget can be reconciled against the days.

### Marker discipline

| | meaning |
|---|---|
| ✅ | verified against an official or strong source — **and the source is in §12** |
| ⚠️ | a constraint or trap that changes behaviour |
| ❓ | unverified, conflicting sources, or "ask on the day" — **name what would settle it** |
| 🚨 | high consequence: missing it costs the trip, not a detour |

Never leave a specific departure time bare. `unsourced_specific` fires on any precise time near a departure word without ✅ / ❓ / a link — that rule exists because bare times read as verified when they were estimated.

---

## 3. Self-review before handing over

Run these against the draft. They are the failure modes that survived a generation pass in the corpus.

1. **Every date in range** — checked against the holiday calendar? (§1.1)
2. **Every conveyance** — operating status checked? (§1.3)
3. **Every combo ticket** — contents enumerated? (§1.7)
4. **Nights** — do the day table, the totals line, and the budget all use the same number? Is the first night's date right? (§1.8)
5. **Every transfer day** — door-to-door, or just the rides? (§1.9)
6. **Every ❓** — does it say what would settle it, and is it in the §10 re-verify checklist?
7. **Every ✅** — is its source in §12?
8. **Overclaims** — 完全 / 绝对 / 一定 / 从不 on an unsourced line is almost always wrong. The corpus has one: "sells no tickets on site at all" — a foreign-visitor counter existed.
9. **The summary table vs the days** — lodging column, durations, and totals must agree. Lint catches some of this; read it anyway.

Then: `make travel-lint`. **A plan that does not lint clean is not finished.**

## 4. Revising an existing plan

Same gate. A revision request ("make it more detailed", "review this") is **not** permission to skip §1 — detail added on top of unverified facts is worse than a thin correct plan, because it reads as authoritative.

- Bump the version, add a changelog row saying **what was wrong**, not just what changed.
- Never silently delete a wrong claim — the changelog is how the user knows not to trust their memory of v1.
- Keep the changelog section excluded from lint (it quotes superseded values on purpose; `_excluded_mask` already handles this).
- When a revision finds defects worth remembering, add them to `tests/fixtures/travel_known_defects.yaml` with a `class` — that file is the eval set for this skill.

## 5. Files

| path | what |
|---|---|
| `references/structure.md` | the full section-by-section contract |
| `references/verify-checklist.md` | §1 as a copyable checklist with search phrasings |
| `references/share-html.md` | how to build the share version |
| `templates/plan.md` | the skeleton to start from |
| `assets/share.css` | the stylesheet the share HTML reuses verbatim |
