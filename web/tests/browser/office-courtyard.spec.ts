// Actual scene acceptance using only the explicitly synthetic demo roster.
import fs from "node:fs";
import { expect, test, type Page, type TestInfo } from "@playwright/test";

test.use({ reducedMotion: "reduce" });

const viewportShot = async (page: Page, testInfo: TestInfo, name: string): Promise<void> => {
  fs.writeFileSync(testInfo.outputPath(name), await page.locator(".office-viewport").screenshot());
};

test("courtyard: 18 employees, stable filtered seat, selection, demo isolation, responsive", async ({ page }, testInfo) => {
  const errors: string[] = [];
  const privateRequests: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("request", (req) => {
    if (req.url().includes("/api/office/")) privateRequests.push(req.url());
  });

  await page.goto("/office?mode=demo&scenario=team");
  await page.locator(".office-host-label").waitFor();
  expect(await page.locator(".office-worker-chip").count()).toBe(18);
  await page.getByRole("button", { name: "Name labels", exact: true }).click();
  await viewportShot(page, testInfo, "01-courtyard-overview.png");
  await page.getByRole("button", { name: "Name labels", exact: true }).click();
  await page.locator(".office-worker-chip").filter({ hasText: "Coach Planner" }).click();
  await page.getByRole("button", { name: "Focus selected worker", exact: true }).click();
  await viewportShot(page, testInfo, "03-coach-studio.png");
  await page.getByRole("button", { name: "Reset camera view", exact: true }).click();
  await page.locator(".office-worker-chip").filter({ hasText: "Wealth Manager" }).click();
  await page.locator(".office-worker-profile h2").filter({ hasText: "Wealth Manager" }).waitFor();

  const anchor = (): Promise<[number, number]> =>
    page
      .locator(".office-floating-label")
      .filter({ hasText: "Wealth Manager" })
      .evaluate((el): [number, number] => {
        const labels = [...document.querySelectorAll(".office-floating-label:not(.office-host-label)")];
        const line = document.querySelectorAll(".office-label-leaders line")[labels.indexOf(el)];
        return [Number(line.getAttribute("x2")), Number(line.getAttribute("y2"))];
      });

  await viewportShot(page, testInfo, "00-before-filter.png");
  const before = await anchor();
  await page.locator("#office-filter").click();
  await page.getByRole("option", { name: "Standby", exact: true }).click();
  await page.waitForTimeout(300); // let the filtered layout settle before measuring the anchor
  await viewportShot(page, testInfo, "00-after-filter.png");
  const after = await anchor();
  expect(Math.hypot(before[0] - after[0], before[1] - after[1]), "filtering keeps the employee in the same physical seat").toBeLessThan(1);
  await page.locator("#office-filter").click();
  await page.getByRole("option", { name: "All states", exact: true }).click();

  for (const width of [1440, 390, 320]) {
    await page.setViewportSize({ width, height: 1000 });
    await viewportShot(page, testInfo, `02-selected-${width}.png`);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBeTruthy();
  }
  expect(errors).toEqual([]);
  expect(privateRequests).toEqual([]);
});
