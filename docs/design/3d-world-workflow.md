# Fast 3D world construction — Design-Lite and operating guide

[Status: Warning] Tooling implemented and locally verified; latest global typecheck blocked by concurrent world work · 2026-11-08

## 1. Problem and outcome

The first Kenney office pass repeated archive inspection, size/orientation discovery, temporary capture code and server launches. Its final broad browser run took 4.4 minutes; most time was in shared movement scenarios rather than prop rendering. Future extensions should reuse local assets and a warm isolated server, produce a reviewable screenshot early, and run final regression coverage once at the scope that changed.

## 2. Owners and scope

| Contract | Owner | Consumers |
| --- | --- | --- |
| Asset aliases → bundled paths | `web/lib/office-assets.json` | KenneyAsset, asset tooling |
| Bytes, licence, source URL, SHA-256 | Each pack's `sources.json` | Asset check/import/catalog |
| Geometry, units, visual acceptance | [3D scene standard](3d-scene-standard.md) | Every scene and agent |
| Scope → required checks | `config/scene_checks.json` | Workflow CLI; this guide explains it |
| Preview launch/doctor/drive/cleanup | Existing verify-web scripts | Workflow CLI reuses them |
| Choosing the construction sequence | `.agents/skills/world-builder/SKILL.md` | Future world-building tasks |

No observation schema, movement values, private data or deployment changes are needed. Existing asset aliases and KenneyAsset props remain compatible. Generated catalogs, preview state and screenshots live under ignored `web/.scene-preview/`, outside Playwright's disposable output directory.

## 3. Everyday loop

1. For a new task, run `make scene-reset`, then `make scene-preview SCENE=office` before editing. Omit reset while continuing the same task. It starts or reuses an owned loopback server, captures a baseline and hashes the relevant source files. Leave it running while editing so Next can hot reload.
2. Run `make scene-assets QUERY=desk` to search local models and inspect natural dimensions. Use the registered alias and existing KenneyAsset helper. Edit one representative module before repeating it across the room.
3. After editing, run `make scene-preview SCENE=office` again. Open the screenshot, correct concrete visible gaps, then capture again. The first baseline is retained for the session.
4. Run `make scene-plan` to see the changed files and required checks. Run `make scene-check` once the appearance is ready. The plan escalates shared characters and navigation to all their consumers; unknown scene code is conservative.
5. Run `make scene-stop` when finished. It stops only the owned preview and keeps its build cache and evidence. `make scene-reset` explicitly starts a new baseline on the next preview.

`SCENE=characters` uses the existing cast preview; `SCENE=home` uses the home page and waits for the iframe's ready marker. `WIDTH=390 DARK=1` checks a phone-sized dark view. Preview uses reduced motion for reproducibility; interaction regression remains a separate final check.

## 4. Import a model once

Search the local catalog first. For a new Kenney model, download the official pack once and import only selected models and their dependencies:

```bash
python3 scripts/scene_assets.py archive-list /path/to/kenney_furniture-kit.zip
python3 scripts/scene_assets.py import --archive /path/to/kenney_furniture-kit.zip \
  --pack furniture-kit --model loungeSofa --alias sofa \
  --source-url https://kenney.nl/assets/furniture-kit
make scene-assets QUERY=sofa
```

The importer requires an explicit official source, verifies the archive's CC0 notice, refuses conflicting existing bytes, records hashes and dependencies, and adds the requested alias. It does not extract arbitrary archive paths. An alias is reusable via `<KenneyAsset kind="sofa" ... />` after import; no second loader or path registry is needed. Character rig conversion remains owned by `build_kenney_characters.py`.

Natural bounds and triangle counts are computed from the GLB, including node transforms. They help choose uniform scale; they do not prove the front direction. Check front/side views once and retain the result in the task's evidence rather than guessing from a filename.

## 5. Fast iteration and final acceptance

Preview is feedback, not completion. It runs local asset integrity checks and the existing real-browser capture driver, records errors/writes and produces evidence. It does not rerun all unit tests or movement journeys after each visual edit.

