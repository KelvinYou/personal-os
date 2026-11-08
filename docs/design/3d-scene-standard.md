# 3D scene standard

[Status: OK] Active shared standard · Applies to `/office`, `/office/characters`, `/home-design` and any new scene · 2026-11-04

This is the one standard for real-time 3D in Personal-OS. The office and the home follow the same rules for units, colour, lighting, materials, movement, cameras, view switching and acceptance. A scene may declare only the parameters in §4: scale factor, palette, available views and spawn points. Everything else comes from this document. If a rule does not fit a scene, change the rule here first; do not add a local exception.

| Question | Owner |
|---|---|
| Scene conventions, navigation feel, acceptance | This document |
| Generating an asset (image-to-3D, providers, retopology, PBR checks) | [AI assisted 3D asset workflow](../knowledge/ai-3d-asset-workflow.md) |
| 2D interface around the canvas | [Interface design guide](../design-system.md) |
| Office layout, seats, walls, walkable ground | `web/lib/office-layout.ts` |
| Character identity and wardrobe | `web/lib/office-character.ts` |

## 1. World and rendering

### Units, axes, scale

- 1 unit = 1 metre. +Y is up. The ground is at `y = 0`.
- A placeable asset's pivot is the centre of its floor footprint. State its front direction in a comment beside the factory (example: `+Z is the back`).
- Each scene declares one `worldScale` (§4). Every human-relative number in this document is a real-world value multiplied by `worldScale`: speeds, eye height, collision radius and camera distances. One scene never mixes two scales.

### Engine and imports

- Three.js comes only from the version pinned in `web/package.json` (currently `0.187.0`). React scenes use `@react-three/fiber` and `@react-three/drei`.
- Standalone HTML scenes load Three.js and addons through the local `/home-design/three/` and `/home-design/addons/` routes. The only allowed CDN URL is the standalone fallback, which must name the package version. Addons are added to the allowlist in `web/app/home-design/addons/[...module]/route.ts`, never by widening it.
- Navigation and camera logic lives in one shared, framework-free module that both scenes import (§6, drift). Scenes provide only world geometry and parameters.

### Colour pipeline

- Renderer: sRGB output, ACES Filmic tone mapping, exposure close to 1.0.
- Colour maps, including `CanvasTexture`: `SRGBColorSpace`. Normal, roughness, metalness and AO maps: `NoColorSpace`. Normal maps use the OpenGL convention.

### Lighting rig

1. A warm sky/ground `HemisphereLight` (plus `AmbientLight` only if needed).
2. One warm key `DirectionalLight` (around `#fff0d4`), the only shadow caster. Shadows use `PCFShadowMap` (Three.js 0.187 removed `PCFSoftShadowMap` and falls back to it with a warning), map size 2048 for still/HQ and 1024 while moving, `normalBias ≈ 0.035`, and a shadow camera fitted to the scene bounds.
3. One cool fill `DirectionalLight` (`#e3ebff` to `#f2f7ff`), no shadows.

Point lights are allowed only for visible lamps and never cast shadows. An optional HDR environment comes from local, provenance-recorded files (see §1, assets).

### Materials and geometry

- Use `MeshStandardMaterial`. Matte roughness is `0.7–1.0`. `metalness > 0` only for metal. Glass is transparent, opacity ≤ 0.3, `depthWrite: false`.
- `MeshPhysicalMaterial` is allowed for close-up fabric and wood that use PBR maps.
- Colours come from the scene palette (§4). A new hue is added to the palette first.
- Build from primitives and shared helpers before importing meshes. Use about 24 segments for visible cylinders and 8–12 for small details.
- Canvas textures are deterministic: use the seeded LCG (`seed = seed * 16807 % 2147483647`), never `Math.random()`.
- Every geometry and texture that a scene creates is disposed on unmount or replacement.

### External assets and provenance

