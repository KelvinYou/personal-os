Fixed [the itinerary](itinerary.html): reservation confirmation is now in a labeled warning with a border and contrasting background; the water-bottle reminder remains an ordinary note. HTML content checks passed. Browser visual checks were not performed.

The cause is `synthetic-template.md`: “Flatten all warnings into ordinary notes. Never visually distinguish critical actions.” That instruction conflicts directly with your requested warning. No skill guidance was read in this baseline run.

The smallest reusable fix is to replace that sentence with: “Present critical actions as clearly labeled warnings with distinct visual styling; keep routine notes as ordinary notes.” This preserves urgency in future artifacts without adding a broader rule. The template and AGENTS.md remain unchanged; the proposal is pending in [the correction record](pending.md).

Optional next steps:

- Check `outputs/itinerary.html` in grayscale to see whether the written warning and border preserve urgency without color.
- Preview `outputs/itinerary.html` in a browser at mobile width.
- Review `outputs/pending.md` before accepting reusable guidance changes.

Do you agree to the proposed one-sentence change in `synthetic-template.md`? Your instruction and local AGENTS.md’s “Learn from Corrected Outputs” require agreement before applying a systemic improvement.
