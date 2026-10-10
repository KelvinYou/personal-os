# City checklists: places and food

Read when composing or revising a full trip plan or itinerary page. These lists
make the traveller's priorities easy to find and reconcile with the route; they
do not create an additional sightseeing or eating schedule.

## Shared contract

- Group by actual destination, not railway/airport transfer stops. Include the
  user's accepted choices; add researched recommendations only where useful.
  Do not fill every category or city with invented recommendations.
- Labels express this traveller's priorities, not a universal ranking or a
  claim that every item is guaranteed. Define them once in the reader's language.
- Each item names what to see/eat, why it fits, its day or meal/area, map links,
  and any condition that changes whether it can be done. Keep the source plan's
  first-mention 高德 + Google map convention; HTML uses the established provider
  choice with individual place links rather than a generic city search.
- Ground descriptions and recommendations in appropriate sources. Record the
  verification date and sources in the plan; keep a short supporting note in the
  page where useful. Old guides support location/food ideas, not current opening,
  prices or queues. Do not claim inaccessible social-media recommendations were
  researched. Unknown details remain pending with a way to confirm them.

## Must-visit list — §4.1 / HTML #places

Use city headings with `Priority | Place | Day/route | Experience / conditions`.

| Label | Meaning |
|---|---|
| 必去 / Must visit | Prioritise the accepted core experience in the planned route. |
| 顺路 / Along the route | Combine with a nearby main stop; shorten if time or energy runs low. |
| 备选 / Alternative | Replace another stop or use genuine spare time; do not silently add it. |

Add qualifiers when relevant: `通行确认后`, `先预约`, `短看`, `择一`.
An unassigned wish is explicitly `未排入 / Unscheduled` with its reason or the
information needed to place it; listing it as a must-visit does not schedule it.
Differentiate a district, its landmarks and transit access points. Adjacent
places can share an entry, but each remains named and easy to locate.

Coverage pass: compare all accepted places against the daily timelines and
fallbacks. Account for walking slopes, transfers, queues, meals, rest and luggage.
Explain the time trade-off when adding a place. Avoid promising all stops will
be completed when a race closure, operating status or unbooked train controls
the route. A fallback must not contradict the checklist's conditions.

## Must-eat list — §5 / HTML #food

Use city headings with `Priority | Dish | How to order / why | Meal/area`.

| Label | Meaning |
|---|---|
| 必吃 / Must eat | Reserve a meal or appetite for the traveller's priority dish. |
| 备选 / Alternative | Substitute within an existing meal. |
| 顺路尝鲜 / Try if nearby | Optional small taste where the route already passes. |

Qualify `二选一 / choose one` and `小份 / small portion` when useful. Say which
meal and neighbourhood fit; account for group size, dietary preferences and
appetite. Do not require eating the whole list. Dish recommendations do not
imply a particular restaurant is open or verified; distinguish a dish from a
candidate shop, and mark shop hours, price and queue estimates appropriately.
Do not add a cross-town detour solely to complete a food list. Include numerical
costs only when sourced or clearly marked as estimates/pending.

## HTML composition

Reuse `.grid`, `.practical-card`, `.eyebrow`, `.plain`, `.tag`, `.sub` and
`.hotel-links`; no new trip-specific CSS is needed. Put the city places section
before the city food section, and expose both in top navigation. Keep important
booking/closure constraints visible, not only in collapsed supporting notes.

```html
<section id="places">
  <div class="section-head"><h2>Must-visit places</h2></div>
  <p>Must visit prioritises this route; alternatives replace rather than add stops.</p>
  <div class="grid">
    <article class="practical-card">
      <p class="eyebrow">Destination</p><h3>The core experience</h3>
      <ul class="plain"><li>
        <span class="tag">Must visit · reservation required</span>
        <strong>Actual place name</strong>
        <p>What to experience and the condition that matters.</p>
        <p class="sub">Planned: <a href="#day-1">Day 1 · view the day</a></p>
        <div class="hotel-links"><a href="ACTUAL_MAP_URL">Place · map ↗</a></div>
      </li></ul>
    </article>
  </div>
</section>
```

Replace illustrative labels/URLs with real content. `#food` uses the same card
pattern, with meal/area rather than sightseeing durations. Each assigned place
should link to its actual day anchor; multi-day opportunities can have multiple
day links. Unscheduled alternatives have an honest status instead of a fake date.

## Revision and validation

Read both existing artifacts before editing. Sync overview, daily timeline,
checklists, map/day links, fallback conditions and freshness notes. Keep prior
verification dates for facts not rechecked. Preserve the skill's offline assets,
theme/print controls, selected/pending hotel statuses and visible blockers.

Run source-plan lint and `validate_share.py PATH --days N --checklists`. The
checklist flag checks sections, navigation and presence of city cards, not
recommendation quality, per-city completeness or semantic schedule agreement;
review those manually. Hotel-only derivatives (`--days 0`) omit these sections
and the flag. Legacy itinerary pages can use the structural-only command until
their checklists are updated. Inspect actual desktop/mobile renders when browser
tools are available; report a concrete rendering limitation rather than claiming
an unperformed visual check passed.