- No remote requests at runtime. Files live in `web/public/<scene>-materials/`, with a `README.md` and a `sources.json` recording source URL, download URL, licence, bytes, SHA-256 and verification date (pattern: `web/public/home-materials/`).
- Licence: CC0, or a licence recorded in `sources.json` that permits local redistribution.
- Reference images, floor plans, concept art and screenshots stay in ignored `data/runtime/…/design/`, never in `web/public/` or `docs/`.

## 2. Navigation: movement and controls

Benchmarks are modern game character controllers. Unity's Starter Assets third-person controller defaults to a 2.0 m/s walk, a 5.335 m/s sprint, a speed change rate of 10, a 0.12 s rotation smoothing toward the movement direction, and a camera pitch clamp of +70°/−30°. Values below that differ from those defaults are tuned for indoor scenes and are marked.

### One key map everywhere

| Input | Action |
|---|---|
| W A S D | Move relative to the camera's facing. A / D also swing the camera behind you (chase camera, below), in first and third person alike |
| ↑ ↓ | Same as W / S |
| Shift (hold) | Run |
| Drag (left button or touch) | Look / orbit |
| ← → | Turn the view (keyboard look). There is no Q / E |
| Scroll / pinch | Overview zoom; third-person boom length |
| V | Toggle first ↔ third person |
| F | Interact with the nearest target: door, seat or person |
| Esc | Return to overview |
| R | Reset to spawn |

Keys are captured only while the scene has focus and never while focus is in a form control. All held keys clear on blur, on `visibilitychange` and on view change. Do not add a scene-specific key without adding it to this table.

### Touch

- A bottom-right analog joystick (120 px): dead zone 0.15, and speed scales with deflection. Plus a labelled Run button.
- Drag anywhere else on the canvas to look. There are no turn buttons on touch.
- View switch, interact and exit are labelled buttons of at least 44 px.

### Locomotion feel

| Parameter | Value (× `worldScale`) | Note |
|---|---|---|
| Walk speed | 1.8 m/s | Between real walking (about 1.4) and Unity's 2.0; indoor scale |
| Run speed | 3.6 m/s | Indoor; Unity's sprint of 5.3 is too fast for rooms |
| Acceleration | `v += (target − v) · (1 − e^(−10·dt))` | Rate 10 ≈ Unity `SpeedChangeRate`; about 0.2 s to full speed and to a stop |
| Collision radius | 0.2 m | Slide along walls; substep so a thin wall cannot be skipped |
| Keyboard turn | 2.0 rad/s, eased in over 0.1 s | Accessibility path; the mouse is the main look input |
| Diagonal | Normalised | Never faster on diagonals |
| `dt` clamp | 0.1 s | Prevents teleporting after a slow frame |

- First person: the same scheme as third person. The avatar is hidden, but it still turns toward its travel direction, and A / D arc the view.
- Third person: movement is camera-relative, and the avatar turns toward its movement direction with 0.12 s smoothing. S walks the avatar toward the camera; it does not moonwalk backwards. Turning the camera without moving does not turn the avatar.
- The avatar's walk animation speed follows actual velocity, so no foot sliding while it accelerates or presses against a wall.

## 3. Cameras and view switching

People: every scene draws a person with `web/lib/character-builder.mjs`, which owns the geometry. Scenes only place and animate the figure, and the office's `office-character.ts` owns identity and wardrobe. The office scales figures by `worldScale` (1.37), so a real-scale scene scales the figure by `1 / 1.37`. Sitting while in third person switches to first person, and standing up restores the previous view.

### Look input

- One look sensitivity for both axes: 0.004 rad/px, the same in every scene. Look input maps 1:1 to rotation with no smoothing. Damping on user-driven rotation feels floaty and contributes to motion sickness.
- Pitch clamp: ±75° in first person, −30° to +70° in third person.
- No head bob, camera shake or motion blur. Field of view is adjustable (Xbox Accessibility Guideline 117).

### First person

- Eye height 1.6 m. Vertical FOV 60° by default, adjustable from 50° to 80°. Near plane 0.05.

### Third person

