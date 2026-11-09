// Flat town: Lab and Finance buildings on one floor (docs/design/office-world.md).
// Demo only: synthetic sessions and the canonical synthetic wealth fixture; no private reads or writes.
import { expect, test, type Page } from "@playwright/test";
import { GROUND } from "../../lib/office-departments";

test.use({ reducedMotion: "reduce" });
const shell = (page: Page) => page.locator(".radar-canvas-shell");
const ready = (page: Page) => page.locator('.radar-canvas-shell[data-assets-ready="true"]');
const departmentsNav = (page: Page) => page.getByRole("navigation", { name: "Departments" });

test("town: switch Lab ↔ Finance and open desks without leaving the page", async ({ page }, info) => {
  const errors: string[] = [], writes: string[] = [], privateReads: string[] = [];
  page.on("pageerror", e => errors.push(e.message));
  page.on("request", r => {
    if (r.url().includes("/api/") && !["GET", "HEAD"].includes(r.method())) writes.push(r.url());
    if (r.url().includes("/api/office/state")) privateReads.push(r.url());
  });
  await page.goto("/office?mode=demo&scenario=team");
  await expect(ready(page)).toBeVisible();
  // Both buildings are on screen at once: their projected name buttons are visible.
  await expect(page.locator(".town-anchor-department", { hasText: /^Lab$/ })).toBeVisible();
  await expect(page.locator(".town-anchor-department", { hasText: "Finance" })).toBeVisible();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Who needs you right now?");
  await page.locator(".office-viewport").screenshot({ path: info.outputPath("01-whole-town.png") });
  // A page marker proves switching is in-page, not a navigation.
  await page.evaluate(() => { (window as unknown as { __stay: boolean }).__stay = true; });

  await departmentsNav(page).getByRole("button", { name: /^Finance/ }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Finance");
  await expect(shell(page)).toHaveAttribute("data-department", "finance");
  await expect(page).toHaveURL(/dept=finance.*station=analysis|station=analysis.*dept=finance/);
  await expect(page.getByRole("button", { name: "Funding tasks", exact: true })).toBeVisible();
  // The camera never locks onto one building: both buildings stay on screen after switching.
  await expect(page.locator(".town-anchor-department", { hasText: /^Lab$/ })).toBeVisible();
  await expect(page.locator(".town-anchor-department", { hasText: "Finance" })).toBeVisible();
  await expect(page.locator(".town-anchor-department", { hasText: "Finance" })).toHaveAttribute("aria-pressed", "true");
  await page.locator(".office-viewport").screenshot({ path: info.outputPath("02-finance-selected.png") });

  // The projected desk button in the town opens that workstation; amounts stay masked.
  await page.locator(".town-anchor-desk", { hasText: "Assets" }).click();
  await expect(page.getByRole("heading", { name: "Asset overview", exact: true })).toBeVisible();
  await expect(page.locator("#finance-workstation")).toContainText("••••••");
  await expect(page.locator("#finance-workstation")).not.toContainText("RM ");
  await page.getByRole("navigation", { name: "Finance workstations" }).getByRole("button", { name: "Finance notices", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Finance notices", exact: true })).toBeVisible();
  await expect(page).toHaveURL(/station=notices/);

  // Back to the Lab: the radar queue returns and nothing reloaded.
  await departmentsNav(page).getByRole("button", { name: /^Lab/ }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Who needs you right now?");
  await expect(page.locator(".radar-queue ol .radar-queue-row")).toHaveCount(4);
  await expect(page.locator("#finance-workstation")).toHaveCount(0);
  expect(await page.evaluate(() => (window as unknown as { __stay?: boolean }).__stay)).toBe(true);
  await expect(page.getByRole("link", { name: "Walk outside" })).toHaveCount(0);
  expect(errors).toEqual([]); expect(writes).toEqual([]); expect(privateReads).toEqual([]);
});

test("town: old street links, deep links, reload, narrow reflow and dark", async ({ page }, info) => {
  const errors: string[] = []; page.on("pageerror", e => errors.push(e.message));
  await page.goto("/office/world?place=finance&mode=demo");
  await expect(page).toHaveURL(/\/office\?dept=finance&mode=demo/);
  await expect(ready(page)).toBeVisible();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Finance");
  await page.goto("/office?mode=demo&dept=finance&station=assets");
  await expect(page.getByRole("heading", { name: "Asset overview", exact: true })).toBeVisible();
  // A deep link chooses the panel, not the camera: the Lab is still in view.
  await expect(page.locator(".town-anchor-department", { hasText: /^Lab$/ })).toBeVisible();
  await page.reload(); await expect(ready(page)).toBeVisible();
  await expect(page.getByRole("heading", { name: "Asset overview", exact: true })).toBeVisible();
  for (const width of [390, 320]) {
    await page.setViewportSize({ width, height: 1000 });
    await expect(departmentsNav(page).getByRole("button", { name: /^Lab/ })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
    // Departments stay reachable by keyboard and touch-sized buttons.
    const box = (await departmentsNav(page).getByRole("button", { name: /^Finance/ }).boundingBox())!;
    expect(box.height).toBeGreaterThanOrEqual(44);
    await page.screenshot({ path: info.outputPath(`03-narrow-${width}.png`), fullPage: true });
  }
  await page.evaluate(() => document.documentElement.classList.add("dark"));
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.screenshot({ path: info.outputPath("04-dark.png"), fullPage: true });
  expect(errors).toEqual([]);
});

test("town: walk kelvin.ai in third person to a Finance desk, press F, and return to overview", async ({ page }, info) => {
  const errors: string[] = []; page.on("pageerror", e => errors.push(e.message));
  await page.goto("/office?mode=demo&scenario=team");
  await expect(ready(page)).toBeVisible();
  const region = page.getByRole("region", { name: "Control kelvin.ai", exact: true });
  const pose = () => shell(page).evaluate(el => JSON.parse((el as HTMLElement).dataset.player ?? "null") as { x: number; z: number });
  await page.getByRole("button", { name: "Third person", exact: true }).click();
  await expect(region).toHaveAttribute("data-office-view", "third");
  await expect(page.locator(".office-camera-controls")).toBeHidden();
  await page.locator(".office-viewport").screenshot({ path: info.outputPath("05-third-person-plaza.png") });
  const start = await pose();
  await region.focus();
  const hold = async (keys: string[], ms: number) => { for (const k of keys) await page.keyboard.down(k); await page.waitForTimeout(ms); for (const k of [...keys].reverse()) await page.keyboard.up(k); await page.waitForTimeout(200); };
  // Straight ahead is the planter: kelvin.ai walks, then stops at its edge.
  await hold(["w"], 1600);
  const blocked = await pose();
  expect(blocked.z).toBeLessThan(start.z - .5);
  expect(blocked.z).toBeGreaterThan(3.4);
  // Turn east along the plaza, then north into Finance (← → turn the view; ↑ walks).
  await page.keyboard.press("r");
  await expect.poll(async () => (await pose()).z).toBeCloseTo(start.z, 1);
  await hold(["ArrowRight"], 830);
  await expect.poll(async () => { if ((await pose()).x < 28.6) await hold(["Shift", "ArrowUp"], 250); return (await pose()).x; }, { timeout: 30000 }).toBeGreaterThan(28.5);
  await hold(["ArrowLeft"], 830);
  await expect.poll(async () => { if ((await pose()).z > 0) await hold(["ArrowUp"], 250); return (await pose()).z; }, { timeout: 30000 }).toBeLessThan(.2);
  await expect(page.locator(".town-interact")).toHaveText(/^F · Open /);
  await page.locator(".office-viewport").screenshot({ path: info.outputPath("06-third-person-desk.png") });
  await region.focus(); await page.keyboard.press("f");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Finance");
  await expect(page).toHaveURL(/dept=finance/);
  await region.focus(); await page.keyboard.press("Escape");
  await expect(region).toHaveAttribute("data-office-view", "overview");
  await expect(page.locator(".office-camera-controls")).toBeVisible();
  // Touch: the joystick moves kelvin.ai at phone width.
  await page.setViewportSize({ width: 390, height: 1000 });
  await page.getByRole("button", { name: "Third person", exact: true }).click();
  const before = await pose();
  const stick = page.locator("[data-office-joystick]");
  await stick.scrollIntoViewIfNeeded();
  const box = (await stick.boundingBox())!;
  await stick.dispatchEvent("pointerdown", { pointerId: 1, pointerType: "touch", clientX: box.x + box.width / 2, clientY: box.y + 10 });
  await expect.poll(async () => { const p = await pose(); return Math.hypot(p.x - before.x, p.z - before.z); }).toBeGreaterThan(.3);
  await stick.dispatchEvent("pointerup", { pointerId: 1, pointerType: "touch" });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
  expect(errors).toEqual([]);
});

test("town: panning far keeps the overview on the town ground", async ({ page }) => {
  const errors: string[] = []; page.on("pageerror", e => errors.push(e.message));
  await page.goto("/office?mode=demo&scenario=team");
  await expect(ready(page)).toBeVisible();
  const orbit = () => shell(page).evaluate(el => JSON.parse((el as HTMLElement).dataset.orbit ?? "null") as { x: number; z: number } | null);
  // Focusing a person pauses the kelvin.ai follow, which otherwise pulls every pan back.
  await page.locator(".radar-queue-row").first().click();
  await page.getByRole("button", { name: "Focus selected person", exact: true }).click();
  // Measure after selection: the details panel shifts the layout.
  await shell(page).locator("canvas").scrollIntoViewIfNeeded();
  const box = (await shell(page).locator("canvas").boundingBox())!;
  const cx = box.x + box.width / 2, cy = box.y + box.height / 2;
  const start = (await orbit())!;
  let travelled = 0;
  // Right-drag pans; repeat in each direction well past the town edge.
  for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
    for (let i = 0; i < 8; i++) {
      await page.mouse.move(cx, cy); await page.mouse.down({ button: "right" });
      await page.mouse.move(cx + dx * box.width * .45, cy + dy * box.height * .45, { steps: 6 }); await page.mouse.up({ button: "right" });
    }
    const at = await orbit();
    expect(at).not.toBeNull();
    travelled = Math.max(travelled, Math.hypot(at!.x - start.x, at!.z - start.z));
    const halfW = GROUND.width / 2, halfD = GROUND.depth / 2;
    expect(at!.x).toBeGreaterThanOrEqual(GROUND.x - halfW - .01); expect(at!.x).toBeLessThanOrEqual(GROUND.x + halfW + .01);
    expect(at!.z).toBeGreaterThanOrEqual(GROUND.z - halfD - .01); expect(at!.z).toBeLessThanOrEqual(GROUND.z + halfD + .01);
  }
  // The drags really panned: guards against a test that never reaches OrbitControls.
  expect(travelled).toBeGreaterThan(10);
  expect(errors).toEqual([]);
});
