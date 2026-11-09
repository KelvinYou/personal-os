// Fullscreen world shell (docs/design/office-immersive-world.md). Demo only: synthetic sessions and the
// canonical synthetic wealth fixture; no private reads or writes.
import { expect, test, type Page } from "@playwright/test";

test.use({ reducedMotion: "reduce" });
const world = (page: Page) => page.locator(".office-world");
const shell = (page: Page) => page.locator(".radar-canvas-shell");
const panel = (page: Page) => page.locator("#office-world-panel");
const orbit = (page: Page) => shell(page).evaluate(el => JSON.parse((el as HTMLElement).dataset.orbit ?? "null") as { x: number; z: number } | null);
const open = async (page: Page) => {
  await page.goto("/office?mode=demo&scenario=team");
  await expect(page.locator('.radar-canvas-shell[data-assets-ready="true"]')).toBeVisible();
};

test("immersive: native fullscreen fills the screen and keeps camera, selection and panel content mounted", async ({ page }, info) => {
  const errors: string[] = []; page.on("pageerror", e => errors.push(e.message));
  await open(page);
  // Select a person and focus them: the camera is now user-positioned.
  await page.locator(".radar-queue-row").first().click();
  await expect(page.getByLabel("Session details")).toBeVisible();
  await page.getByRole("button", { name: "Focus selected person", exact: true }).click();
  await expect.poll(() => orbit(page)).not.toBeNull();
  const before = (await orbit(page))!;
  // Mark the timeline node: if it is the same node afterwards, nothing remounted.
  await page.locator(".radar-timeline").evaluate(el => { (el as HTMLElement & { __probe?: number }).__probe = 1; });

  await page.getByRole("button", { name: "Fullscreen", exact: true }).click();
  await expect(world(page)).toHaveAttribute("data-world-screen", "native");
  expect(await page.evaluate(() => document.fullscreenElement?.classList.contains("office-world"))).toBe(true);
  const viewport = page.viewportSize()!;
  await expect.poll(async () => (await shell(page).locator("canvas").boundingBox())!.width).toBeGreaterThan(viewport.width - 2);
  await expect(page.getByLabel("Session details")).toBeVisible();
  // The timeline moved into the in-world panel without remounting.
  await expect(panel(page).locator(".radar-timeline")).toBeVisible();
  expect(await page.locator(".radar-timeline").evaluate(el => (el as HTMLElement & { __probe?: number }).__probe)).toBe(1);
  // Resize to fullscreen did not reframe the user's camera.
  await page.waitForTimeout(400);
  const after = (await orbit(page))!;
  expect(Math.hypot(after.x - before.x, after.z - before.z)).toBeLessThan(.01);
  // Drawing buffer stays inside the pixel budget (web/lib/office-render.ts).
  const pixels = await shell(page).locator("canvas").evaluate(el => (el as HTMLCanvasElement).width * (el as HTMLCanvasElement).height);
  expect(pixels).toBeLessThanOrEqual(3_000_000 * 1.02);
  await page.screenshot({ path: info.outputPath("01-fullscreen-lab.png") });

  // Escape closes the panel's detail first (the walking view is not active).
  await page.keyboard.press("Escape");
  await expect(page.getByLabel("Attention queue")).toBeVisible();

  // Finance data is read inside the world: the selected workstation renders in the panel.
  await page.getByRole("navigation", { name: "World departments" }).getByRole("button", { name: /Finance/ }).click();
  await expect(panel(page)).toHaveAttribute("aria-label", "Finance workstations");
  // The panel's workstation nav is the accessible in-world path; projected desk buttons depend on framing.
  await panel(page).getByRole("navigation", { name: "Finance workstations" }).getByRole("button", { name: "Finance notices", exact: true }).click();
  await expect(panel(page).locator("#finance-workstation")).toContainText("Finance notices");
  await page.screenshot({ path: info.outputPath("02-fullscreen-finance.png") });

  // The panel can be hidden to see the whole world.
  await page.getByRole("button", { name: "Hide panel", exact: true }).click();
  await expect(panel(page)).toBeHidden();
  await page.getByRole("button", { name: "Show panel", exact: true }).click();
  await expect(panel(page)).toBeVisible();

  await page.getByRole("button", { name: "Exit fullscreen", exact: true }).click();
  await expect(world(page)).toHaveAttribute("data-world-screen", "windowed");
  expect(await page.evaluate(() => document.fullscreenElement)).toBeNull();
  // Back on the page: Finance detail is below the town again and the page scrolls normally.
  await expect(page.locator(".world-page-slot #finance-workstation")).toBeVisible();
  expect(errors).toEqual([]);
});

test("immersive: a declined fullscreen request falls back to a labelled expanded view", async ({ page }, info) => {
  const errors: string[] = []; page.on("pageerror", e => errors.push(e.message));
  await page.addInitScript(() => { Element.prototype.requestFullscreen = () => Promise.reject(new TypeError("Permissions check failed")); });
  await open(page);
  await page.getByRole("button", { name: "Fullscreen", exact: true }).click();
  await expect(world(page)).toHaveAttribute("data-world-screen", "expanded");
  await expect(page.getByRole("status").filter({ hasText: "declined fullscreen" })).toBeVisible();
  expect(await page.evaluate(() => document.body.style.overflow)).toBe("hidden");
  const box = (await world(page).boundingBox())!, viewport = page.viewportSize()!;
  expect(box.width).toBeGreaterThan(viewport.width - 2); expect(box.height).toBeGreaterThan(viewport.height - 2);
  await page.screenshot({ path: info.outputPath("03-expanded.png") });
  // Escape leaves expanded mode when nothing is selected, and page scroll comes back.
  await page.keyboard.press("Escape");
  await expect(world(page)).toHaveAttribute("data-world-screen", "windowed");
  expect(await page.evaluate(() => document.body.style.overflow)).toBe("");
  expect(errors).toEqual([]);
});

test("immersive: narrow screens get a bottom sheet and 44 px controls", async ({ page }, info) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.addInitScript(() => { Object.defineProperty(Document.prototype, "fullscreenEnabled", { get: () => false }); });
  await open(page);
  await page.getByRole("button", { name: "Fullscreen", exact: true }).click();
  await expect(world(page)).toHaveAttribute("data-world-screen", "expanded");
  // The sheet starts closed so the framed town is visible; Show panel opens it.
  await expect(panel(page)).toBeHidden();
  await page.screenshot({ path: info.outputPath("04-narrow-world.png") });
  await page.getByRole("button", { name: "Show panel", exact: true }).click();
  const sheet = (await panel(page).boundingBox())!;
  expect(sheet.y + sheet.height).toBeGreaterThan(844 - 2);
  expect(sheet.width).toBeGreaterThan(388);
  const exit = (await page.getByRole("button", { name: "Exit fullscreen", exact: true }).boundingBox())!;
  expect(exit.height).toBeGreaterThanOrEqual(44);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
  await page.screenshot({ path: info.outputPath("05-narrow-sheet.png") });
});
