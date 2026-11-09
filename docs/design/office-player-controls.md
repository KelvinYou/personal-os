# Office player controls

> **Superseded / frozen (2026-11-08):** the office direction is owned by [the attention radar](office-attention-radar.md). This view remains at `/office?scene=town`; bug fixes only.

[Status: OK] Implemented and locally verified · 2026-11-03

## Scope and acceptance

Control the existing kelvin.ai avatar with overview, first-person and third-person cameras. All modes share one player pose; switching cameras never teleports the avatar. Before the first control action the host remains seated. Entering play stands it in the clear main aisle. Overview retains the last standing position after play and preserves existing worker selection and camera controls.

Page pattern: existing room plus compact camera switch and movement controls.
Reused components/assets: OfficeScene, Person, original host character, room geometry, existing office controls and Three.js cameras.
New decisions: drag-to-look without mandatory pointer lock, scoped keyboard input, explicit touch controls and collision against furniture/perimeter. No execution, observation, persistence or private-data contract changes.

## Plan

1. Pure player movement and collision geometry with focused tests: normalized diagonal movement, frame-rate-safe movement, aisle access, furniture/perimeter collision and camera-wall clearance.
2. Bind the same player pose to the existing host, a perspective camera and first/third-person controls. Keep overview orthographic; hide the host mesh in first person. Keyboard input is active only within the focused room, clears on blur/hidden/mode change, and ignores editing controls.
3. Desktop/touch HUD with WASD/arrows, Q/E turn, drag look, V camera toggle, Escape overview and reset position. Explicit movement works when decorative animation is paused/reduced.
4. Build and inspect actual baseline/first/third/walk/overview screenshots, including narrow viewports. Verify keyboard release, focus isolation, touch release and preserved observation/task UI.

## Bounds

Static collisions derive desk/chair locations from office-life and match amenity footprints. The third-person boom shortens at perimeter/glass partitions; it does not turn into a second movable avatar. This is flat-floor navigation, without jumping, stairs, agent state changes or model execution. The room's visible geometry and character art remain the design target.

## Acceptance

- `node --test tests/office*.cjs` from `web/`: 48 passed, including normalized movement, perimeter/furniture/glass collision, collision sliding, large-frame caps and third-person boom clearance. Existing execution, history and observation contracts passed unchanged.
- `npm --prefix web run typecheck` and `NEXT_DIST_DIR=.next-office-player npm --prefix web run build`: passed.
- `web/tests/office-player-browser.mjs`: actual production WebGL, synthetic demo roster, reduced motion, first-person movement, V switch, third-person following, Escape overview, retained host position, keyboard/UI focus isolation with static canvas comparison and touch press/release. 1440px, 390px and 320px; no page errors or document overflow.
- `web/tests/office-team-browser.mjs`: existing worker labels, selection, native-team view, keyboard/fullscreen, reload and results passed against the new scene with synthetic endpoints. No live model work was started.
- Actual screenshots inspected in `/tmp/office-player-evidence/`; final captures in its `final/` directory. A lamp obscured the original third-person starting camera; moving the spawn from z=2 to the clear aisle at z=5 and adding tall-prop camera clearance removed it in fresh desktop and narrow captures.
- Editable sources: `web/lib/office-navigation.ts`, `web/components/office/office-player.tsx` and `web/components/office/office-scene.tsx`. Existing architecture and private stores are unchanged.

The player pose is local to the mounted scene and resets on reload/remount. Collisions cover static furnishings and bounds, not dynamic worker-to-player physics. Physical-phone performance is unverified; narrow screenshots and input tests use browser emulation. Decorative motion can remain paused while the user explicitly walks. No commit or deployment was performed.

## Subsequent layout revision — 2026-11-03

The [courtyard studio](office-courtyard.md) replaces the earlier bench rows and meeting-glass geometry. Player input, shared pose and camera switching retain the implementation verified above. Static furniture, garden and tall-prop collisions now derive from the same presentation layout consumed by the scene. Current acceptance and screenshots belong to the courtyard revision; the earlier records above describe the preceding room.

## Subsequent garden-town revision — 2026-11-03

The approved [modern garden town](office-garden-town.md) supersedes the courtyard floor with five pavilions, organic terrain and a Coach Studio gym. Earlier acceptance records above describe their original revisions. Current layout, collision and visual evidence belong to the garden-town document.