Final acceptance still includes `make test`, `make design-check`, the affected browser suites from the machine-owned scope map, and the visual checks in the shared standard. A shared character change reaches office, classic town, task rooms and home; camera/navigation changes retain their full relevant journeys. Adding a static office prop reaches the radar suite. Ambiguous code changes escalate rather than silently narrowing coverage. `make test-browser` remains the full release/integration sweep.

A known failing suite remains a failure. Report the exact assertion; do not omit it or change its expected value to obtain green. The earlier classic-town 18-versus-20 employee failure came from a hardcoded headcount; its check now compares the exact rendered membership against the canonical public skill registry, so legitimate new skills remain covered.

## 6. Failure behaviour and trade-offs

| Scenario | Result |
| --- | --- |
| Port belongs to another process | Refuse reuse; select another preview port |
| Asset hash, licence or local dependency invalid | Fail before browser capture; name the file |
| Browser/page error or unexpected API write | Capture evidence, fail the preview |
| Test runner clears test-results | Preview ownership and evidence survive in .scene-preview |
| No baseline / unknown changed scene code | Use a conservative check plan |
| Screenshot exists but canvas is blank | Agent opens it; technical pass alone is insufficient |

Reusing verify-web avoids another browser harness. Keeping scene layout as existing React modules avoids introducing a new scene DSL or editor before there is evidence it would save work. The catalog and alias registry remove repeated discovery without changing rendering semantics.

## 7. Verification and open questions

Tool tests cover safe imports/dependencies, transformed bounds, provenance conflicts and scope escalation. Replay the existing office using a cold and warm preview, open both captures and report measured timing rather than promising a fixed speedup. Existing verify-web defaults must remain compatible. No unresolved product choice blocks this implementation; a drag-and-drop world editor is a separate future feature.

## 8. Verification record and contract review

[Status: OK] Cold office preview took 15.14 s; warm preview 7.99 s; warm preview after Playwright cleared its output took 7.63 s. These are individual measurements on this machine, not a guaranteed latency or an agent-efficiency benchmark. State, source baseline and evidence survived the browser test run. `scene-stop` preserved the warm Next cache. Default verify-web launch/doctor/cleanup was separately replayed on port 3053 and retained its original cleanup behaviour.

[Status: OK] `make test` passed 485 Python tests, web typecheck and 102 web tests. Nine focused tool tests cover bounds, imports, path/dependency restrictions, byte conflicts, tamper detection, snapshots and scope unions. An actual original Furniture Kit archive imported a sofa into an isolated temporary root: its dependencies/provenance checked and its natural bounds were reported. No new furniture was added to the live world by this test. The three radar browser tests and the corrected canonical-roster courtyard journey passed. Desktop office, 320px office and 390px dark character captures were opened. Evidence and timing records: `web/.scene-preview/verification.json` and `web/.scene-preview/evidence/` (ignored).

| Contract | Migration / compatibility | Decision |
| --- | --- | --- |
| Asset aliases | Same keys and paths moved out of the component into one JSON owner; KenneyAsset callers unchanged | OK |
| Pack provenance | Existing manifest fields retained; new imports add source hashes, local dependencies and a pack README | OK |
| Verify-web | Optional state/output/strict flags; original defaults remain compatible | OK |
| Scene acceptance | Machine-owned scope unions plus conservative fallback; full units and affected consumers remain required | OK |
| Skill roster | world-builder is assignable and therefore appears in the canonical office roster; browser assertion checks exact membership | OK |
| Privacy and private data | Source assets/config are public; screenshots/state ignored; no finance, log or observation contract changes | OK |

[Status: Warning] A subsequent global typecheck observed concurrently added `web/components/office/world-workspace.tsx` importing a missing `./world-scene` (TS2307 and TS2769). Those files were not part of this tooling implementation and were left intact. The earlier full check passed; the latest complete working tree is not green until that separate work is complete.

Contract review: CONDITIONAL GO for local tooling use; full-tree integration remains blocked by the missing concurrent world module. No release, commit or deployment is implied. Source authority remains the shared scene standard; this guide and skill describe execution, not a competing visual standard.
