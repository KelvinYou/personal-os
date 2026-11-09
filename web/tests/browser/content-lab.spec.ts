// Synthetic content/agent evidence; SSR uses demo Finance and tests intercept all Office APIs.
import fs from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";
test.use({ actionTimeout: 15000, reducedMotion: "reduce", permissions: ["clipboard-read", "clipboard-write"] });
const snapshot = JSON.parse(fs.readFileSync(path.join(__dirname, "../../../tests/fixtures/office/snapshot.json"), "utf8"));
const id = "sample-2026-01-01";
const record = { schema_version: 1, stage: "published", experiment: { hypothesis: "Actionable questions earn saves", changed_variable: "Opening question", gate: [{ question: 1, result: "pass", note: "Synthetic demand" }], demand_evidence: [] }, task_ids: [], readiness: { factual: "passed", visual: "passed", owner_review: "accepted" }, publication: { platform: "xhs", published_at: "2026-01-01T00:00:00Z", url: "https://www.xiaohongshu.com/explore/sample" }, measurements: [{ observed_at: "2026-01-08T00:00:00Z", source: "Synthetic capture", traffic: "organic", views: 120, saves: 0, likes: null, comments: null, shares: null, follows: null }], production: { minutes: null, cost: null, currency: null }, pipeline: { status: "idle", requested_at: null as string | null, feedback: [], runs: [] } };
const execution = { schema_version: 1, thread_id: null, turn_id: null, status: "ready", activity: "Ready", error: null, messages: [], input_request: null, poll_interval_ms: 60000, max_prompt_chars: 8000, updated_at: "2026-01-01T00:00:00Z", task: null, agents: [] };

