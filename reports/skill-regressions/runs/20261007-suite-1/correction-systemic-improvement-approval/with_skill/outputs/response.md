Fixed [itinerary.html](itinerary.html): reservation confirmation now appears first in a labeled warning with a border and bold text. Content checks passed; browser visual checks were not performed.

The supplied `synthetic-template.md` directly caused the conflict: it instructs flattening all warnings. Proposed replacement: “Keep critical actions in a clearly labeled, visually distinct warning before ordinary notes.” This would prevent the same suppression on reuse. The template and AGENTS.md remain unchanged; the correction is recorded as pending in [pending.md](pending.md).

Do you agree to that one-sentence template change? Agreement is required by your instruction and local AGENTS.md’s “Learn from Corrected Outputs” rule: “seek the user's agreement before applying it.”

Optional next steps:

- Preview `outputs/itinerary.html` at a narrow viewport to check the warning remains prominent.
- Review the proposed sentence in `outputs/pending.md`.
- After agreement, update only the conflicting sentence in `synthetic-template.md`.
