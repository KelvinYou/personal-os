// Home design viewer: doors, seats, god-view figure, third person, closed-door collision, keyboard exit, small-screen reflow.
import { expect, test, type Locator } from "@playwright/test";

test.use({ viewport: { width: 1440, height: 1050 } });

interface Vec3 { x: number; y: number; z: number }
interface WalkPosition extends Vec3 { yaw: number }
type Doors = Record<string, string>;

const dist = (a: Vec3, b: Vec3) => Math.hypot(a.x - b.x, a.z - b.z);

test("home viewer interactions", async ({ page }, testInfo) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));

  await page.goto("/home-design/viewer");
  await expect(page.locator('[data-ready="true"]').first()).toBeVisible({ timeout: 90_000 });

  const root: Locator = page.locator("#wyn-home-preview");
  // Reads a JSON `data-*` attribute of the preview root (camelCase name -> kebab-case attribute).
  const state = async <T>(name: string): Promise<T> => {
    const raw = await root.getAttribute("data-" + name.replace(/[A-Z]/g, (c) => "-" + c.toLowerCase()));
    if (raw === null) throw new Error(`data attribute ${name} missing`);
    return JSON.parse(raw) as T;
  };
  const doors = () => state<Doors>("doors");
  const walkPosition = () => state<WalkPosition>("walkPosition");
  const figure = () => state<Vec3>("figure");
  // Hold a key for a fixed real duration: these steps measure actual elapsed movement/animation.
  const hold = async (key: string, ms: number) => {
    await page.keyboard.down(key);
    try { await page.waitForTimeout(ms); } finally { await page.keyboard.up(key); }
  };
  const door = page.locator("[data-door]");
  const doorToggle = page.locator("[data-door-toggle]");
  const seat = page.locator("[data-seat]");
  const sit = page.locator("[data-sit]");
  const orbit = page.locator("[data-orbit]");
  const walk = page.locator("[data-walk]");

  await page.screenshot({ path: testInfo.outputPath("after-dollhouse.png") });

  await test.step("doors ease open and closed", async () => {
    // Logical state flips immediately and the leaf settles within a second.
    await door.selectOption("bedroom");
    await doorToggle.click();
    await expect(root).toHaveAttribute("data-door-moving", "true");
    expect((await doors()).bedroom).toBe("closed");
    await expect(root).toHaveAttribute("data-door-moving", "false", { timeout: 3000 });
    await doorToggle.click();
    await expect(root).toHaveAttribute("data-door-moving", "false", { timeout: 3000 });
    expect((await doors()).bedroom).toBe("open");
  });

  await test.step("door state is preserved across modes", async () => {
    for (const id of ["bedroom", "bathroom", "office", "entry"]) {
      await door.selectOption(id);
      await doorToggle.click();
      expect((await doors())[id]).toBe("closed");
      await walk.click();
      expect((await doors())[id]).toBe("closed");
      await expect(root).toHaveAttribute("data-mode", "walk");
      await orbit.click();
      expect((await doors())[id]).toBe("closed");
      await doorToggle.click();
      expect((await doors())[id]).toBe("open");
    }
  });

  await test.step("five seats: posture, height, blocked seated movement, safe standing", async () => {
    for (const id of ["sofa", "dining-north", "dining-south", "office", "bed"]) {
      await seat.selectOption(id);
      await sit.click();
      await expect(root).toHaveAttribute("data-posture", id);
      const before = await walkPosition();
      expect(before.y).toBeLessThan(1.6);
      await hold("w", 300); // seated: the position must not change after a real 300 ms of held key
      expect(await walkPosition()).toEqual(before);
      await page.screenshot({ path: testInfo.outputPath(`seat-${id}.png`) });
      await page.keyboard.press("f");
      await expect(root).toHaveAttribute("data-posture", "standing");
      expect((await walkPosition()).y).toBe(1.6);
      await orbit.click();
    }
  });

  await test.step("god view: WASD walks the figure, Enter & walk continues from there", async () => {
    await walk.click();
    await page.keyboard.press("r");
    await orbit.click();
    await page.locator(".wyn-stage canvas").click({ position: { x: 40, y: 40 } });
    const fig0 = await figure();
    await page.keyboard.down("w");
    try {
      await expect
        .poll(async () => dist(await figure(), fig0), { timeout: 8000, message: "figure walks from the dollhouse view" })
        .toBeGreaterThan(0.4);
    } finally { await page.keyboard.up("w"); }
    const fig1 = await figure();
    await walk.click();
    const entered = await walkPosition();
    expect(dist(entered, fig1), "walk mode starts where the figure stands").toBeLessThan(0.6);
    await orbit.click();
  });

  await test.step("third person: avatar, boom, chase camera, V toggle, sitting returns to first person", async () => {
    await orbit.click();
    await page.locator("[data-third]").click();
    await expect(root).toHaveAttribute("data-mode", "walk");
    await expect(root).toHaveAttribute("data-person", "third");
    await hold("w", 500); // real movement so the boom collision arm settles
    await page.screenshot({ path: testInfo.outputPath("third-person.png") });
    expect(Number(await root.getAttribute("data-boom"))).toBeGreaterThan(0.2);

    // Chase camera: holding A in third person swings the view; the same key in first person only strafes.
    await page.waitForTimeout(1200); // let the chase camera settle before measuring yaw
    const yaw0 = (await walkPosition()).yaw;
    // Hold A until the camera has swung: software-rendered frames are slow on a cold server, so wait for the state, not a duration.
    await page.keyboard.down("a");
    await page.waitForFunction((from) => Math.abs(JSON.parse(document.querySelector("#wyn-home-preview")!.getAttribute("data-walk-position")!).yaw - from) > 0.25, yaw0, { timeout: 15_000 });
    await page.keyboard.up("a");
    await page.keyboard.press("v");
    await expect(root).toHaveAttribute("data-person", "first");
    await page.keyboard.press("v");
    await expect(root).toHaveAttribute("data-person", "third");
    await seat.selectOption("sofa");
    await sit.click();
    await expect(root).toHaveAttribute("data-person", "first");
    await page.locator("[data-stand]").click();
    await expect(root).toHaveAttribute("data-person", "third");
    await orbit.click();
    await walk.click();
    await expect(root).toHaveAttribute("data-person", "first");
    await orbit.click();
  });

  await test.step("a closed office door stops the viewer, an open one lets them through", async () => {
    await door.selectOption("office");
    await doorToggle.click();
    await walk.click();
    await page.locator('[data-view="office"]').click();
    const box = await page.locator("canvas").first().boundingBox();
    if (!box) throw new Error("canvas has no bounding box");
    await page.mouse.move(box.x + box.width * 0.25, box.y + box.height * 0.5);
    await page.mouse.down();
    await page.mouse.move(box.x + box.width * 0.25 + Math.PI / 0.004, box.y + box.height * 0.5, { steps: 10 });
    await page.mouse.up();
    await hold("w", 1100); // measures real distance walked into the closed door
    const blocked = await walkPosition();
    expect(blocked.x, JSON.stringify(blocked)).toBeGreaterThan(3.17);
    expect(blocked.x, JSON.stringify(blocked)).toBeLessThan(3.5);

    await doorToggle.click();
    expect((await doors()).office).toBe("closed");
    await expect(page.locator("[data-status]")).toHaveText(/Step away/);
    await page.keyboard.down("s");
    try {
      // requestAnimationFrame-rate polling so the key is released right after crossing x>4.2 (slower polling overshoots into furniture)
      await page.waitForFunction(() => JSON.parse(document.querySelector<HTMLElement>("#wyn-home-preview")?.dataset.walkPosition ?? "null")?.x > 4.2, undefined, { timeout: 15_000 });
    } finally { await page.keyboard.up("s"); }
    await doorToggle.click();
    expect((await doors()).office).toBe("open");
    await page.keyboard.down("w");
    try {
      await page.waitForFunction(() => JSON.parse(document.querySelector<HTMLElement>("#wyn-home-preview")?.dataset.walkPosition ?? "null")?.x < 2.9, undefined, { timeout: 15_000 });
    } finally { await page.keyboard.up("w"); }
    const crossed = await walkPosition();
    expect(crossed.x, JSON.stringify(crossed)).toBeLessThan(2.9);
  });

  await test.step("room reset and keyboard exit", async () => {
    await orbit.click();
    await seat.selectOption("sofa");
    await sit.click();
    await page.locator('[data-view="office"]').click();
    await expect(root).toHaveAttribute("data-posture", "standing");
    await seat.selectOption("office");
    await sit.click();
    await page.keyboard.press("Escape");
    await expect(root).toHaveAttribute("data-mode", "orbit");
    await expect(root).toHaveAttribute("data-posture", "standing");
  });

  for (const width of [320, 390]) {
    await test.step(`reflow at ${width}px`, async () => {
      await page.setViewportSize({ width, height: 900 });
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      await seat.selectOption("sofa");
      await sit.click();
      await page.screenshot({ path: testInfo.outputPath(`mobile-${width}.png`) });
      await page.locator("[data-stand]").click();
      await orbit.click();
    });
  }

  expect(errors).toEqual([]);
});
