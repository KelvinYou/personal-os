# Synthetic correction queue

## 2026-10-07 — Preserve critical-action warnings

- Status: pending
- Observed result: The supplied itinerary presented “Confirm reservation before departure.” as an ordinary paragraph alongside “Bring a water bottle.”
- User correction: “This misses the intent: the critical action needs a clear warning. Fix the result first, then check whether conflicting docs or skills caused it. If a small systemic improvement would prevent recurrence, explain it and get my agreement before applying it.”
- Evidence: `synthetic-template.md` says “Flatten all warnings into ordinary notes. Never visually distinguish critical actions.” This reusable instruction conflicts directly with the requested warning.
- Smallest proposed fix: Replace that template sentence with “Present critical actions as clearly labeled warnings with distinct visual styling; keep routine notes as ordinary notes.” Await agreement before changing the template.
- Proposed AGENTS.md wording change for review only: “Reusable presentation guidance must preserve explicit critical-action warnings.” The template fix is preferred; no AGENTS.md change is needed to fix the current artifact.
- Current artifact repaired; no reusable guidance change applied. No skill guidance was read or invoked in this baseline run.
