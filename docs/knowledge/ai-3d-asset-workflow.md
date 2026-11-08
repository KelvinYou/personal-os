---
type: howto
status: active
summary: Generate AI assisted 3D assets through reference control, geometry and PBR checks, and acceptance in the target application.
updated: 2026-11-02
review_after: 2027-02-02
---

# AI assisted 3D asset workflow

[Status: OK] Research checked on 2026-11-02. This is a working production
procedure, not an industry certification or a ranking of generators. Provider
features require rechecking before a new production run.

## Define the asset before generating

Record the target application and device, asset purpose, approximate viewing
distance, dimensions and units, forward/up axes, pivot, permitted materials,
triangle and texture budgets, and whether animation or printing is required.
Choose budgets from a representative scene on the target device; there is no
universal acceptable polygon count. Distinguish measured dimensions from estimates.

| Target | Acceptance priority |
|---|---|
| Web or game prop | Silhouette, triangles, draw calls, texture memory and load cost |
| Animated character | Joint topology, separate moving parts, skinning and deformation |
| Product or AR | Scale, hidden surfaces and material response under changed lighting |
| Offline render | Shape and shading at the final camera distance |
| Printing | Closed volume, wall thickness and printable structural details |

Use [Khronos Real-time Asset Creation Guidelines 2.0](https://github.com/KhronosGroup/3DC-Asset-Creation/blob/main/asset-creation-guidelines/RealtimeAssetCreationGuidelines.md)
as the general delivery reference. Its August 2025 edition covers geometry,
UVs, PBR, animation, LOD and publishing targets. Product recommendations about
real-world accuracy do not establish the accuracy of an AI reconstruction.

## Control the reference

For an established design, prefer image conditioning over an unconstrained text
prompt. Use a complete single subject, a simple background and diffuse lighting.
Avoid cropping, strong shadows, specular hotspots and blurred structural details.
For asymmetric or complex objects, use consistent front, side, back and
three-quarter references. Inspect generated reference views for contradictory
parts before reconstruction. A guessed back view is design input, not evidence
of the physical object. Use an A-pose or T-pose for humanoids intended for rigging.
See [Meshy's input and pose guidance](https://docs.meshy.ai/en/webapp/image-to-3d).

Keep the brief, references, prompt, provider/model version, seed when available,
settings, generation date, output hash and elapsed generation/cleanup time.
Record reference provenance and applicable asset/model terms with the output.
Personal floor plans and home details remain in the private project record;
public documentation contains reusable procedures only.

## Generate, inspect, then spend on detail

1. Generate several geometry candidates from the same brief.
2. Disable textures and inspect all sides, underside and silhouette. Reject
   fused parts, missing openings, unintended surfaces and major proportion errors.
3. Repair shape, separate moving parts and retopologize or decimate as required.
4. Finalize UVs, then bake or generate materials for the final topology.
5. Rig if needed; test representative extreme joint poses.
6. Export, reimport and inspect the exact delivery artifact in the target runtime.

This ordering avoids paying for detailed textures on rejected geometry. Meshy
recommends [remeshing before texturing](https://help.meshy.ai/en/articles/9996860-how-to-use-meshy-image-to-3d).
Automatic quad output does not establish good joint deformation. For static
props, evaluate shading and performance rather than requiring quads; glTF
triangle primitives are suitable for delivery.

## Require materials that survive changed lighting

Use a supported PBR workflow. Inspect base color, roughness, metallic and normal
channels where applicable, UV seams, texture density and tangent/normal conventions.
Follow the target format's color-space and channel-packing rules; do not treat
numeric material maps as display color. Avoid unintended shadows and highlights
painted into base color. See [glTF PBR](https://www.khronos.org/gltf/pbr).

A practical local acceptance procedure is to compare neutral, warm and side-lit
setups with a fixed camera and exposure, then inspect a gray material override.
These three setups are our test method, not a mandatory Khronos standard.
Keep deliberate stylized shading explicit in the brief.

## Verify delivery separately from appearance

Keep an editable source and a delivery artifact. GLB is convenient for web
transport; FBX or other formats depend on the receiving pipeline. Confirm axes,
scale, pivot, textures and animation after export. In glTF one unit is one meter;
choose a pivot appropriate to placement or articulation. Use compression only
when the target loader supports it and compare the compressed result.

Run [Khronos glTF Validator](https://github.khronos.org/glTF-Validator/) for glTF
or GLB. A clean report establishes format checks, not visual quality, printable
geometry or animation suitability. Check actual loading, frame cost, rendered
draw calls, triangles, texture memory and missing-resource errors on target devices.

Compare original and candidate under identical camera, viewport, lighting and
material modes. Count rendered geometry separately from unique geometry and
shadow passes. Record raw frame timings and environment; do not call one timing
sample a performance benchmark. Visual preference requires a separate review.

## Select a tool by the experiment

| Route | Verified capability | Qualification |
|---|---|---|
| [Meshy](https://docs.meshy.ai/) | Image/text generation, PBR texturing and remeshing | Inspect final geometry despite game-ready labels |
| [Tripo](https://www.tripo3d.ai/help/getting-started/what-features-does-tripo-have) | Generation, segmentation, retopology, UVs, rigging and DCC transfer | Feature availability and output require checking |
| [TRELLIS.2](https://github.com/microsoft/TRELLIS.2) | Image-conditioned assets with PBR attributes | Official setup lists Linux and at least 24 GB NVIDIA GPU memory |
| [Hunyuan3D-2.1](https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1) | Image-conditioned geometry and PBR generation | Check hardware and model/license terms before deployment |
| AI authored Three.js geometry | Reproducible, editable local mesh construction | Code generation is a different method from image-to-3D inference |

Provider claims and model demonstrations do not establish a universal winner.
Use the same brief and compare total time to an acceptable asset, including
cleanup, rather than generation speed or a selected preview alone.

## Minimal prop trial

Replace one static prop inside an existing scene. Keep the original selectable,
its placement fixed, and the rest of the scene unchanged. Add gray and relighting
checks and record geometry, materials and runtime observations. Preserve the
candidate source and results; promote it only after technical and visual review.
A local procedural trial can validate this acceptance loop, but cannot establish
the quality of Meshy, Tripo or another unexecuted generator.
