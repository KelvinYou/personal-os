// Attention radar acceptance (docs/design/office-attention-radar.md). Synthetic demo and fixture only.
import fs from "node:fs";
import path from "node:path";
import { expect, test, type Page } from "@playwright/test";

test.use({ reducedMotion: "reduce" });
const fixture = JSON.parse(fs.readFileSync(path.join(__dirname, "../../../tests/fixtures/office/snapshot.json"), "utf8"));

async function noHorizontalScroll(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(0);
}

test("radar: zones, queue, selection, replay and reflow on the demo day", async ({ page }, info) => {
  const errors: string[] = []; page.on("pageerror", e => errors.push(e.message));
  const writes: string[] = []; page.on("request", r => { if (r.method() !== "GET" && r.url().includes("/api/")) writes.push(r.url()); });
  const stateRequests: string[] = []; page.on("request", r => { if (r.url().includes("/api/office/state")) stateRequests.push(r.url()); });
  await page.goto("/office?mode=demo&scenario=team");
  await page.locator("canvas").waitFor();
  await page.locator(".radar-label").first().waitFor();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Who needs you right now?");
  const counts = page.getByLabel("Attention summary");
  await expect(counts).toContainText("2 need you"); await expect(counts).toContainText("2 ready for review"); await expect(counts).toContainText("3 working");

  // Queue: needs-you first, oldest wait first; subagents never queue.
  const rows = page.locator(".radar-queue ol .radar-queue-row");
  await expect(rows).toHaveCount(4);
  // Other departments' owner decisions follow the sessions (demo seeds one research proposal).
  await expect(page.getByRole("button", { name: "Finance: 1 proposal to review" })).toBeVisible();
  await expect(rows.nth(0)).toContainText("Waiting for your input"); await expect(rows.nth(0)).toContainText("14m");
  await expect(rows.nth(1)).toContainText("Tool pending");
  await expect(page.locator(".radar-queue")).not.toContainText("Subagent");
  // Skills are badges, people are sessions.
  await expect(rows.nth(0).locator(".radar-badge")).toHaveText("Weekly Review");
  await page.locator(".office-viewport").screenshot({ path: info.outputPath("01-radar.png") });

  // Selecting a queue row opens details; the inferred approval wait says it is inferred.
  await rows.nth(1).click();
  await expect(page.getByLabel("Session details")).toContainText("Needs you");
  await expect(page.getByText(/Inferred: Claude Code does not record an open approval prompt/)).toBeVisible();
  await page.getByRole("button", { name: "Back to queue", exact: true }).click();
  await expect(page.getByLabel("Attention queue")).toBeVisible();

  // Replay: move to the morning; fewer people, replay banner, back to live restores.
  const scrub = page.getByRole("slider", { name: "Replay time" });
  const min = Number(await scrub.getAttribute("min")), max = Number(await scrub.getAttribute("max"));
  await scrub.evaluate((element, value) => {
    const input = element as HTMLInputElement;
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!.call(input, String(value));
    input.dispatchEvent(new Event("input", { bubbles: true }));
  }, max - 595 * 60000);
  expect(min).toBeLessThan(max);
  await expect(page.getByRole("heading", { name: /^Replaying \d\d:\d\d$/ })).toBeVisible();
  await expect(page.locator(".radar-canvas-shell[data-replay]")).toBeVisible();
  await expect(rows).toHaveCount(0);
  await page.locator(".office-viewport").screenshot({ path: info.outputPath("02-replay-morning.png") });
  await page.getByRole("button", { name: "Back to live", exact: true }).first().click();
  await expect(page.getByRole("heading", { name: "Live", exact: true })).toBeVisible();
  await expect(rows).toHaveCount(4);

  // Classic town is one link away and frozen.
  await expect(page.getByRole("link", { name: "Classic town" })).toHaveAttribute("href", /scene=town/);
  expect(stateRequests, "demo never queries local sessions").toEqual([]);
  expect(writes).toEqual([]);

  for (const width of [390, 320]) {
    await page.setViewportSize({ width, height: 900 });
    await page.locator(".radar-queue-row").first().waitFor();
    await noHorizontalScroll(page);
    await page.screenshot({ path: info.outputPath(`03-width-${width}.png`), fullPage: true });
  }
  expect(errors).toEqual([]);
});

