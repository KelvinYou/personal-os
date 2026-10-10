Updated the reusable travel UI in `.agents/skills/travel-plan/assets/share.css` and its HTML reference. Future builds now use calmer grouped surfaces, larger reading text, comfortable spacing, stronger action hierarchy and a phone timeline. Existing appearance, reduced-glass and print controls remain available.

Rebuilt `itinerary.html`; build and freshness checks passed. Browser rendering was not inspected: no browser surface was enabled. Desktop/mobile appearance, contrast and print layout still need visual review.

Optional next steps:

- Review the densest day at 200% zoom in `outputs/itinerary.html` to catch reading issues before reusing the style.
- Open `outputs/itinerary.html` at 320px and 390px in light, dark and reduced-glass modes.
- Use `scripts/travel_build.py <source.md> --output <itinerary.html>` to apply the shared style to another normalized source.
