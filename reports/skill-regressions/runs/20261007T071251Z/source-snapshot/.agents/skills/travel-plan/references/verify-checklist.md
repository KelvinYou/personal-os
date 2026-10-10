# The verification gate, as a worklist

Run before drafting any day. Copy this into the working notes, fill it, then write.

Each row: what to look up, how to phrase the search, and what a wrong answer costs.

---

## A. Calendar — once per trip, covers every date

| # | Lookup | Search phrasing | Cost of missing it |
|---|---|---|---|
| A1 | National holiday notice for the travel year | `<国家> <年份> 放假安排 国务院 通知` / `<country> public holidays <year> official` | Entire days land in a holiday: tickets gone, rooms 2-10×, stations jammed |
| A2 | Compensatory workdays around each holiday | same notice | A "weekday" is actually a working Saturday, or vice versa |
| A3 | Conventions / expos / marathons / festivals per city, per date | `<城市> <月份> <年份> 展会 马拉松 封路` | Hotel prices spike near the venue; roads closed |
| A4 | Which weekday each day falls on | compute | Monday closures, Saturday-only events (fireworks, markets) |

> Do A1 even when the trip looks far from any holiday. The Changsha plan sat three days inside Mid-Autumn for three versions because nobody asked.

## B. Venues — once per ticketed place

| # | Lookup | Search phrasing | Cost |
|---|---|---|---|
| B1 | Weekly closure day | `<venue> 开放时间 闭馆` | A whole slot is dead on arrival |
| B2 | Last admission time (≠ closing time) | same | Arriving 30 min before closing means not getting in |
| B3 | Reservation required? foreign-passport channel? | `<venue> 预约 护照 外籍` | Turned away at the gate with a valid ticket |
| B4 | Current ticket price for the travel year | `<venue> 门票 价格 <年份>` | Budget off; and a stale price usually means a stale everything-else |

## C. Conveyances — once per cable car / lift / ferry / sightseeing train

| # | Lookup | Search phrasing | Cost |
|---|---|---|---|
| C1 | **Is it running right now?** | `<名称> 索道 停运 检修 升级改造 恢复 <年份>` | The day's whole route is fiction |
| C2 | If partly closed, what is the current routing | `<景区> <年份> 游览路线 A线 B线 调整` | Wrong entrance, wrong ticket, wasted hours |
| C3 | Bad-weather fallback routing | `<景区> 恶劣天气 停运 线路变更` | No plan B on the one day it matters |
| C4 | What the ticket includes after the change | `<景区> 门票 包含 <年份>` | Pay twice, or get stuck mid-mountain |

## D. Intercity legs — once per leg

| # | Lookup | Search phrasing | Cost |
|---|---|---|---|
| D1 | Is there really no direct route? Check stations within ~50 km | `<A> 到 <B> 高铁 最近的高铁站` | A bookable 1 h train written as an unverifiable 4 h bus |
| D2 | Advance-sale window, and whether it includes the travel date | `<平台> 预售期 几天` | Booking checkpoints land before tickets exist |
| D3 | Same-platform transfer, or exit-and-re-enter? | `<站> 换乘 同台` | A 40-minute connection that is actually impossible |
| D4 | Door-to-door: station access at both ends | map query | Transfer day understated by 2 h |
| D5 | First / last service for any edge-of-day leg | `<线路> 首末班 运营时间` | Stranded at an airport at 01:00 |

## E. Money and arithmetic — no lookup, but no skipping

| # | Check | Cost |
|---|---|---|
| E1 | Combo ticket: enumerate what is inside and what is still extra | Double-paying, or a gap mid-route |
| E2 | Nights, not days. First night's date for an after-midnight arrival | 3am in the lobby |
| E3 | Door-to-door totals ≥ sum of legs | The day does not fit |
| E4 | Budget reconciles against the 门票 column of the day tables | Budget quietly fictional |
| E5 | Totals agree across summary table / totals line / budget | Lint will catch some; not all |

## F. Admin — once per trip

| # | Lookup |
|---|---|
| F1 | Visa / visa-free terms, stay limit, passport validity floor (arrival date + N months) |
| F2 | Arrival card / entry declaration: required? fillable in advance? |
| F3 | Payment: foreign-card acceptance, fee thresholds, cash needs in small towns |
| F4 | Network: what is blocked, whether a local SIM or roaming is required, VPN before arrival |
| F5 | Consular contacts for **each** region of the trip (jurisdictions differ by province) |
| F6 | Travel medical insurance — especially with rafting / height / adventure activities |

---

## Recording the results

Every answer lands in the draft in one of three shapes:

- **✅ fact + source in §12** — verified.
- **❓ fact + what would settle it** — looked and it was unclear, conflicting, or unpublished. Name the phone number / counter / page to check.
- **Nothing** — you did not look. This is the only unacceptable outcome.

A conflicting result is a finding, not a failure: write both numbers and say which one to plan against.
