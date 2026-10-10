Updated the source and reusable renderer/CSS. The pre-departure confirmation has a full-width red warning panel, an explicit label, and an action to check the hotel, dates, and payment status against the order. Urgent day labels remain red; ordinary packing stays neutral. The visible rain alternative replaces the park walk with rest at Sample Hotel, as supplied. Source links, verification date, and generated provenance remain intact.

Build and `--check` passed. Opened the generated local page in Chrome and inspected its desktop screenshot; mobile, dark appearance, and print layout were not visually checked.

Optional next steps:

- Check the rain alternative beside Day 1 in `itinerary.html` before leaving, so the change is actionable at the time of the walk.
- Open `itinerary.html` on a narrow phone viewport to verify wrapping.
- After editing `plan.md`, rerun `scripts/travel_build.py plan.md --output itinerary.html --check` with the provided Python interpreter.
