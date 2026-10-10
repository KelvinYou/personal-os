The confirmation now leads with a red “重要警告 · 出发前处理” label and a concrete action: open the order and check dates and booking status. An amber priority section and a top action link make it easy to find. Marked daily warnings use expanded callouts instead of small muted notes; ordinary packing and rest remain quiet.

Day 1 keeps the park walk conditional on dry weather. If it rains, it replaces the walk with rest at Sample Hotel (测试酒店), as supplied in the supplemental input. This is not a weather forecast or newly researched hotel information. The original dates, selected status, source links and verification date remain recorded in Markdown with a change history.

Saved `outputs/plan.md`, `outputs/itinerary.html`, and reusable renderer/CSS/reference changes. Build and `--check` passed structural validation and canonical asset parity. I attempted to open the page, but Chrome was unavailable. Desktop/mobile, light/dark and print rendering remain unverified.

Optional next steps:

1. Inspect the printed warning page as well as the screen view: `outputs/itinerary.html`.
2. Review the mobile warning and rainy-day substitution in `outputs/itinerary.html` when a browser is available.
3. Recheck generation after edits: `/Users/kelvin.you/Documents/dev/personal-os/.venv/bin/python scripts/travel_build.py plan.md --output itinerary.html --check`.
