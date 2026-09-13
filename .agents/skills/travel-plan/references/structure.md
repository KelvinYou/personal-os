# Document structure contract

Section order is fixed so that two plans can be diffed and so `make travel-lint` finds what it expects. Sections may be empty-dropped only where noted.

---

## Header block

```markdown
# <路线> <YYYY-MM-DD> → <YYYY-MM-DD>

> **版本** v1（查证日）｜<一句话说明这一版是什么>
> **复核期限**：**<日期> 前必须逐条复核一次**。本文档所有数据以「查证日 <日期>」为准。
> **图例**：`[地名](高德)` · `G` = Google Maps · ✅ 已查证 · ⚠️ 坑点/硬约束 · ❓ 待确认 · 🚨 高风险项
```

The **verification date** is not decoration. Prices, reservation rules and timetables all drift; a reader six weeks later needs to know how stale the page is. The **re-verify deadline** should sit ~2 weeks before departure, or before the first booking window closes — whichever is earlier.

## The "do this now" block

Immediately after the header, before §0. Two to four items, **ranked by consequence** — what is unrecoverable if missed, not what comes first chronologically.

Qualifies: a ticket that sells out with no substitute; a booking window that closes; a room that must be booked for a non-obvious date; a route that no longer exists.
Does not qualify: anything that can be fixed on the day.

If the verification gate turned up structural surprises, they go here too, with the ✅ evidence inline — the reader has to be able to see *why* their existing plan was wrong.

## §0 一页速览

- Day table: `Day | 日期 | 城市/主题 | 住宿 | 主要交通`
- Include a `—` row for a pre-trip night when the first room is booked before Day 1.
- Then explicit totals on their own lines: days, stops, **nights with the per-city enumeration**.
- Then the structural risks in one or two lines.

Totals must agree with the table and with §7. `count_consistency` fires when they do not — including across renamings (`6 家酒店` vs `5 处住宿` counts as the same unit).

⚠️ Write enumerations so the lint arithmetic reads them: `**12 晚**（长沙 2 + 张家界 1 + 镇远 2 + 开阳 2 + 成都 3）`. Avoid putting a second count immediately before the same parenthesis, and avoid `9/21 晚` style date-plus-unit strings on a totals line — both create false positives.

## §1 基本信息

Two-column table: 人数 / 预算 / 去程 / 回程 / 值机截止 / 护照有效期底线 / 停留天数 / 天气.

Flights carry both the local time and the airport, with map links. Check-in cut-off is ❓ until the ticket confirmation is in hand — say so rather than assuming 60 minutes.

## §2 出发前必做

Back-dated from deadlines, not listed by topic.

- §2.1 what to book now, and why each one cannot wait
- §2.2 entry and documents
- §2.3 payment and network
- §2.4 **the dated booking calendar** — a table of `窗口 | 要做的事`, computed from the advance-sale windows found in the gate

The booking calendar is the part people actually use. It must contain real dates, derived from real windows.

## §3 the anchor activities

One table for the two to four things the trip is *for*. Location confirmed, opening season, price, what the price includes, physical constraints, and the phone number to call for whatever is still ❓.

## §4 逐日行程

The body. Per-day format is in `SKILL.md §2`. Additional rules:

- Lead each day with `> **定位：**` — one sentence naming what the day is. A day whose 定位 cannot be written in one line is usually two days crammed into one.
- A transfer day is a 定位 in its own right. Do not apologise for it or stuff it with sights.
- Fallback blocks go under the day they belong to.
- When a day changed materially from the previous version, say so inline (`✅ v4 从 Day 6 移到这里`) — the reader may be holding the old version.

## §5 餐饮

`城市 | 推荐 | 地图 | 人均参考`. A ❓ on 人均 is fine; an invented number is not.

## §6 已知坑点与避雷

Cross-verified traps only. Each entry: what happens, then **避雷:** what to do instead. Scams get 🚨; annoyances get ⚠️. Anything without a second source stays ❓ or gets dropped.

## §7 预算明细

Per-person table with a 合计 row, plus a ticket breakdown that reconciles against the 门票 columns in §4.

State the verdict explicitly: inside budget, at the ceiling, or over — and if it moved from the previous version, say by how much and why. If it is at the ceiling, give the levers to pull.

## §8 行李清单

Grouped: 证件与支付 / 通讯 / 衣物 / 专项 / 其他. The 专项 group is per-activity (rafting, climbing, a photoshoot) — that is where the trip-specific value is.

## §9 应急信息

Local emergency numbers, the venue phone numbers already cited elsewhere, consular contacts **per region visited**, and a medical-cost line. Plus: which addresses to save in the phone in the local script.

## §10 复核清单

The single most reusable section. Every ❓ in the document appears here as a checkbox, grouped by how it gets resolved (a phone call, a booking site, a date-gated release). Group phone calls together — they get made in one sitting or not at all.

## §11 变更记录

One row per version. Say **what was wrong**, not just what changed — a changelog that reads "improved the itinerary" is useless to someone holding v1.

This section is excluded from every lint rule (it quotes superseded values deliberately).

## §12 数据来源

Links for everything marked ✅. Without this, ✅ means nothing and the next revision cannot tell verified from assumed.
