// Real WebGL scene with synthetic demo workers; no private endpoints/model calls.
import fs from "node:fs";
import { expect, test, type Page, type TestInfo } from "@playwright/test";

test.use({ reducedMotion: "reduce" });

const viewportShot = async (page: Page, testInfo: TestInfo, name: string): Promise<Buffer> => {
  const buf = await page.locator(".office-viewport").screenshot();
  fs.writeFileSync(testInfo.outputPath(name), buf);
  return buf;
};

test("player: first/third person, walking, focus guard and touch joystick", async ({ page }, testInfo) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));

  await page.goto("/office?scene=town&mode=demo&scenario=team");
  await page.locator("canvas").waitFor();
  await page.locator(".office-host-label").waitFor();
  await viewportShot(page, testInfo, "00-overview-baseline.png");

  const first = page.getByRole("button", { name: "First person", exact: true });
  await first.click();
  await expect(first).toHaveAttribute("aria-pressed", "true");
  const firstPerson = await viewportShot(page, testInfo, "01-first-person.png");

  const controller = page.getByRole("region", { name: "Control kelvin.ai" });
  await controller.focus();
  // Fixed wait: measures real elapsed avatar movement while the key is held.
  await page.keyboard.down("w");
  await page.waitForTimeout(550);
  await page.keyboard.up("w");
  const firstWalk = await viewportShot(page, testInfo, "02-first-walk.png");
  expect(firstPerson.equals(firstWalk), "walking changes the actual camera view").toBe(false);

  await page.keyboard.press("v");
  await page.waitForFunction(() => document.querySelector('[aria-label="Third person"]')?.getAttribute("aria-pressed") === "true");
  await viewportShot(page, testInfo, "03-third-person.png");

  // Fixed wait: real elapsed movement while the key is held.
  await page.keyboard.down("s");
  await page.waitForTimeout(400);
  await page.keyboard.up("s");
  await page.keyboard.press("Escape");
  await expect(page.getByRole("button", { name: "Overview", exact: true })).toHaveAttribute("aria-pressed", "true");
  await page.locator(".office-host-label").waitFor();
  await viewportShot(page, testInfo, "04-overview-after-walk.png");

  const third = page.getByRole("button", { name: "Third person", exact: true });
  await third.click();
  await controller.focus();
  await page.keyboard.down("w");
  await third.focus();
  await page.keyboard.up("w");
  // Fixed wait: let any residual avatar motion settle before the baseline frame.
  await page.waitForTimeout(250);
  const stopped = await page.locator("canvas").screenshot();
  // Fixed wait: real elapsed time during which the avatar must NOT move.
  await page.keyboard.down("w");
  await page.waitForTimeout(250);
  await page.keyboard.up("w");
  const afterBlur = await page.locator("canvas").screenshot();
  expect(afterBlur.equals(stopped), "focus on a UI button cannot keep driving the avatar").toBe(true);
  await page.getByRole("button", { name: "Reset player position", exact: true }).click();

  for (const width of [390, 320]) {
    await page.setViewportSize({ width, height: 1000 });
    const stick = page.locator("[data-office-joystick]");
    const box = await stick.boundingBox();
    expect(box).toBeTruthy();
    const cx = box!.x + box!.width / 2;
    const cy = box!.y + box!.height / 2;
    await stick.dispatchEvent("pointerdown", { pointerId: 1, pointerType: "touch", isPrimary: true, clientX: cx, clientY: cy - 40 });
    // Fixed wait: real elapsed joystick hold.
    await page.waitForTimeout(300);
    await stick.dispatchEvent("pointerup", { pointerId: 1, pointerType: "touch", isPrimary: true, clientX: cx, clientY: cy - 40 });
    await viewportShot(page, testInfo, `05-third-${width}.png`);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBeTruthy();
  }
  expect(errors).toEqual([]);
});
