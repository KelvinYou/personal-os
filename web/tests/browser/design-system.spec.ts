import fs from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";

test("component catalog interactions stay local and preserve state semantics", async ({ page }) => {
  const writes: string[] = [];
  const errors: string[] = [];
  page.on("request", request => { if (!["GET", "HEAD"].includes(request.method()) && request.url().includes("/api/")) writes.push(request.url()); });
  page.on("pageerror", error => errors.push(error.message));
  await page.goto("/design-system");
  await expect(page.getByRole("heading", { name: "Design system & components" })).toBeVisible();
  await page.getByRole("button", { name: "Refresh sample", exact: true }).click();
  await expect(page.getByText("Sample refreshed.", { exact: true })).toBeVisible();
  await page.getByLabel("Workspace name", { exact: true }).fill("Example workspace");
  await page.getByLabel("Notes", { exact: true }).fill("Sample note");
  await page.getByRole("button", { name: "Save sample", exact: true }).click();
  await expect(page.getByText("Saved locally: Example workspace.", { exact: true })).toBeVisible();
  const privacy = page.locator("#privacy");
  await expect(privacy).not.toContainText("12,345.67");
  await privacy.getByRole("button", { name: "Show amounts" }).click();
  await expect(privacy).toContainText("12,345.67");
  await privacy.getByRole("button", { name: "Hide amounts" }).click();
  await expect(privacy).not.toContainText("12,345.67");
  await page.getByRole("button", { name: "Empty", exact: true }).click();
  await expect(page.locator("#charts svg[role=img]")).toHaveCount(1);
  await page.getByRole("button", { name: "Single point", exact: true }).click();
  await expect(page.locator("#charts")).toContainText("2026-08-31");
  await page.getByRole("button", { name: "Complete", exact: true }).click();
  // Complete asset history now has a trend and a separate monthly-change chart.
  await expect(page.locator("#charts svg[role=img]")).toHaveCount(4);
  await page.getByRole("button", { name: "Week 3", exact: true }).focus();
  await page.keyboard.press("Enter");
  await expect(page.getByText("Week 3: Completed 10 · Planned 14", { exact: true })).toBeVisible();
  await page.getByLabel("Data state", { exact: true }).click();
  await page.getByRole("option", { name: "Error — retry available" }).click();
  await expect(page.locator("#states")).toContainText("Balance unavailable");
  await page.getByRole("button", { name: "Retry sample" }).click();
  await expect(page.locator("#states")).toContainText("Confirmed balance: MYR 0.00");
  const select = page.getByLabel("Sample account", { exact: true });
  await select.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("option", { name: "All sample accounts", exact: true })).toBeFocused();
  await page.keyboard.press("ArrowDown");
  await expect(page.getByRole("option", { name: "900719925474099312345678901234567890", exact: true })).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("output")).toHaveText("900719925474099312345678901234567890");
  await select.click();
  await page.keyboard.press("Escape");
  await expect(select).toBeFocused();
  // New component modules must stay discoverable through the catalog.
  function modules(dir: string): string[] {
    return fs.readdirSync(dir, { withFileTypes: true }).flatMap(entry => entry.isDirectory() ? modules(path.join(dir, entry.name)) : /\.(tsx?|mjs)$/.test(entry.name) ? [path.relative(path.resolve("components"), path.join(dir, entry.name))] : []);
  }
  for (const file of modules(path.resolve("components"))) await expect(page.locator("#directory")).toContainText(`components/${file}`);
  expect(writes).toEqual([]);
  expect(errors).toEqual([]);
});

test("shared controls compose consistently and the directory works by keyboard", async ({ page }) => {
  await page.goto("/design-system");
  const composition = page.locator("#composition");
  await composition.getByLabel("Project name").fill("Design preview");
  await composition.getByLabel("Visibility").click();
  await page.getByRole("option", { name: "Shared workspace", exact: true }).click();
  await composition.getByRole("button", { name: "Save changes" }).click();
  await expect(composition.getByRole("status")).toHaveText("Preview saved: Design preview · shared.");
  const controls = composition.locator('.ui-field, .design-select-trigger, .ui-button');
  const sizes = await controls.evaluateAll(elements => elements.map(element => {
    const style = getComputedStyle(element);
    return { height: element.getBoundingClientRect().height, radius: style.borderRadius, shadow: style.boxShadow };
  }));
  expect(new Set(sizes.map(size => size.height)).size).toBe(1);
  expect(new Set(sizes.map(size => size.radius)).size).toBe(1);
  expect(sizes.every(size => size.shadow === "none")).toBe(true);
  const input = composition.getByLabel("Project name");
  await input.focus();
  await expect(input).toBeFocused();
  expect(await input.evaluate(element => getComputedStyle(element).outlineStyle)).not.toBe("none");
  const sidebar = page.getByLabel("Design system directory");
  await sidebar.getByRole("link", { name: "Button", exact: true }).focus();
  await page.keyboard.press("Enter");
  await expect(sidebar.getByRole("link", { name: "Button", exact: true })).toHaveAttribute("aria-current", "location");
  await page.setViewportSize({ width: 390, height: 900 });
  await page.evaluate(() => scrollTo(0, 0));
  await page.getByText("Browse components", { exact: true }).click();
  await expect(page.locator(".design-mobile-directory nav")).toBeVisible();
  for (const control of await controls.all()) expect(await control.evaluate(element => element.getBoundingClientRect().height)).toBeGreaterThanOrEqual(44);
  await page.getByRole("button", { name: "Appearance", exact: true }).click();
  const theme = page.getByRole("menuitemcheckbox", { name: /Dark appearance/ });
  await theme.click();
  await expect(theme).toBeVisible();
  await page.getByRole("menuitemcheckbox", { name: /Reduce transparency/ }).click();
  await expect(theme).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("button", { name: "Appearance", exact: true })).toBeFocused();
});

for (const width of [320, 390, 1440]) {
  for (const dark of [false, true]) {
    test(`catalog reflows at ${width}px in ${dark ? "dark" : "light"}`, async ({ page }, testInfo) => {
      await page.setViewportSize({ width, height: 1000 });
      await page.addInitScript(({ dark }) => { localStorage.setItem("os-theme", dark ? "dark" : "light"); localStorage.setItem("os-material", "solid"); }, { dark });
      await page.goto("/design-system");
      await expect(page.locator("#directory")).toBeAttached();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
      await page.screenshot({ path: testInfo.outputPath("catalog-top.png") });
      await page.locator("#composition").scrollIntoViewIfNeeded();
      await page.screenshot({ path: testInfo.outputPath("catalog-composition.png") });
      await page.locator("#fields").scrollIntoViewIfNeeded();
      await page.screenshot({ path: testInfo.outputPath("catalog-fields.png") });
      await page.locator("#charts").scrollIntoViewIfNeeded();
      await page.screenshot({ path: testInfo.outputPath("catalog-charts.png") });
      await page.locator("#directory").scrollIntoViewIfNeeded();
      await page.screenshot({ path: testInfo.outputPath("catalog-directory.png") });
      // Enlarged text must not force page-level horizontal scrolling.
      await page.evaluate(() => { document.documentElement.style.fontSize = "32px"; });
      const overflow = await page.evaluate(() => Array.from(document.querySelectorAll("main *")).filter(element => element.getBoundingClientRect().right > innerWidth + 1 && !element.closest('[role="region"]')).map(element => ({ tag: element.tagName, text: element.textContent?.slice(0, 60), width: element.getBoundingClientRect().width, right: element.getBoundingClientRect().right })).slice(0, 30));
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), JSON.stringify(overflow)).toBe(true);
    });
  }
}
