// Office pixel budget (web/lib/office-render.ts): fullscreen must not multiply drawing-buffer pixels.
import assert from "node:assert/strict";
import { test } from "vitest";
import { budgetDpr, OFFICE_DPR_CAP, OFFICE_PIXEL_BUDGET } from "@/lib/office-render";

test("windowed canvases keep the existing DPR cap; fullscreen is held to the pixel budget", () => {
  assert.equal(budgetDpr(2, 1080, 620), OFFICE_DPR_CAP); // windowed retina: unchanged 1.75
  assert.equal(budgetDpr(1, 1080, 620), 1); // never upsamples past the device
  const retina = budgetDpr(2, 1728, 1117); // MacBook fullscreen
  assert.ok(retina < OFFICE_DPR_CAP && retina > 1);
  assert.ok(1728 * retina * 1117 * retina <= OFFICE_PIXEL_BUDGET + 1);
  assert.equal(budgetDpr(1, 1920, 1080), 1); // 1x full HD fits the budget at native resolution
  assert.ok(budgetDpr(1, 3840, 2160) < 1); // a 4K display at 1x drops below 1 only because the budget requires it
  assert.equal(budgetDpr(1, 100000, 100000), .5); // floor
  assert.equal(budgetDpr(Number.NaN, 800, 600), 1); // unknown device ratio treated as 1
});
