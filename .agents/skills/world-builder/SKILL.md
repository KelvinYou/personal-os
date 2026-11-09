---
name: world-builder
description: >
  Extend Personal-OS's 3D office or world using the local Kenney asset catalog,
  reusable scene helpers and a warm preview loop. Use for adding rooms, furniture,
  scenery, characters or modular world sections, and for requests to speed up 3D
  construction. Excludes image-only generation and unrelated 2D UI work.
---

# World builder

Build in the current Three.js/R3F runtime, using existing assets and modules first.
The owner selected original Kenney Mini characters and Modular Space Kit / Furniture
Kit surroundings. Preserve the chosen art direction unless the brief changes it.

## Start with a visible baseline

Read [the scene standard](../../../docs/design/3d-scene-standard.md), then the relevant
scene code. Use [the construction guide](../../../docs/design/3d-world-workflow.md)
for command options and import details. Do not load every historical office design.

For a new task run `make scene-reset`, then `make scene-preview SCENE=office`
(or `characters` / `home`) before editing. Omit reset during the same task.
Open the screenshot. This starts or reuses an isolated server and records the current
source hashes. Leave it running while iterating; hot reload is the fast path.
`web/.scene-preview/` owns the baseline and evidence, outside Playwright output cleanup.

## Reuse before creating

Run `make scene-assets QUERY=<name>` and inspect the model's natural bounds. Asset aliases
live only in `web/lib/office-assets.json`; use the existing `KenneyAsset` component.
Build one representative room/desk/wall module, inspect it, then repeat or instance it.
Use plain placements and reusable React modules; do not introduce a scene DSL or editor
for a one-off extension.

If the asset is absent, inspect a downloaded official pack with
`python3 scripts/scene_assets.py archive-list <zip>`, then import the selected model,
dependencies, licence and alias with the documented `import` command. Search/browse only
for missing references or new packs. Keep reference images private; imported runtime
assets require local provenance. The character converter remains the shared model owner.

Bounds suggest uniform scale; they do not establish front direction. Check front/side
views before multiplying a model across the world. Preserve original palettes and rigs.

## Iterate on the smallest useful result

Change layout and silhouette first, then material/light polish. Run the same preview
again, open it and name concrete visible gaps before the next edit. Keep the camera fixed
for comparisons. Use 390/320 px and dark checks when the layout changes.

During these visual iterations, use targeted tool/unit checks and screenshots. Run the
full unit suite and final affected browser journeys once the integrated result is ready;
repeating unrelated movement suites after each prop placement wastes feedback time.

## Finish at the right scope

Run `make scene-plan`, inspect its file list, then `make scene-check`.
The policy in `config/scene_checks.json` unions matching scopes: a generic asset rule
cannot narrow shared-character coverage. Mixed camera/room files and unknown scene code
escalate conservatively. If a dependency is missing from the plan, broaden the checks.
Never call a visual preview final acceptance, hide a failing suite or change an assertion
merely to make it green. Full release/integration checks remain `make test-browser`.

Open final screenshots, report relevant tests and remaining gaps, and link evidence.
Measure cold/warm times if claiming faster work; do not invent speedup percentages.
Run `make scene-stop` when done. It keeps the cache and evidence. `make scene-reset`
explicitly begins a new comparison baseline for the next task.

For close matching to a supplied image, also use the available `3d-reference-match`
workflow. For controls or route changes, update verify-web's feature map in the same change.
