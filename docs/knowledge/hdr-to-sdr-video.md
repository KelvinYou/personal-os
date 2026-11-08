---
type: howto
status: active
summary: Diagnose washed out iPhone HLG Dolby Vision footage and convert HDR to Rec.709 SDR once before editing, with output inspection and frame accurate export checks.
updated: 2026-10-27
---

# HDR to SDR video conversion and export checks

[Status: OK] The Apple AVFoundation path below worked for an iPhone HLG editing
case on macOS. Recheck SDK availability, API deprecations and actual output when
porting it. This is an SDR delivery recipe, not calibrated color mastering.

## Diagnose washed out or overly white footage

Inspect the original with `ffprobe` before adding exposure or saturation filters:

```sh
ffprobe -v error -show_streams -show_format -of json INPUT.MOV
```

Read bit depth/pixel format, color primaries, transfer, matrix, Dolby Vision side
data, display rotation, frame rate and audio presence. Encoded landscape dimensions
plus a rotation matrix can represent portrait footage; inspect displayed orientation.
Do not infer the source color space from its `.MOV` extension.

A relevant iPhone format is 10-bit HEVC with BT.2020 primaries, HLG transfer and
Dolby Vision profile 8 / compatibility ID 4. [Apple's original guidance](https://developer.apple.com/av-foundation/Incorporating-HDR-video-with-Dolby-Vision-into-your-apps.pdf),
particularly pages 2 and 5–6, describes H.264 SDR export and performing color
conversion before or alongside reducing 10-bit pixels to 8-bit.

A failed FFmpeg tone-map configuration in the case produced pale, clipped-looking
clouds. The successful alternative was a managed Apple conversion. This does not
establish that a particular tone-mapping algorithm always fails.

## Convert once before creative editing

For the tested AVFoundation path, create a video composition from the source
asset, set all three composition color properties to Rec.709, and export through
an H.264 preset. The core settings were:

```swift
let composition = try await AVMutableVideoComposition.videoComposition(
    withPropertiesOf: asset
)
composition.colorPrimaries = AVVideoColorPrimaries_ITU_R_709_2
composition.colorTransferFunction = AVVideoTransferFunction_ITU_R_709_2
composition.colorYCbCrMatrix = AVVideoYCbCrMatrix_ITU_R_709_2
let session = AVAssetExportSession(
    asset: asset,
    presetName: AVAssetExportPresetHighestQuality
)
session?.videoComposition = composition
```

This is the relevant fragment, not a complete converter. The private case keeps
the tested complete source. Its mutable-composition API produced a deprecation
warning in the installed SDK; do not describe it as the current preferred API
without checking official documentation.

Confirm the actual export is H.264, 8-bit SDR and correctly oriented. Retain
normalized SDR intermediates. Subsequent cuts, resizing and audio mixing operate
on those files; do not apply another HDR transform to an already converted clip.
Color metadata flags describe pixels; changing labels alone is not tone mapping.
Correct conversion and creative grading are separate decisions. Avoid blanket
whitening, saturation or LUT changes to disguise a transform error.

Inspect matching original/converted/exported moments: clouds, white water, foliage,
faces, dark areas and adjacent overcast/sunny shots. Rec.709 tags and a successful
decode do not prove that highlights look right.

## Quantize the timeline to frames

Decimal seconds such as 0.75 do not represent an integral number of frames at
30fps. Choose cumulative boundaries in frames, then derive each shot's length:

```python
end_frame = round(cumulative_seconds * fps)
shot_frames = end_frame - previous_end_frame
```

Export shots with explicit frame counts and record those counts in the edit plan.
The accepted case used 810 frames for 27 seconds at 30fps. Derive audio alignment
from the final frame boundaries; approximate decimal timestamps can drift by a
frame. The case's sound timing had sub-frame rounding differences, not sample-
accurate mastering.

## Verify the delivered files

Run checks against the final master and preview, not just intermediates:

```sh
ffmpeg -v error -i FINAL.mp4 -f null -
ffprobe -v error -show_streams -show_format -of json FINAL.mp4
ffmpeg -hide_banner -i FINAL.mp4 -af ebur128=peak=true -f null -
```

Check expected duration/frame count, dimensions/orientation, video and audio
streams, Rec.709 properties, full decode and intentional end fades. Review cut
boundaries and beginning/middle/end frames, then play the whole film with sound.
Use measured loudness and true peak to avoid accidental level differences and
clipping; a target used in one project is not a platform-wide standard.

Use two-pass loudness normalization on the exact mixed excerpt when consistent
levels are needed, then measure the encoded output again. If dynamics matter,
confirm normalization did not flatten the intended music/location contrast.

## Implementation pitfalls worth keeping

- Discover FFmpeg features with `ffmpeg -filters` and its build configuration.
  A small installation may lack `zscale`, `drawtext` or needed audio filters.
  Choose a capable build only when the edit requires it.
- In FFmpeg expressions, nest two-argument `min` calls; a three-argument `min`
  caused a failed title render. Read the render log before retrying.
- Avoid naming a Python helper `inspect.py`: it can shadow the standard library
  and cause unrelated Pillow imports to fail.
- Cache intermediate clips by source content and render settings. Merely checking
  that an output filename exists can silently reuse stale edits after a change.
- Keep a 720p review export and a 1080p master when useful; frame counts, dimensions
  and bitrates are delivery choices rather than measures of storytelling quality.

For sequence design and creative acceptance, use the
[video editing workflow](video-editing-workflow.md).
