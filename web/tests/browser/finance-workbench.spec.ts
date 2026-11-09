// Uses the real Python/Next command path in synthetic demo mode. No private files.
import { test, expect, type Page } from "@playwright/test";

test.use({ reducedMotion: "reduce" });
async function open(page: Page) {
  await page.goto("/office?dept=finance&mode=demo");
  await expect(page.getByRole("button", { name: /Sample investment funding · open/ })).toBeVisible();
  await page.getByRole("button", { name: "Show amounts", exact: true }).click();
}
async function choose(page: Page, label: string, option: string) {
  await page.getByRole("combobox", { name: label, exact: true }).click();
  await page.getByRole("option", { name: option, exact: true }).click();
}
test("funding evidence saves independently, survives reload, and stale revisions retain the draft", async ({ page }, info) => {
  const errors: string[] = []; page.on("pageerror", e => errors.push(e.message));
  await open(page);
  await expect(page.getByText("Next evidence needed: Fund redemption", { exact: true })).toBeVisible();
  await choose(page, "Step status", "In transit");
  await page.getByLabel("Original amount", { exact: true }).fill("200");
  await page.getByLabel("Evidence or reason", { exact: true }).fill("Synthetic redemption receipt R-001; settlement pending.");
  const saved = page.waitForResponse(r => r.url().includes("/api/finance/workbench?mode=demo") && r.request().method() === "POST");
  await page.getByRole("button", { name: "Save step evidence", exact: true }).click();
  expect((await saved).ok()).toBe(true);
  await expect(page.getByText("In transit", { exact: true }).first()).toBeVisible();
  await expect(page.getByRole("button", { name: /Sample investment funding · open · revision 2/ })).toBeVisible();
  await page.reload();
  await expect(page.getByRole("button", { name: /Sample investment funding · open · revision 2/ })).toBeVisible();
  await page.getByRole("button", { name: "Show amounts", exact: true }).click();
  await expect(page.getByLabel("Evidence or reason", { exact: true })).toHaveValue(/R-001/);
  // Inject a stale-revision response to prove the UI retains the unsaved draft.
  await page.route("**/api/finance/workbench?mode=demo", async route => {
    if (route.request().method() === "POST") await route.fulfill({ status: 409, json: { error: { code: "revision_conflict" } } }); else await route.continue();
  });
  await page.getByLabel("Evidence or reason", { exact: true }).fill("Retain this unsaved conflict draft");
  await page.getByRole("button", { name: "Save step evidence", exact: true }).click();
  await expect(page.locator('[aria-label="Finance workbench"]').getByRole("alert")).toContainText("another tab");
  await expect(page.getByLabel("Evidence or reason", { exact: true })).toHaveValue("Retain this unsaved conflict draft");
  await page.screenshot({ path: info.outputPath("funding-evidence.png"), fullPage: true });
  expect(errors).toEqual([]);
});

test("monthly allocation calculates in Python, persists its result and records review", async ({ page }, info) => {
  await open(page);
  await page.getByRole("button", { name: "Monthly allocation", exact: true }).click();
  await page.getByLabel("Worksheet title", { exact: true }).fill("Sample monthly allocation");
  await page.getByLabel("Available after usual bills (MYR)", { exact: true }).fill("2000");
  await page.getByLabel("Near-term amount to reserve (MYR)", { exact: true }).fill("300");
  await page.getByLabel("Existing protected emergency reserve (MYR)", { exact: true }).fill("2000");
  await page.getByRole("button", { name: "I confirm these inputs are current", exact: true }).click();
  await page.getByRole("button", { name: "Calculate & save result", exact: true }).click();
  await expect(page.getByRole("button", { name: /Sample monthly allocation · draft/ })).toBeVisible();
  const output = page.locator('[aria-label="Selected finance record"]');
  await expect(output).toContainText("700.00");
  await expect(output).toContainText("1,000.00");
  await page.getByRole("button", { name: "Mark result reviewed", exact: true }).click();
  await expect(page.getByRole("button", { name: "Reviewed · no money moved", exact: true })).toBeDisabled();
  await page.reload();
  await page.getByRole("button", { name: "Monthly allocation", exact: true }).click();
  await expect(page.getByRole("button", { name: /Sample monthly allocation · reviewed · revision 2/ })).toBeVisible();
  await expect(output).not.toContainText("700.00"); // Amounts hide again on reload.
  await page.screenshot({ path: info.outputPath("monthly-allocation-masked.png"), fullPage: true });
});

test("cash scenarios retain dated assumptions, compare independently known values, and reflow", async ({ page }, info) => {
  const errors: string[] = []; page.on("pageerror", e => errors.push(e.message));
  await open(page);
  await page.getByRole("button", { name: "Scenario comparison", exact: true }).click();
  await page.getByLabel("Worksheet title", { exact: true }).fill("Sample income interruption");
  for (const [label, value] of [["Starting cash (MYR)", "10000"], ["Monthly income (MYR)", "4000"], ["Monthly expenses (MYR)", "3000"], ["Protected cash buffer (MYR)", "3000"], ["One-off cost in month one (MYR)", "2000"], ["Monthly expense increase (MYR)", "500"], ["Income interruption (months)", "1"], ["Comparison horizon (months)", "3"]]) await page.getByLabel(label, { exact: true }).fill(value);
  await page.getByRole("button", { name: "I confirm these inputs are current", exact: true }).click();
  await page.getByRole("button", { name: "Calculate & save result", exact: true }).click();
  const output = page.locator('[aria-label="Selected finance record"]');
  await expect(output).toContainText("13,000.00");
  await expect(output).toContainText("5,500.00");
  await expect(output).toContainText("No buffer breach within the entered horizon.");
  await page.reload();
  await page.getByRole("button", { name: "Scenario comparison", exact: true }).click();
  await expect(page.getByRole("button", { name: /Sample income interruption · draft/ })).toBeVisible();
  for (const width of [390, 320]) {
    await page.setViewportSize({ width, height: 1000 });
    await page.evaluate(() => document.documentElement.classList.add("dark"));
    await output.scrollIntoViewIfNeeded();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
    await page.screenshot({ path: info.outputPath(`scenario-${width}-dark.png`), fullPage: true });
  }
  expect(errors).toEqual([]);
});
