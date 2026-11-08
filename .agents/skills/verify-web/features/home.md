# Home

## Sub-features

- h1 "Home design" page with `Full screen` and `Open viewer` actions around a same-origin iframe
  (`title="Full apartment 3D preview"`, `src=/home-design/viewer`).
- Viewer: view modes `Enter & walk` / `Third person` / `Dollhouse view`; room focus `Whole home`,
  `Floor plan`, `Living`, `Dining`, `Kitchen`, `Bedroom`, `Work & movement`, `Bathroom`.
- Door select + `Close <room> door`, `Take a seat` select + `Sit down` / `Stand up`.
- Walk mode: WASD/arrows, drag to look, Escape to exit (shared 3D standard key map).

## How to get to it (user POV)

Top nav **Home** → `/home-design`; `Open viewer` → `/home-design/viewer` (full page, no nav).
The model is the owner's `web/components/home-design/apartment.html` (gitignored, local only).

## Driving it with drive.mjs

```bash
cd web && node ../.agents/skills/verify-web/scripts/drive.mjs --port 3041 \
  --route /home-design --heading "Home design" \
  --wait-for 'iframe >> [data-ready="true"]' --label home
# The viewer alone (3D proof without the page shell):
node ../.agents/skills/verify-web/scripts/drive.mjs --port 3041 \
  --route /home-design/viewer --wait-for '[data-ready="true"]' --label home-viewer
```

Proof: `before.png` shows the dollhouse model with room labels, not a "Loading your apartment" card.

## Gotchas

- Waiting for `iframe` alone passes while the iframe still shows "Loading your apartment" and an
  empty 3D area. Wait for `[data-ready="true"]` inside the iframe (`iframe >> …`).
- Missing `apartment.html` → viewer returns 503 "Home preview unavailable"; that is the error
  state working. `/home-design/viewer` answers 403 to non-local requests by design.
- Door/seat movement, collision and camera behaviour are proven by
  `make test-browser SUITES=home-interactions`, which `docs/design/3d-scene-standard.md` §5 requires
  before and after any 3D change. This journey only proves the scene loads.
- Native `<select>` controls in the viewer come from `apartment.html`, which is on the
  design-rules baseline (a known gap, not a new regression).
