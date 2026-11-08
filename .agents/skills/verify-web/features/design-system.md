# Design system

## Sub-features

- h1 "Design system & components": the reference surface for every control and data state.
- Composition and gallery forms (`Refresh sample`, `Save sample`, `Workspace name`, `Notes`).
- Privacy toggle demo (`#privacy`), chart states (`Empty`, `Single point`, `Complete`),
  data-state select (`Data state`), asset-history preview (`#asset-history-preview`).

## How to get to it (user POV)

Top nav **Design** → `/design-system`. Static fixtures only; no private data, no writes.

## Driving it with drive.mjs

```bash
cd web && node ../.agents/skills/verify-web/scripts/drive.mjs --port 3041 \
  --route /design-system --heading "Design system & components" \
  --click "Refresh sample" --expect-text "Sample refreshed." --label design-system
```

Proof: `Sample refreshed.` appears after the click; `writes` stays empty (interactions are local).

## Gotchas

- This page is the safe place to prove a shared component change; finance/office pages then
  prove integration. It is not visual approval on its own (`docs/dev-sop.md` UI acceptance).
- Screenshots must use `caret: "initial"` (drive.mjs does). Playwright's default caret hiding
  injects a style before hydration and produces a false hydration-mismatch console error.
