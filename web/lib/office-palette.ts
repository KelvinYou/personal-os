// Office town palette: the code side of docs/design/3d-scene-standard.md §4 "Office town parameters".
// tests/scene-standard.test.ts fails unless every hex here appears in that section and vice versa.

export const townPalette = { grass: "#9fb27a", paving: "#e3d8c2", kerb: "#cbbd9e", trunk: "#8a6a4a", soil: "#6f5a45",
  leaves: ["#71864b", "#829559", "#5f7a45"], pine: ["#536d41", "#4d6a48", "#5d7a4c"], flowers: ["#ef925b", "#f2c94c", "#f4f1e6", "#d97a9b"], lamp: "#464d49", glow: "#fff0c8" };

/** Current static sky, background and fog colour. */
export const townSky = "#dfe8e2";

/** Planned time-of-day sky (docs/design/office-immersive-world.md, phase 3): local "HH:MM" → sky/fog colour.
 *  Not rendered yet; phase 3 interpolates these in the configured timezone and replaces `townSky`. */
export const townSkyAnchors: readonly { at: string; color: string }[] = [
  { at: "00:00", color: "#1c2740" },
  { at: "06:00", color: "#1c2740" },
  { at: "07:30", color: "#cfe3ee" },
  { at: "12:00", color: "#a9d2ea" },
  { at: "19:15", color: "#e8b996" },
  { at: "20:15", color: "#1c2740" },
];
