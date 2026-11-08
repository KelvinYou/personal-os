// Shared-model appearance preview; no runtime, observation, model or external requests.
import fs from "node:fs";
import { expect, test, type Page, type TestInfo } from "@playwright/test";

test.use({ reducedMotion: "reduce" });

const stageShot = async (page: Page, testInfo: TestInfo, name: string): Promise<void> => {
  fs.writeFileSync(testInfo.outputPath(name), await page.locator(".office-character-stage").screenshot());
};

test("characters: cast preview, angles, poses, responsive and keyboard", async ({ page }, testInfo) => {
  const errors: string[] = [];
  const runtime: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("request", (r) => {
    if (r.url().includes("/api/office/")) runtime.push(r.url());
  });

  await page.goto("/office/characters");
  await page.locator("canvas").waitFor();
  expect(await page.locator(".office-character-captions h2").count()).toBe(6);
  fs.writeFileSync(testInfo.outputPath("01-cast-page.png"), await page.screenshot({ fullPage: true }));
  await stageShot(page, testInfo, "01-lineup.png");

  const select = async (name: string) => {
    await page.locator("#character-choice").click();
    await page.getByRole("option", { name, exact: true }).click();
  };
  const btn = (name: string) => page.getByRole("button", { name, exact: true });

  await select("Coach Planner");
  await page.locator(".office-character-captions").getByText("Training top · shorts · trainers", { exact: true }).waitFor();
  for (const angle of ["Front", "Side", "Back"]) {
    await btn(angle).click();
    await stageShot(page, testInfo, `02-coach-${angle.toLowerCase()}.png`);
  }
  await btn("Seated").click();
  await btn("Front").click();
  await stageShot(page, testInfo, "03-coach-seated.png");
  await btn("Standing").click();
  await select("Travel Plan");
  await btn("Back").click();
  await stageShot(page, testInfo, "04-travel-backpack.png");
  await select("Wealth Manager");
  await btn("Front").click();
  await stageShot(page, testInfo, "05-wealth.png");
  await select("Coach Planner");

  for (const width of [390, 320]) {
    await page.setViewportSize({ width, height: 1000 });
    fs.writeFileSync(testInfo.outputPath(`06-preview-${width}.png`), await page.screenshot({ fullPage: true }));
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBeTruthy();
  }

  await page.locator("#character-choice").focus();
  await page.keyboard.press("Enter");
  await page.getByRole("listbox").waitFor();
  await page.keyboard.press("Escape");
  await page.getByRole("listbox").waitFor({ state: "hidden" });
  await page.waitForFunction(() => document.getElementById("character-choice") === document.activeElement);
  expect(await page.locator("#character-choice").evaluate((el) => el === document.activeElement)).toBe(true);

  expect(runtime).toEqual([]);
  expect(errors).toEqual([]);
});
