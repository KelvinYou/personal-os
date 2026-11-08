# Role-aware character wardrobe — Design-Lite

[Status: OK] Implemented and locally verified · 2026-11-03

## 1. Context

The owner finds the current characters too crude and explicitly requests gym clothing for Coach Planner. Existing cast identities, dark hair, Malaysian Chinese cosmetic preset and stable skin/hair/name seeds stay intact. Improve clothing silhouettes, shoes and accessories rather than applying shirt recolors alone.

## 2. Scope

Page pattern: existing office plus a close-up appearance comparison surface.
Reused components/assets: procedural person, decorative/player poses, shared Select, office navigation and data states.
New decisions: unified softer character forms with athletic, creative, study, business, travel and host wardrobes; shared model between office and preview.

## 4. Implementation

`office-character.ts` retains identity ownership and adds a pure cosmetic wardrobe resolver using only an explicit skill ID. Unassigned runtime participants use generic casual clothing; prompt text, nickname and inferred assignment cannot supply a profession. The host has an explicit cosmetic style. The scene passes the catalog-owned skill ID to a shared character model.

Coach outfit: athletic top, shorts, exposed calves, training shoes, wristwatch/headband. Makers: hoodies/overshirts and selective headphones. Study/review: knitwear/cardigans and softer palettes. Wealth: business-casual jackets/trousers. Travel: utility overshirt and a compact backpack. Role-specific variants prevent every colleague sharing one outfit. No outfit claims that a role is currently running or that an activity occurred.

Extract the existing person animation/picking logic into a reusable model, retaining click selection, reduced motion, first-person hiding, shared player pose and idle routines. A read-only `/office/characters` preview shows the same model in static standing/seated views, with real roster choices and explicit appearance-only labels. It queries no execution/observation API.

## 7. Trade-offs

Retain local editable meshes and current rig pivots, avoiding external character generators or asset/rig migrations. Accessories and clothing layers supply recognizable differences at normal zoom; faces keep a consistent stylized direction. Preview poses are cosmetic and separate from observed runtime state.

## 8. Verification

Check explicit coach outfit, generic fallback, stable identity/wardrobe and complete current-role coverage. Inspect actual front/side/back, standing/seated, role comparison and office walking screenshots. Run typecheck, focused Office tests and production browser controls/preview checks. Read the existing garden-town acceptance for unchanged terrain/layout; no layout, runtime, persistence or private-data migration is planned.

## 9. Open questions

No blocking decisions. First pass uses the owner's text brief and existing cast; visual acceptance is assessed in the actual scene, with no generated illustration used as software evidence.

## Contract review

[Status: OK] Cosmetic appearance remains separate from identity, membership and runtime evidence.

| Contract | Owner | Consumers | Verification / migration |
|---|---|---|---|
| Stable cosmetic identity | Existing `characterProfile` | Shared model, nickname consumers | Original name/skin/hair seeds preserved |
| Role wardrobe | New `characterWardrobe`, explicit catalog skill ID | Shared model, detail tint, preview labels | Coach kit and generic fallback tests; no implicit role inference |
| Employee membership | Existing skill directory/catalog | Office scene, preview selector | Registry does not add employees; selector reads actual catalog |
| Player/decorative pose | Existing Person frame logic, extracted to shared model | Office/team scene and controller | Same root object names and pivots; browser walking regression |
| Static preview pose | Explicit preview prop, preview page only | Shared model in appearance viewer | No API calls and no simulated live worker state |

Finance, private stores, execution/observation APIs, task assignment and terrain/navigation contracts are unchanged. No migration is required.

## Acceptance record

- Final production build with `NEXT_DIST_DIR=.next-office-character-final`: passed, including type validation.
- `node --test tests/office*.cjs` from `web/`: 56 passed. Covers explicit gym clothing, preserved identity, unknown/prototype-name fallback, current role coverage and all existing Office contracts.
- Appearance browser check passed on the final build: six-family comparison, coach front/side/back, seated pose, backpack, business jacket, keyboard return focus, 1440/390/320px containment and no execution/observation API requests or page errors.
- Existing player browser assertions passed unchanged on the final build using the local Apple Metal renderer: first/third/overview, movement, touch, reduced motion and focus isolation. Temporary test copies changed only the ANGLE backend flag; no assertions or deadlines were weakened.
- The software SwiftShader player run timed out while taking a first-person screenshot. A diagnostic recorded a stable viewport rectangle and only two frames across about 7.4 seconds, versus 119 frames across about 2 seconds with Apple Metal. These short diagnostic samples are not a general performance benchmark. Software-renderer performance parity and physical-phone performance remain unverified. The appearance-only software-renderer check passed.
- Opened fresh production cast, coach front/side/seated, backpack and actual Office third-person screenshots. Refined limb continuity, shoulder connections, inner-shirt shape and coach socks after inspecting the first pass. The result deliberately retains a stylized procedural cast rather than claiming photorealism or an imported skinned character library.

The updated Office remains at `http://127.0.0.1:3016/office`; the close-up viewer is `/office/characters`, reachable through Meet the cast. Reference comparison, screenshots, source hashes, renderer-specific logs and original failed-run evidence are retained under ignored `data/runtime/ai-office/design/characters/evidence/`. No live model task, commit or hosted deployment was performed.
