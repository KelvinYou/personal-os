// Office render budget (docs/design/3d-scene-standard.md §4 Office town parameters).
// Fullscreen multiplies drawing-buffer pixels; cap them so a large display does not multiply GPU fragment work.

/** Drawing-buffer pixel budget. Provisional until the immersive-world phase 1 baseline measures it. */
export const OFFICE_PIXEL_BUDGET = 3_000_000;
/** The existing device-pixel-ratio cap of the town Canvas. */
export const OFFICE_DPR_CAP = 1.75;
/** Canvas width (CSS px) below which workstation buttons and building summary boards are not projected:
 *  they would stack into the camera toolbar or cover the town. Building names always show. */
export const MIN_DETAIL_CANVAS = 560;
const DPR_FLOOR = .5;

/** Effective DPR: min(device, cap, √(budget / CSS pixels)), never below the floor. */
export function budgetDpr(deviceDpr: number, width: number, height: number, budget = OFFICE_PIXEL_BUDGET, cap = OFFICE_DPR_CAP): number {
  const device = Number.isFinite(deviceDpr) && deviceDpr > 0 ? deviceDpr : 1;
  const area = Math.max(1, width) * Math.max(1, height);
  return Math.max(DPR_FLOOR, Math.min(device, cap, Math.sqrt(budget / area)));
}
