# Hotel search and comparison

Follow this order: **recommend areas → propose preferences → traveller confirms →
search Trip.com → verify room offers → rank → traveller selects**. Confirmation
prevents a polished shortlist from optimizing for the wrong needs. Searching is
read-only; hotel selection is not authorization to reserve, pay or cancel.

## 1. Establish context and recommend areas

Read the existing plan, confirmed preferences and relevant private profile before
asking for missing information. Check dates, nights (including midnight arrival),
travellers per stay, room count, beds, luggage, arrival/departure anchors and travel
style. For a new trip, ask only for missing inputs that materially affect location
or room eligibility; do not assume every segment has the same party size.

Recommend 2–3 areas per city, or fewer if only one is suitable, and name a first
choice. Explain sightseeing/food access, real transport connections, onward travel,
noise and terrain trade-offs. Use age as supporting context, not as a proxy for
walking tolerance, nightlife preferences or comfort needs. Actual transport habits,
interests and willingness to walk matter more.

Research current maps and reliable local/official sources for location claims.
Explain why an area suits this itinerary rather than merely saying most visitors
stay there. Verify walks to usable station exits or attraction entrances; a hotel
name containing a district and straight-line distance do not establish access.
Area research may precede preference confirmation; specific hotel-offer searching
and ranking wait until confirmation.

## 2. Propose a preference draft and obtain confirmation

Give a compact, editable recommendation with reasons, rather than a blank survey.
Use trip-wide preferences with explicit city/stay overrides. A transit night may
justify different comfort priorities from a multi-night stay; propose the override
and obtain confirmation instead of silently changing the requirements.

| Preference | What to specify |
|---|---|
| Stay context | Check-in/out dates, adults/children and ages where required, rooms, occupancy per room and bed arrangement |
| Area | Preferred area and accepted alternatives, with itinerary-specific reasons |
| Budget | Currency, per-room/night target and full-stay tax-inclusive ceiling for all rooms |
| Window | External window/daylight requirement; whether an internal or obstructed window is acceptable |
| Space | Minimum or preferred room area, considering occupants, beds and luggage |
| Smoking | Explicit non-smoking booked room; whether a wholly non-smoking property is required or preferred |
| Access | Actual walking-time limit to a usable metro exit or relevant transport/attraction entrance; stairs, slopes and luggage constraints |
| Ranking priority | Lowest eligible price, value for money, or comfort/higher star category |
| Other needs | Quietness, breakfast, laundry, heating/hot water, lift, luggage storage and arrival/check-in needs |
| Terms and eligibility | Required cancellation flexibility, payment terms and acceptance of the travellers' documents/occupancy |

Classify each criterion as **required**, **preferred**, or **flexible**. Agree which
flexible criteria may be relaxed first. Explain suggested defaults; do not turn
examples into universal thresholds. For example, 200 sq ft is approximately
18.6 m², not a guarantee of comfort, and “has a window” does not guarantee daylight.

Present the proposed areas, values, priorities and city overrides together and ask
the traveller to confirm or edit them. Stop before hotel-offer search while the
answer is pending. Silence is not confirmation. Explicit preferences supplied in
the current request or previously confirmed for this trip already count; ask only
about unresolved material choices. Evaluating a hotel the traveller explicitly
supplies is authorized, but do not infer preferences or expand to a new search.

## 3. Search Trip.com and verify specific offers

Search Trip.com with the confirmed dates, guests, rooms, areas and available
filters. Web search can discover candidates; it cannot establish current room
availability or checkout totals. If search lacks coverage or cannot expose room
details, use available browser controls to set filters, browse results and compare
each candidate's room offers. Do not claim a filter was applied unless observed.
If neither route works, report the access gap and request links or relevant offer
details; do not manufacture a ranking from search snippets.

Compare **hotel + specific room type + rate plan**, not hotel names alone. Check:

- All rooms available for the whole stay at the specified occupancy and bed setup.
- Room-level window type, area and smoking policy; property-wide amenities do not
  prove the booked room has them. Unknown required criteria remain pending, not
  passed. For area ranges, the lower bound must meet a confirmed hard minimum.
- Full-stay total for all rooms, taxes/mandatory fees, currency, breakfast,
  cancellation deadline (including timezone), payment and promotion conditions.
  Label totals not observed at checkout as provisional; never substitute a “from”
  price, one-room price or inaccessible coupon for the comparable total.
- Actual address and walking route, usable station exit, building entrance,
  lifts/slopes, luggage storage and late/early arrival arrangements as relevant.
- Recent recurring review issues, especially noise, cleanliness, odour and worn
  facilities. Distinguish dated guest reports from verified room features; do not
  rely on a high aggregate score with very few reviews or treat stars as room quality.
- Document/guest eligibility from current platform policy or hotel confirmation;
  flag conflicting or missing statements and say what would resolve them.

Capture direct property/room links, dates, occupancy, room count, currency and
observation time with timezone. Add map/source links for verified claims. Mark
missing/conflicting details ❓ with a resolution path. Prices and inventory are a
dated snapshot, not a hold; recheck the chosen offer before booking.

## 4. Rank and explain the trade-offs

Apply required criteria first. Exclude known failures, and put offers with unknown
required criteria in a separate pending group; do not rank them as eligible winners.
Rank eligible offers by the confirmed priority:

- **Lowest price:** comparable full-stay total first; explain meaningful drawbacks.
- **Value:** balance price with the confirmed location, comfort and terms priorities;
  show what the extra spend buys compared with the cheaper eligible alternative.
- **Comfort/higher stars:** use actual room features and condition alongside the
  requested star category, within the confirmed ceiling.

Return 3–5 strong candidates per stay, or fewer when evidence supports fewer. Name
the first choice and explain why each candidate ranks above/below alternatives.
Prefer concrete trade-offs to an opaque numerical score. State search coverage and
limitations; do not claim an exhaustive market-wide best price. Stop once the
shortlist offers clear choices and further browsing is unlikely to change the
decision; do not pad it with ineligible rooms.

| Rank | Hotel / room / rate plan | Full-stay total (all rooms) | Why this rank | Main compromise | Pending checks / links |
|---|---|---|---|---|---|
| 1 | Specific eligible offer | Currency, taxes, observed time | Fit to confirmed priorities | Concrete drawback | Offer and evidence |

If no offer satisfies all required criteria, explain the blocking conditions and
propose specific relaxations with their benefits/costs. Obtain confirmation before
rerunning with changed hard requirements; do not silently increase budget, remove
non-smoking requirements or move outside accepted areas.

## 5. Record selection and keep the itinerary consistent

Save trip-specific preferences, confirmation status, city overrides and comparison
evidence in the private plan's §2.1 supporting content. Keep preference confirmation
separate from hotel selection and booking confirmation. Preserve prior comparisons
as dated history when inputs or selections change; do not reuse obsolete quotes in
the current budget.

Use the existing `2.1.1 当前住宿（展示表）` header and its five-column schema for the
current stays. A candidate is `待确认`, a traveller-selected hotel is `已选`, and
`已预订` requires actual booking evidence. Update overview lodging, relevant day
transfers, budget, sources and rechecks when a choice changes. Regenerate lodging
inside the main itinerary's `#stays` with the existing build/check workflow; no
separate hotel HTML. This adds no render schema fields and requires no historical
plan migration. Refer to `structure.md` and `render-source.md` for output contracts.
