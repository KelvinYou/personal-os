// Perspective overview, eased view travel, FOV slider and F interaction. Synthetic demo roster only.
import fs from "node:fs";
import { expect, test, type Page, type TestInfo } from "@playwright/test";

const shot = async (page: Page, testInfo: TestInfo, name: string): Promise<Buffer> => {
  const buf = await page.locator(".office-viewport").screenshot();
  fs.writeFileSync(testInfo.outputPath(`${name}.png`), buf);
  return buf;
};

test("camera: perspective overview, eased travel, FOV and F interaction", async ({ page }, testInfo) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));

  await page.goto("/office?scene=town&mode=demo&scenario=team");
  await page.locator("canvas").waitFor();
  await page.locator(".office-host-label").waitFor();
  const overview = await shot(page, testInfo, "00-overview-perspective");

  // God view: W A S D walk kelvin.ai without leaving the overview.
  await page.locator("canvas").click({ position: { x: 60, y: 300 } });
  const label = () => page.locator(".office-host-label").boundingBox();
  const before = await label();
  // Fixed wait: measures real elapsed movement while the key is held.
  await page.keyboard.down("w");
  await page.waitForTimeout(800);
  await page.keyboard.up("w");
  await page.waitForTimeout(150);
  const after = await label();
  expect(before).toBeTruthy();
  expect(after).toBeTruthy();
  expect(Math.hypot(after!.x - before!.x, after!.y - before!.y), "host moved in the overview " + JSON.stringify([before, after])).toBeGreaterThan(8);
  await shot(page, testInfo, "00b-overview-walked");

  await page.getByRole("button", { name: "Third person", exact: true }).click();
  // Fixed waits: sample the eased camera travel at real elapsed times (early frame vs settled).
  await page.waitForTimeout(120);
  const early = await shot(page, testInfo, "01-travel-early");
  await page.waitForTimeout(900);
  const settled = await shot(page, testInfo, "02-third-settled");
  // The travel is eased, not a cut: the early frame matches neither endpoint.
  expect(early.equals(settled)).toBe(false);
  expect(early.equals(overview)).toBe(false);

  const fov = page.getByRole("slider", { name: "Field of view" });
  expect(await fov.inputValue()).toBe("60");
  await fov.fill("78");
  await page.waitForTimeout(200); // let the new FOV render a frame
  const wide = await shot(page, testInfo, "03-wide-fov");
  expect(wide.equals(settled), "FOV changes the picture").toBe(false);

  await page.getByRole("region", { name: "Control kelvin.ai" }).focus();
  // Fixed waits below: real elapsed movement while keys are held.
  for (let i = 0; i < 3; i++) {
    await page.keyboard.down("w");
    await page.waitForTimeout(500);
    await page.keyboard.up("w");
    await page.keyboard.down("Shift");
    await page.keyboard.down("a");
    await page.waitForTimeout(200);
    await page.keyboard.up("a");
    await page.keyboard.up("Shift");
  }
  await page.keyboard.press("f");
  await page.waitForTimeout(300); // let the F interaction play
  await page.keyboard.press("Escape");
  await page.locator(".office-host-label").waitFor();
  await shot(page, testInfo, "04-back-to-overview");
  expect(errors).toEqual([]);
});
