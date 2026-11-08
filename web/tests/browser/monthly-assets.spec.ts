import { expect, test } from "@playwright/test";

test("monthly asset changes show amounts and percentages without exposing hidden balances", async ({ page }) => {
  await page.goto("/design-system");
  const section = page.locator("#asset-history-preview");
  const table = section.getByRole("region", { name: "Monthly asset changes", exact: true }).getByRole("table");
  await expect(section.getByRole("button", { name: "Monthly", exact: true })).toHaveAttribute("aria-pressed", "true");
  const allocation = section.getByTestId("allocation-preview");
  await expect(allocation.getByRole("img", { name: /Asset allocation donut/ })).toBeVisible();
  await allocation.getByRole("button", { name: "Stocks & ETFs", exact: true }).click();
  await expect(allocation).toContainText("priced stocks and ETFs only");
  await expect(allocation.getByRole("img", { name: /Investment allocation by market value/ })).toBeVisible();
  await expect(allocation).toContainText("75.0%");
  await allocation.getByRole("button", { name: "All assets", exact: true }).click();
  await section.getByRole("button", { name: "This year", exact: true }).click();
  await expect(section.getByRole("button", { name: "This year", exact: true })).toHaveAttribute("aria-pressed", "true");
  await section.getByRole("button", { name: "All", exact: true }).click();
  await expect(section.getByRole("region", { name: "Monthly change bars", exact: true })).toBeVisible();
  await expect(section).toContainText("Partial activity record");
  await expect(table).toContainText("+20.00%");
  await expect(table).toContainText("−5.00%");
  await expect(table).not.toContainText("12,000.00");
  await section.getByRole("button", { name: "Show amounts" }).click();
  const september = table.getByRole("row").filter({ hasText: "2026-09-30" });
  await expect(september).toContainText("12,000.00");
  await expect(september).toContainText("2,000.00");
  await expect(table.getByRole("row").filter({ hasText: "2026-08-31" })).toContainText("—");
  await section.getByRole("button", { name: "Daily", exact: true }).focus();
  await page.keyboard.press("Enter");
  await expect(table).toHaveCount(0);
  await section.getByRole("button", { name: "Monthly", exact: true }).click();
  await section.getByRole("button", { name: "Hide amounts" }).click();
  for (const width of [320, 390, 1440]) {
    await page.setViewportSize({ width, height: 1000 });
    for (const dark of [false, true]) {
      await page.evaluate(dark => document.documentElement.classList.toggle("dark", dark), dark);
      await section.scrollIntoViewIfNeeded();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
      await expect(section.getByRole("region", { name: "Monthly asset changes" })).toBeVisible();
      await section.screenshot({ path: `test-results/monthly-assets-${width}-${dark ? "dark" : "light"}.png` });
    }
  }
});
