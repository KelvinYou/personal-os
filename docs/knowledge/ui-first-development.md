---
type: howto
status: active
summary: Validate UI states independently, trace their trigger conditions to requirements, and replay the same scenarios after API integration.
updated: 2026-10-12
---

# UI-first development: appearance before integration

Treat the accepted UI as a contract, then fill in the logic that drives it.
Separate **what a state looks like** from **when that state appears** so that
visual review does not depend on a backend, a production account, or a difficult
sequence of actions.

This is a reusable development reference, not a mandatory repository workflow.
It is distilled from the local deck `ai-ui-first-workflow(1).html`, especially
sections 04–10 and 22. The deck describes a mobile page migration; the method
below also applies to new features with sufficiently clear requirements.

## 1. Build independently reviewable UI states before connecting APIs

Create a preview that uses the same presentation components intended for the
production page. Keep production requests and handlers out of the preview;
drive its appearance with local state or deterministic fixtures.

Before polishing the main state, list the meaningful scenarios:

- Loading, empty, error, complete, disabled, and submitting states where relevant.
- Conditional elements present and absent, including the resulting layout.
- Long content, supported languages, themes, keyboard visibility, and enlarged text.
- Supported platforms and widths according to the product's actual scope.

Make each scenario directly accessible and reproducible. A state that cannot be
shown has not been visually verified. Cover valid combinations and important
interactions rather than blindly enumerating the entire Cartesian product.

Rendering all conditional elements together can help inspect their individual
styles. It does not verify the layouts produced when some elements are hidden.
Review those layouts separately.

**Example:** A fee schedule should distinguish a confirmed zero fee from a
loading failure. Review both appearances before deciding how API results select
between them. An API failure must not accidentally become a successful-looking
free-fee display.

## 2. Record conditions and their evidence before wiring them into the UI

Maintain a small state contract:

| Visible state | Trigger condition | Source | Integration check |
|---|---|---|---|
| Save disabled with an explanatory error | Required selection is empty | Approved requirement | Empty selection cannot submit |
| Explicitly free fee | Effective configuration is valid and explicitly zero | Approved rule and response contract | Zero is distinct from missing data and request failure |
| Error with retry | Required request failed | Error-handling contract | Failure does not fall through to the empty or complete state |

For migrations, trace conditions to the relevant existing code. For new
features, use the current PRD, confirmed product answers, and API contract.
Resolve contradictions explicitly; a prototype demonstrates an interaction,
but does not by itself prove validation rules or backend behavior.

Investigate conditions early enough to discover missing or impossible states.
Keep that investigation separate from implementing production conditions in
the preview. The useful separation is appearance versus triggering logic;
it does not require postponing all requirements analysis.

## 3. Preserve the accepted UI as an integration regression baseline

Reuse the accepted presentation components when adding real data. Put request
handling, response normalization, and business decisions in the appropriate
API, state, or hook layer. Presentation components receive explicit display
state and callbacks rather than interpreting raw transport error codes.

Use two independent acceptance checks:

- **Visual check:** layout, content, interaction feedback, and supported environments.
- **Component check:** existing design-system components, variants, slots, and tokens
  are used where available. Similar pixels do not prove the correct implementation.

After integration, replay the original scenario list. Add newly discovered
states such as timeout, permission denial, or conflict to both the preview and
the condition contract. A successful happy-path request is insufficient.

For multi-step features, also specify data dependencies: changing an upstream
selection invalidates dependent downstream values. Missing prerequisites must
lead to a defined recovery path. Decide draft reset and restoration behavior
from requirements rather than relying on navigation history.

**Example:** Changing a country may invalidate the selected bank and account
details. Editing one currency's customer scope should preserve other currency
records if that is the approved update boundary. These rules need integration
checks in addition to visual review.

## Practical handoff

Before API integration, retain three artifacts:

1. A scenario list with a reproducible way to display each state.
2. A condition table with requirement or code references and resolved conflicts.
3. Visual and component acceptance evidence, followed by results from replaying
   the same scenarios after integration.

## Boundaries

“Frozen UI” means preserving accepted behavior and presentation during wiring.
If integration exposes a missing requirement, revise the contract and re-review
the affected states rather than forcing the implementation into an incorrect UI.

Pixel precision needs an agreed reference and review method; merely saying
“pixel-perfect” is not acceptance evidence. Use screenshots or visual comparison
when repeatability matters.

The source deck's specific navigation API claims are version-dependent and
explicitly described as source-inferred without device validation. They are not
adopted here as general rules. Likewise, a global store, a ban on URL state, a
500px breakpoint, and resetting every flow are product-specific choices.

For technically uncertain features, validate feasibility and essential API
contracts before investing in a fully polished UI. UI-first development is most
useful when appearance and business wiring can be reviewed independently.