test("radar: live fixture, empty and failing sources stay honest", async ({ page }) => {
  const errors: string[] = []; page.on("pageerror", e => errors.push(e.message));
  let mode: "ok" | "empty" | "fail" = "ok";
  await page.route("**/api/office/state", route => mode === "fail" ? route.fulfill({ status: 503, json: { error: { code: "source_unavailable" } } }) : route.fulfill({ json: { ...fixture, sessions: mode === "empty" ? [] : fixture.sessions } }));
  await page.route("**/api/office/work", route => route.fulfill({ json: { schema_version: 1, runs: [], has_more: false } }));
  // Department waits read private records in live mode; keep them empty so only sessions count.
  await page.route("**/api/office/content-lab", route => route.fulfill({ json: { schema_version: 1, items: [], partial: false } }));
  await page.route("**/api/finance/research", route => route.fulfill({ status: 503, json: { error: { code: "research_unavailable" } } }));
  await page.route("**/api/office/collaboration", route => route.fulfill({ json: { tasks: [], resources: [], events: [], available: true } }));
  await page.route("**/api/office/execution", route => route.fulfill({ json: { schema_version: 1, thread_id: null, turn_id: null, status: "ready", activity: "Ready", error: null, messages: [], input_request: null, poll_interval_ms: 60000, max_prompt_chars: 8000, updated_at: "2026-11-01T12:00:00Z", task: null, agents: [] } }));
  await page.goto("/office");
  await expect(page.getByLabel("Attention summary")).toContainText("1 working");
  await expect(page.getByText("Codex connected · Claude connected").first()).toBeVisible();
  await expect(page.getByText("Nothing waiting on you")).toBeVisible();
  await expect(page.getByText("Office tasks")).toBeVisible();
  mode = "empty"; await page.getByRole("button", { name: "Refresh", exact: true }).click();
  await expect(page.getByText("A quiet office")).toBeVisible();
  mode = "fail"; await page.getByRole("button", { name: "Refresh", exact: true }).click();
  await expect(page.locator(".office-source-notice[role=alert]")).toContainText("Cannot refresh local session evidence");
  expect(errors).toEqual([]);
});

// Alerts are only useful while you are in another window: a hidden tab must keep
// polling when alerts are on, and stop polling when they are off.
for (const alerts of [true, false]) test(`radar: hidden tab ${alerts ? "keeps polling and notifies" : "stops polling"} with alerts ${alerts ? "on" : "off"}`, async ({ page }) => {
  await page.addInitScript((on: boolean) => {
    const w = window as unknown as { __hidden: boolean; __notes: string[] };
    w.__hidden = false; w.__notes = [];
    Object.defineProperty(Document.prototype, "hidden", { configurable: true, get: () => w.__hidden });
    Object.defineProperty(Document.prototype, "visibilityState", { configurable: true, get: () => w.__hidden ? "hidden" : "visible" });
    class FakeNotification { static permission = "granted"; static requestPermission = async () => "granted"; constructor(title: string) { w.__notes.push(title); } }
    Object.defineProperty(window, "Notification", { configurable: true, value: FakeNotification });
    localStorage.setItem("office-radar-alerts", on ? "on" : "off");
  }, alerts);
  let waiting = false; let hiddenRequests = 0; let hidden = false;
  const needsYou = { ...fixture.sessions[0], state: "waiting", attention: "needs_you", attention_since: fixture.observed_at, activity_label: "Waiting for your approval", tool: null };
  await page.route("**/api/office/state", route => { if (hidden) hiddenRequests++; return route.fulfill({ json: { ...fixture, sessions: [waiting ? needsYou : fixture.sessions[0]] } }); });
  await page.route("**/api/office/work", route => route.fulfill({ json: { schema_version: 1, runs: [], has_more: false } }));
  // Department waits read private records in live mode; keep them empty so only sessions count.
  await page.route("**/api/office/content-lab", route => route.fulfill({ json: { schema_version: 1, items: [], partial: false } }));
  await page.route("**/api/finance/research", route => route.fulfill({ status: 503, json: { error: { code: "research_unavailable" } } }));
  await page.route("**/api/office/collaboration", route => route.fulfill({ json: { tasks: [], resources: [], events: [], available: true } }));
  await page.route("**/api/office/execution", route => route.fulfill({ json: { schema_version: 1, thread_id: null, turn_id: null, status: "ready", activity: "Ready", error: null, messages: [], input_request: null, poll_interval_ms: 60000, max_prompt_chars: 8000, updated_at: "2026-11-01T12:00:00Z", task: null, agents: [] } }));
  await page.goto("/office");
  await expect(page.getByLabel("Attention summary")).toContainText("1 working");
  await expect(page.getByRole("button", { name: alerts ? "Alerts on" : "Alert me" })).toBeVisible();
  hidden = true; waiting = true;
  await page.evaluate(() => { (window as unknown as { __hidden: boolean }).__hidden = true; document.dispatchEvent(new Event("visibilitychange")); });
  if (alerts) {
    await expect.poll(() => page.evaluate(() => (window as unknown as { __notes: string[] }).__notes), { timeout: 10000 }).toEqual([expect.stringMatching(/needs you$/)]);
    await expect(page).toHaveTitle(/^\(1\) /);
  } else {
    await page.waitForTimeout(fixture.poll_interval_ms * 2 + 500);
    expect(hiddenRequests, "hidden tab without alerts does not poll").toBe(0);
  }
});

test("posts live on their own route", async ({ page }) => {
  await page.route("**/api/office/posts", route => route.fulfill({ json: { posts: [], partial: false } }));
  await page.goto("/posts");
  await expect(page.getByRole("heading", { name: "Posts", exact: true })).toBeVisible();
  await expect(page.getByText("No posts yet")).toBeVisible();
  await expect(page.getByRole("button", { name: "Close posts" })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Posts" })).toHaveAttribute("aria-current", "page");
});