test("content: ideas and pipeline boards, preserve world, review output and recorded results", async ({ page }, info) => {
  const errors: string[] = [], writes: string[] = [];
  page.on("pageerror", e => errors.push(e.message));
  page.on("request", r => { if (r.url().includes("/api/") && !["GET", "HEAD"].includes(r.method())) writes.push(r.url()); });
  let unavailable = false;
  await page.route("**/api/office/**", route => {
    const u = new URL(route.request().url());
    if (u.pathname.endsWith("/content-lab")) return route.fulfill({ status: unavailable ? 503 : 200, json: { schema_version: 1, items: [{ post_id: id, record }], partial: false } });
    if (u.pathname.endsWith("/state")) return route.fulfill({ json: snapshot });
    if (u.pathname.endsWith("/posts/image")) return route.fulfill({ contentType: "image/svg+xml", body: '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="400"><rect width="300" height="400" fill="beige"/><text x="20" y="60">Synthetic post</text></svg>' });
    if (u.pathname.endsWith("/posts")) {
      const p = { id, title: "Synthetic content package", date: "2026-01-01", imageCount: 1, cover: `/api/office/posts/image?id=${id}&name=01-cover.png` };
      return route.fulfill({ json: u.searchParams.has("id") ? { post: { ...p, images: [{ name: "01-cover.png", url: p.cover }], copy: "Synthetic publication copy", notes: "# Synthetic", verification: null } } : { posts: [p], partial: false } });
    }
    if (u.pathname.endsWith("/work")) return route.fulfill({ json: { schema_version: 1, runs: [], has_more: false } });
    return route.fulfill({ json: execution });
  });
  await page.goto("/office?mode=demo&dept=content&station=research");
  await expect(page.locator('.radar-canvas-shell[data-assets-ready="true"]')).toBeVisible();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Content Lab");
  await page.evaluate(() => { (window as unknown as { __canvas: unknown }).__canvas = document.querySelector("canvas"); });
  await expect(page.getByRole("heading", { name: "Ideas board", exact: true })).toBeVisible();
  await expect(page.getByText(/No ideas waiting/)).toBeVisible();
  expect(writes).toEqual([]);
  const nav = page.getByRole("navigation", { name: "Content Lab workstations", exact: true });
  await nav.getByRole("button", { name: "Pipeline", exact: true }).click();
  await expect(page.getByText("No packages in production.", { exact: true })).toBeVisible();
  await nav.getByRole("button", { name: "Results", exact: true }).click();
  await expect(page.getByRole("region", { name: "Seven-day content results" })).toContainText("120");
  await expect(page.getByRole("region", { name: "Seven-day content results" })).toContainText("Unknown");
  await expect(page.getByText(/Incomplete comparison: fewer than three/)).toBeVisible();
  expect(await page.evaluate(() => document.querySelector("canvas") === (window as unknown as { __canvas: unknown }).__canvas)).toBe(true);
  // Switch via real Source control to Live; APIs remain intercepted and no task is dispatched.
  await page.getByRole("combobox", { name: "Source", exact: true }).click();
  await page.getByRole("option", { name: "Live office", exact: true }).click();
  await nav.getByRole("button", { name: "Review", exact: true }).click();
  await page.getByRole("button", { name: /Synthetic content package/ }).click();
  await expect(page.getByRole("img", { name: "Synthetic content package — image 1", exact: true })).toBeVisible();
  // One scroller on the page view: no element inside the workspace scrolls vertically on its own.
  expect(await page.evaluate(() => [...document.querySelectorAll(".office-workspace *")].filter(e => /(auto|scroll)/.test(getComputedStyle(e).overflowY) && e.scrollHeight > e.clientHeight + 1).map(e => e.className))).toEqual([]);
  await page.getByRole("button", { name: "Enlarge image", exact: true }).click();
  const lightbox = page.getByRole("dialog", { name: "Synthetic content package — image viewer", exact: true });
  await expect(lightbox).toBeVisible();
  expect((await lightbox.boundingBox())!.width).toBeGreaterThan(1000);
  await page.keyboard.press("Escape");
  await expect(lightbox).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Enlarge image", exact: true })).toBeFocused();
  await page.getByRole("button", { name: "Copy text", exact: true }).click();
  expect(await page.evaluate(() => navigator.clipboard.readText())).toBe("Synthetic publication copy");
  await nav.getByRole("button", { name: "Results", exact: true }).click();
  await page.getByRole("button", { name: "Prepare results review", exact: true }).click();
  await expect(page.getByLabel("Task instruction")).toHaveValue(/seven-day evidence/);
  await expect(page.getByLabel("Task instruction")).toBeFocused();
  const composerBox = await page.getByLabel("Task instruction").boundingBox();
  expect(composerBox!.width).toBeGreaterThan(500);
  expect(writes).toEqual([]);
  unavailable = true; await page.getByRole("button", { name: "Refresh content", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Content records unavailable", exact: true })).toBeVisible();
  unavailable = false; await page.getByRole("button", { name: "Retry content", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Content records unavailable", exact: true })).not.toBeVisible();
  for (const width of [1440, 390, 320]) {
    await page.setViewportSize({ width, height: 1000 });
    await page.evaluate(() => document.documentElement.classList.toggle("dark", innerWidth === 390));
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
    await page.screenshot({ path: info.outputPath(`content-${width}.png`), fullPage: true });
  }
  expect(errors).toEqual([]);
});

test("content: invalid station falls back and demo never reads private posts or starts tasks", async ({ page }) => {
  const reads: string[] = [], writes: string[] = [];
  page.on("request", r => {
    const u = new URL(r.url());
    if (u.pathname.startsWith("/api/office/") && !u.searchParams.has("mode")) reads.push(u.pathname);
    if (u.pathname.startsWith("/api/") && r.method() !== "GET") writes.push(u.pathname);
  });
  await page.goto("/office?mode=demo&dept=content&station=assets");
  await expect(page.getByRole("heading", { name: "Ideas board", exact: true })).toBeVisible();
  await expect(page.getByText(/No ideas waiting/)).toBeVisible();
  await page.getByRole("navigation", { name: "Content Lab workstations" }).getByRole("button", { name: "Review", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Demo preview", exact: true })).toBeVisible();
  expect(reads).toEqual([]); expect(writes).toEqual([]);
});

test("content: fullscreen keeps the same world and station, including narrow overview", async ({ page }, info) => {
  const errors: string[] = []; page.on("pageerror", e => errors.push(e.message));
  await page.goto("/office?mode=demo&dept=content&station=research");
  await expect(page.locator('.radar-canvas-shell[data-assets-ready="true"]')).toBeVisible();
  await page.evaluate(() => { (window as unknown as { __canvas: unknown }).__canvas = document.querySelector("canvas"); });
  await page.getByRole("button", { name: "Fullscreen", exact: true }).click();
  await expect(page.locator(".office-world")).toHaveAttribute("data-world-screen", /native|expanded/);
  await expect(page.locator(".office-world").getByRole("heading", { name: "Ideas board", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Exit fullscreen", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Ideas board", exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.querySelector("canvas") === (window as unknown as { __canvas: unknown }).__canvas)).toBe(true);
  await page.setViewportSize({ width: 320, height: 1000 });
  await expect(page.locator(".office-room-panel")).toBeHidden();
  await page.getByRole("button", { name: "Show scene", exact: true }).click();
  await expect(page.locator(".town-anchor-department", { hasText: "Content Lab" })).toBeVisible();
  await page.screenshot({ path: info.outputPath("content-narrow-world.png"), fullPage: true });
  expect(errors).toEqual([]);
});

test("content: result entry preserves unknowns and keeps draft on conflict", async ({ page }) => {
  let current = { schema_version: 1, items: [{ post_id: id, record: structuredClone(record), revision: "a".repeat(64) }], partial: false };
  let conflict = false;
  const commands: Record<string, unknown>[] = [];
  await page.route("**/api/office/**", route => {
    const u = new URL(route.request().url());
    if (u.pathname.endsWith("/content-lab")) {
      if (route.request().method() === "POST") {
        const command = route.request().postDataJSON(); commands.push(command);
        if (conflict) return route.fulfill({ status: 409, json: { error: { code: "record_changed" } } });
        current = { ...current, items: [{ ...current.items[0], revision: "b".repeat(64), record: { ...current.items[0].record, publication: command.publication, measurements: [...current.items[0].record.measurements, command.measurement] } }] };
      }
      return route.fulfill({ json: current });
    }
    if (u.pathname.endsWith("/state")) return route.fulfill({ json: snapshot });
    if (u.pathname.endsWith("/posts")) return route.fulfill({ json: { posts: [{ id, title: "Synthetic content package", date: "2026-01-01", imageCount: 0, cover: null }], partial: false } });
    if (u.pathname.endsWith("/work")) return route.fulfill({ json: { schema_version: 1, runs: [], has_more: false } });
    return route.fulfill({ json: execution });
  });
  await page.goto("/office?mode=demo&dept=content&station=results");
  await page.getByRole("combobox", { name: "Source", exact: true }).click();
  await page.getByRole("option", { name: "Live office", exact: true }).click();
  await page.getByLabel("Measured at (local time)").fill("2026-01-09T08:00");
  await page.getByLabel("Views", { exact: true }).fill("0");
  await page.getByLabel("Evidence source", { exact: true }).fill("Synthetic creator dashboard");
  await page.getByRole("button", { name: "Save reported results", exact: true }).click();
  await expect(page.getByText("Results saved. The comparison now uses this recorded evidence.")).toBeVisible();
  expect(commands[0]).toMatchObject({ expected_revision: "a".repeat(64), measurement: { views: 0, saves: null, likes: null } });
  await page.reload();
  await expect(page.getByLabel("Published XHS link")).toHaveValue(record.publication.url);
  await page.getByLabel("Views", { exact: true }).fill("17");
  await page.getByLabel("Evidence source", { exact: true }).fill("Keep this evidence draft");
  conflict = true;
  await page.getByRole("button", { name: "Save reported results", exact: true }).click();
  await expect(page.getByRole("form", { name: "Record published post results" }).getByRole("alert")).toContainText("Your draft is kept");
  await expect(page.getByLabel("Views", { exact: true })).toHaveValue("17");
  await expect(page.getByLabel("Evidence source", { exact: true })).toHaveValue("Keep this evidence draft");
});

test("content: review approves, and a change note re-queues the pipeline without a task send", async ({ page }) => {
  let current = { schema_version: 1, items: [{ post_id: id, record: { ...structuredClone(record), stage: "review", publication: null, measurements: [], readiness: { factual: "unknown", visual: "unknown", owner_review: "pending" } }, revision: null as string | null }], partial: false };
  const commands: { decision: string; note: string }[] = [], otherWrites: string[] = [];
  page.on("request", r => { if (r.method() === "POST" && !r.url().endsWith("/content-lab")) otherWrites.push(r.url()); });
  await page.route("**/api/office/**", route => {
    const u = new URL(route.request().url());
    if (u.pathname.endsWith("/content-lab")) {
      if (route.request().method() === "POST") {
        const command = route.request().postDataJSON(); commands.push(command);
        current.items[0].record.readiness.owner_review = command.decision;
        if (command.note) current.items[0].record.pipeline = { ...current.items[0].record.pipeline, status: "queued", requested_at: "2026-01-02T00:00:00Z" };
        current.items[0].revision = commands.length.toString().repeat(64);
      }
      return route.fulfill({ json: current });
    }
    if (u.pathname.endsWith("/state")) return route.fulfill({ json: snapshot });
    if (u.pathname.endsWith("/posts/image")) return route.fulfill({ contentType: "image/svg+xml", body: '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="400"/>' });
    if (u.pathname.endsWith("/posts")) { const p = { id, title: "Synthetic review", date: "2026-01-01", imageCount: 1, cover: `/api/office/posts/image?id=${id}&name=01-cover.png` }; return route.fulfill({ json: u.searchParams.has("id") ? { post: { ...p, images: [{ name: "01-cover.png", url: p.cover }], copy: "Synthetic copy", notes: null, verification: null } } : { posts: [p], partial: false } }); }
    if (u.pathname.endsWith("/work")) return route.fulfill({ json: { schema_version: 1, runs: [], has_more: false } });
    return route.fulfill({ json: execution });
  });
  await page.goto("/office?mode=demo&dept=content&station=review");
  await page.getByRole("combobox", { name: "Source", exact: true }).click();
  await page.getByRole("option", { name: "Live office", exact: true }).click();
  await page.getByRole("button", { name: /Synthetic review Folder/ }).click();
  await page.getByRole("button", { name: "Approve content", exact: true }).click();
  await expect(page.getByText("Approved by you", { exact: true })).toBeVisible();
  expect(current.items[0].record.stage).toBe("review");
  await page.getByLabel("Changes to request", { exact: true }).fill("Simplify page two");
  await page.getByRole("button", { name: "Request changes", exact: true }).click();
  await expect(page.getByText(/Sent back. The pipeline revises it automatically/)).toBeVisible();
  await expect(page.getByText("Queued for revision", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Task instruction")).toHaveValue("");
  expect(commands.map(c => [c.decision, c.note])).toEqual([["accepted", ""], ["changes_requested", "Simplify page two"]]);
  expect(otherWrites).toEqual([]);
});

test("content: approving an idea queues it, and a failed run shows its reason with retry", async ({ page }) => {
  const idle = { status: "idle", requested_at: null, feedback: [], runs: [] };
  const ideaRecord = { ...structuredClone(record), stage: "idea", publication: null, measurements: [], readiness: { factual: "unknown", visual: "unknown", owner_review: "pending" }, pipeline: idle };
  const failed = { ...structuredClone(ideaRecord), stage: "research", pipeline: { status: "failed", requested_at: "2026-01-01T00:00:00Z", feedback: [{ at: "2026-01-01T00:00:00Z", note: "Use RM" }], runs: [{ started_at: "2026-01-01T00:00:00Z", finished_at: "2026-01-01T00:20:00Z", outcome: "failed", reason: "images: 4 pages, expected 6–9 numbered images", log: "failed-2026-01-01-20260101T000000Z.log" }] } };
  const current = { schema_version: 1, items: [{ post_id: "idea-2026-01-01", record: ideaRecord, revision: null as string | null }, { post_id: "failed-2026-01-01", record: failed, revision: "c".repeat(64) }], partial: false };
  const commands: { action: string; post_id: string }[] = [];
  await page.route("**/api/office/**", route => {
    const u = new URL(route.request().url());
    if (u.pathname.endsWith("/content-lab")) {
      if (route.request().method() === "POST") {
        const command = route.request().postDataJSON(); commands.push(command);
        const item = current.items.find(i => i.post_id === command.post_id)!;
        item.record = { ...item.record, stage: command.action === "approve_idea" ? "research" : item.record.stage, pipeline: { ...item.record.pipeline, status: "queued", requested_at: "2026-01-02T00:00:00Z" } };
      }
      return route.fulfill({ json: current });
    }
    if (u.pathname.endsWith("/state")) return route.fulfill({ json: snapshot });
    if (u.pathname.endsWith("/posts")) return route.fulfill({ json: { posts: [], partial: false } });
    if (u.pathname.endsWith("/work")) return route.fulfill({ json: { schema_version: 1, runs: [], has_more: false } });
    return route.fulfill({ json: execution });
  });
  await page.goto("/office?mode=demo&dept=content&station=research");
  await page.getByRole("combobox", { name: "Source", exact: true }).click();
  await page.getByRole("option", { name: "Live office", exact: true }).click();
  const idea = page.getByRole("article", { name: "Idea idea-2026-01-01" });
  await expect(idea).toContainText("Actionable questions earn saves");
  await idea.getByRole("button", { name: "Approve idea", exact: true }).click();
  await expect(page.getByText(/idea-2026-01-01: queued. The pipeline starts automatically/)).toBeVisible();
  await page.getByRole("navigation", { name: "Content Lab workstations" }).getByRole("button", { name: "Pipeline", exact: true }).click();
  const run = page.getByRole("article", { name: "Pipeline failed-2026-01-01" });
  await expect(run).toContainText("Failed — needs your decision");
  await expect(run).toContainText("images: 4 pages");
  await run.getByRole("button", { name: "Retry run", exact: true }).click();
  await expect(run).toContainText("Queued — starts automatically");
  expect(commands.map(c => [c.action, c.post_id])).toEqual([["approve_idea", "idea-2026-01-01"], ["requeue", "failed-2026-01-01"]]);
});
