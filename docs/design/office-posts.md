# Office posts — Design-Lite

[Status: OK] Implemented; local acceptance recorded below · 2026-11-06

## Outcome and scope

Browse private post carousels from the office toolbar or the existing library
wall board. A modal reader preserves the mounted scene, view and player pose.
The first release reads final images, publication copy;
it does not edit content or infer publication status.

Page pattern: overview (cover collection) → detail (carousel and copy).
Reused assets: Button, DataState, interface tokens, existing library board.
New decisions: native modal dialog for focus isolation; numbered images determine
carousel order; publication copy is displayed as literal text, never executed HTML.

## Owners and contracts

```text
data/posts/<id>/ [UNCHANGED canonical private source]
  → office-posts.ts [NEW bounded read adapter]
  → GET /api/office/posts and /posts/image [NEW local-only endpoints]
  → office workspace / library board [MODIFIED]
  → modal post reader [NEW]
```

| Contract | Owner | Consumer | Migration | Verification |
| --- | --- | --- | --- | --- |
| Existing post folder layout | data/posts/README.md | server adapter | None; no source writes | Synthetic temporary folders |
| List/detail projection | office-posts.ts | workspace and reader | New additive API | Route and filesystem tests |
| Final numbered images | post images/ | image endpoint, covers, carousel | None | Allowlist, confinement, size and signature tests |
| Local request guard | office-work-http.ts | both new routes | Reuse existing guard | Cross-origin and host rejection |
| Interaction and focus | reader / existing player controls | keyboard, pointer, touch | No key-map changes | Browser and existing movement regression |

GET /api/office/posts returns `{posts:[{id,title,date,imageCount,cover}]}`.
GET with `?id=example-2026-01-01` returns
`{post:{id,title,date,imageCount,cover,images:[{name,url}],copy,notes,verification}}`.
Only `post.md`, `publish.txt`, `verification.md` and numbered PNG/JPEG/WebP
files directly under `images/` are readable. Titles prefer the publication copy title, then the Title section,
then the first Markdown heading. Date is the folder date, explicitly creation
date rather than a publication date. Missing optional text is null. Missing
images is an empty collection; missing private source is unavailable, not empty.

GET /api/office/posts/image?id=example-2026-01-01&name=01-cover.png returns
validated image bytes. IDs and names are allowlisted; real paths must remain
inside the canonical posts root and selected post respectively. Symlink escapes
are rejected. Fixed technical read ceilings bound text and image allocation.
No private content enters public assets or persistent generated catalogs.
All responses use loopback/same-origin guards and private/no-store headers.
Errors return fixed codes without source paths. Existing APIs remain unchanged.

## Trade-offs and failure behavior

The existing wall board offers spatial discovery; a DOM reader provides legible
text and full-size images. The toolbar offers equivalent access without walking.
Native dialog provides focus trapping, Escape and inert background, including
inside the office fullscreen root. Blur clears held movement input.

| Failure | Behavior |
| --- | --- |
| Private directory unavailable | Explicit unavailable with retry |
| A post disappears or becomes invalid | Detail error with retry/back to list |
| Some folders cannot be read | Partial-list notice; valid posts remain visible |
| Missing copy | Named missing state; copy disabled when absent |
| Image missing/invalid | Error beside image; other slides remain accessible |
| Clipboard denied | Keep visible, selectable text and explain manual copy |
| Request superseded or dialog closed | Abort/ignore stale response |

Demo mode reads no private endpoints. Browser tests inject synthetic API data.
No blocking product decision remains; no publishing, persistence or schema migration
is required. Acceptance covers desktop/390/320, light/dark, focus restoration,
carousel, enlargement, copy, loading/empty/error, and pre/post scene regression.


## Acceptance and contract review

[Status: OK] GO for the local read-only feature. Canonical private files remain
unchanged; the additive routes serve only named post text and final images.
The matrix above covers the private-file owner, server adapter, endpoint and
UI consumers. There is no migration, public catalog, Python boundary or change
to observation/task contracts. No Critical drift was found.

- `make test`: 418 Python tests, Mermaid/design/knowledge gates, TypeScript and
  90 web tests passed. The subsequently added nearest-interaction test and final
  web suite passed (21 files / 91 tests); the new feature has seven focused tests.
- `make design-check` and `git diff --check`: passed. Existing chart contrast
  warnings remain outside this feature; no new design-rule violations.
- Posts browser acceptance: ordinary board click, toolbar, numbered carousel,
  keyboard arrows, enlargement/Escape, clipboard content, literal untrusted text,
  missing verification, focus restoration, unavailable/empty/retry states and
  preservation of third-person view passed. Screenshots were inspected at 1440,
  390 and 320 px in light and dark; real local content was also opened manually.
  Final synthetic evidence: `/tmp/office-posts-browser-final/`.
- Existing scene regression: home interactions, office camera, cast, courtyard
  and team passed. The combined run's strict pixel equality check for player
  focus failed once; the isolated player rerun passed (including touch controls).
  Before-change player regression also passed. This is recorded as a transient
  screenshot failure, not proof that timing-dependent pixel checks are stable.
- Renderer inspection through Three.js's devtools observe event at one fixed
  camera, without/with two cover textures: 7,730 draw calls, 1,909,735 triangles
  and 4,015 geometries in both; textures 42 → 44. This measures the new board
  without/with covers, not a historical renderer capture. The board reuses the
  previous five meshes and existing collision footprint. Before/after scene
  screenshots and real-content screenshots remain under `/tmp/`, never public
  assets. Resource evidence: `/tmp/office-posts-renderer.json`.

The reader is a solid token-based dialog, so no new transparency material was
introduced. Desktop browser and emulated narrow layouts were checked; physical
phone performance and a production-build replay remain unverified. No model
execution, publish, source-content edit, commit or deployment was performed.


## Reader simplification — 2026-11-06

The reader now shows only images and publication copy. The Post notes and sources
and Verification record disclosures were removed at the owner's request, along
with their unused CSS. Source files and the existing read API remain unchanged.
Earlier acceptance above describes the original reader; the browser regression
now asserts both disclosures are absent while retaining carousel/copy coverage.