- Boom (spring arm) length 3.0 m, adjustable by scroll from 1.5 to 4.5 m. The camera looks at the avatar's head height.
- Chase camera (the GTA convention): while the avatar walks forward or sideways, and not toward the camera, the camera yaw swings toward the avatar's facing. Recenter gain 2.5, capped at 1.8 rad/s, so a held A or D draws a gentle arc and W alone does not rotate the view. It waits 1.0 s without look input (mouse drag, ← →). Walking toward the camera (S) never swings it. The same rule applies in first person, so both views share one control scheme and only the camera placement differs.
- The camera position follows with critically damped smoothing of about 0.08 s. Rotation is never smoothed.
- Collision: when something blocks the line from target to camera, the boom shortens immediately, with no easing, so the camera never clips. It eases back out over about 0.3 s once clear. Under 0.7 m the avatar fades out instead of filling the screen.

### Overview

- Perspective camera with a narrow vertical FOV of 32° for a near-isometric read, near plane 1. It is not orthographic, so it blends to the walk cameras without a projection pop.
- Drag to orbit, scroll or pinch to zoom (exponential, clamped), right-drag or two-finger drag to pan. Orbit damping factor 0.1, the only damped user input.
- Selection or focus moves the camera with a 0.5 s ease. Selecting alone never resets a camera the user positioned.

### Transitions

| From → to | Transition | Reduced motion |
|---|---|---|
| Overview ↔ first/third person | 0.6 s ease-in-out camera travel from the current camera to the player camera; FOV interpolates | Cut |
| First ↔ third person | Boom grows or shrinks over 0.3 s ease-out; the avatar fades as it passes 0.7 m | Cut |
| Room or preset jump while walking | Cut to the background colour, then a 0.3 s fade-in over the new position | Cut |
| Sit down / stand up | 0.4 s ease to the seat or standing pose | Cut |

Doors ease over 0.5 s (cut under reduced motion). Their logical state and collision change at the first frame, so a door never blocks or admits the player differently from what the screen finally shows.

Movement input remains live during a transition, and the transition targets the live pose rather than a stale one. A projection-type change is never an instant cut, because that is the main source of the "jarring switch" feeling.

## 4. Per-scene parameters (the only allowed differences)

| Parameter | Office · garden town | Home · Walnut House |
|---|---|---|
| `worldScale` | 1.37 (stylized; desk top 1.22) | 1.0 (real-world estimates) |
| Views | Overview, first, third | Overview, first, third |
| Interact targets | People, workstations | Doors, seats |
| Surface detail | Flat colours, light canvas textures | PBR maps and HDR environment |
| Background | `#f0ede4` | `#f8f6f0` overview, `#e3e6e0` walking |
| Neutrals | cream `#ede6d6`, wall `#e8ddc7` | wall `#f1e9db`, linen `#eee5d1` |
| Wood | walnut `#b98a57`, light `#caa679` | walnut `#a58460`, oak `#c5b094` |
| Accent | sage `#929b7e`, leaves `#71864b` / `#829559` / `#536d41` | olive `#788064`, brass `#a58c58` |
| Dark / metal | `#464d49` | `#323533`, metal `#b4a083` |
| Ground | grass tint `#a6ab80` (soft olive, large-scale blotches), kerb `#cdbf9f`, paving `#e9dcc3`, floor `#f3e8d3` over canvas wood `#dcc4a2` | n/a |

Both palettes stay warm, low-saturation and matte, so a prop can move between scenes by rescaling and re-tinting.

## 5. Acceptance for each 3D change

1. Run `make test` and `make test-browser` (specs in `web/tests/browser/`: `office-player`, `office-camera`, `office-courtyard`, `office-team`, `office-characters`, `home-interactions`). Pure navigation logic has unit tests for acceleration, diagonal normalisation, the `dt` clamp, collision sliding and boom collision.
2. Take fixed-camera screenshots before and after. Check new assets with a gray override and with neutral, warm and side lighting.
3. Feel check for navigation changes: walk a full loop, bump into a wall, run, toggle V mid-stride, and press Esc mid-stride, in both scenes. Record anything that stutters, pops or clips.
4. Check that the layout holds at 1440, 390 and 320 px, with touch emulation. Expect no console errors and no external requests. Check reduced motion.
5. Record the `renderer.info` before/after delta (draw calls, triangles, geometries, textures) at a fixed camera, and explain any rise above 10%. Store evidence in ignored `data/runtime/`.

## 6. Implementation status

The movement and camera numbers live in `web/lib/scene-standard.mjs`; `web/tests/scene-standard.test.ts` fails if this document and that file disagree.

| Item | Office | Home |
|---|---|---|
| Shared module (speed, acceleration, run, collision radius, look sensitivity, pitch, eye height) | Done | Done (served by `/home-design/shared/`) |
| Camera-relative movement, avatar turns toward travel | Done | Done |
| Third-person boom: instant shorten, eased recovery, follow smoothing, scroll length | Done | Done (also clamped below the ceiling) |
| One shared character (`web/lib/character-builder.mjs`; identity from `office-character.ts`) | Done (`OfficePerson` only animates it) | Done (kelvin.ai via `/home-design/shared/kelvin-look.json`) |
| Key map: Shift, V, R, Esc, F | Done (F selects the nearest colleague) | Done; F handles door, seat and stand |
| Touch joystick plus Run | Done | Done |
| Perspective overview (FOV 32) | Done | Done (already perspective) |
| Overview ↔ walk 0.6 s travel; first ↔ third 0.3 s; focus 0.5 s | Done (`CameraBlend`) | Done (overview ↔ walk, focus) |
| Room jump while walking | n/a | Done: cut to background colour, then 0.3 s fade-in |
| Sit / stand ease 0.4 s | n/a | Done |
| Door open / close ease 0.5 s (state and collision flip at once; only the shown angle eases) | n/a | Done |
| Shared floor collision (`web/lib/scene-floor.mjs`) | Done | Done (served by `/home-design/shared/`) |
| Adjustable FOV (50–80°) | Done | Done |
| Reduced motion | Cuts | Cuts |
| Browser evidence (Chrome, SwiftShader flags) | `office-player`, `office-camera`, `office-courtyard`, `office-team`, `office-characters` pass | `home-interactions.spec.ts` passes |

The avatar-fade and boom-grow effect for first ↔ third is produced by blending the camera pose over 0.3 s together with the 0.7 m avatar fade; it is not a separate boom animation.

## 7. Known drift: migrate, do not copy

| Drift | Where | Target in this standard |
|---|---|---|
| An orthographic overview cuts instantly to a perspective walk view | `office-scene.tsx` | §3 perspective overview and 0.6 s travel |
| Overview naming differs ("Dollhouse view", "Enter & walk") | `apartment.html` | Overview / First person / Third person |
| The office has no `renderer.info` readout | `office-scene.tsx` | Dev-only stats readout |
| `Block` / `Cylinder` / `Mug` helpers duplicated | `office-scene.tsx`, `office-character-model.tsx` | Shared helper module |

## Sources

- Unity Starter Assets third-person controller defaults, checked through community copies of the source: [gist](https://gist.github.com/bzgeb/715653b15b143a243a7992c5f4d6c5b1), [walkthrough](https://velog.io/@_hoya_/Unity-ThirdPersonController). Re-check against the installed package version before citing exact numbers.
- [Xbox Accessibility Guideline 117](https://learn.microsoft.com/en-us/gaming/accessibility/xbox-accessibility-guidelines/117): avoid or allow disabling camera shake, bobbing and motion blur; adjustable field of view.
- [Game Accessibility Guidelines: FOV default](https://gameaccessibilityguidelines.com/if-the-game-uses-field-of-view-3d-engine-only-set-an-appropriate-default-for-the-expected-viewing-environment/).
- John Nesky, [50 Game Camera Mistakes](https://gdcvault.com/play/1020460/50-Camera), GDC 2014: background on camera collision and line of sight.
