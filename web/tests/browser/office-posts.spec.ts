// Synthetic endpoints only; no private filesystem reads.
import fs from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";
test.use({ reducedMotion: "reduce", permissions: ["clipboard-read", "clipboard-write"] });
const snapshot = JSON.parse(fs.readFileSync(path.join(__dirname, "../../../tests/fixtures/office/snapshot.json"), "utf8"));
const id = "sample-2026-01-02", title = "示例图文 · A small everyday mechanism";
const image = (n: number) => `/api/office/posts/image?id=${id}&name=0${n}-page.png`;
const summary = { id, title, date: "2026-01-02", imageCount: 2, cover: image(1) };
const post = { ...summary, images: [1, 2].map(n => ({ name: `0${n}-page.png`, url: image(n) })), copy: "Synthetic caption\n\nReadable publication copy.", notes: "# Notes\n\n<script>window.untrusted = true</script>", verification: null };
const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="900" height="1200"><rect width="900" height="1200" fill="#f4f0e7"/><text x="60" y="130" font-family="sans-serif" font-size="60" fill="#181a1b">An everyday question</text><circle cx="450" cy="570" r="220" fill="#b9c5b0"/><text x="140" y="1040" font-family="sans-serif" font-size="38" fill="#181a1b">SYNTHETIC POST / 01</text></svg>`;
test("posts: board, reader, copy, focus, reflow and recovery", async ({ page }, info) => {
  const errors: string[] = []; page.on("pageerror", e => errors.push(e.message));
  let state = "complete", failDetail = false;
  await page.route("**/api/office/**", r => {
    const u = new URL(r.request().url());
    if (u.pathname.endsWith("/posts/image")) return r.fulfill({ contentType: "image/svg+xml", body: svg });
    if (u.pathname.endsWith("/posts")) {
      if (u.searchParams.has("id")) return r.fulfill({ status: failDetail ? 404 : 200, json: { post } });
      return r.fulfill({ status: state === "error" ? 503 : 200, json: { posts: ["empty", "partial"].includes(state) ? [] : [summary], partial: state === "partial" } });
    }
    if (u.pathname.endsWith("/state")) return r.fulfill({ json: snapshot });
    if (u.pathname.endsWith("/work")) return r.fulfill({ json: { schema_version: 1, runs: [], has_more: false } });
    if (u.pathname.endsWith("/collaboration")) return r.fulfill({ json: { tasks: [], resources: [], events: [], available: true } });
    return r.fulfill({ json: { schema_version: 1, thread_id: null, turn_id: null, status: "ready", activity: "Ready", error: null, messages: [], input_request: null, poll_interval_ms: 60000, max_prompt_chars: 8000, updated_at: "2026-01-02T00:00:00Z", task: null, agents: [] } });
  });
  const button = (name: string) => page.getByRole("button", { name, exact: true });
  await page.goto("/office");
  await page.locator(".office-host-label").waitFor();
  await button("Browse posts").click(); await expect(page.getByRole("dialog")).toBeVisible(); await button("Close posts").click();
  await button("Posts").click(); await page.getByRole("button", { name: new RegExp(title) }).click();
  await expect(page.getByRole("img", { name: `${title} — image 1` })).toBeVisible();
  await button("Next image").click(); await expect(page.getByText("Image 2 of 2", { exact: true })).toBeVisible(); await expect(button("Next image")).toBeDisabled();
  await page.keyboard.press("ArrowLeft"); await expect(page.getByText("Image 1 of 2", { exact: true })).toBeVisible();
  await button("Copy text").click(); await expect(page.getByText("Copied publication copy.", { exact: true })).toBeVisible();
  expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(post.copy);
  await expect(page.getByText("Post notes and sources", { exact: true })).toHaveCount(0);
  await expect(page.getByText("Verification record", { exact: true })).toHaveCount(0);
  expect(await page.evaluate(() => "untrusted" in window)).toBe(false);
  await button("Enlarge image").click(); await expect(button("Fit image")).toBeVisible(); await page.keyboard.press("Escape"); await expect(button("Enlarge image")).toBeVisible();
  for (const theme of ["light", "dark"]) {
    await page.evaluate(v => document.documentElement.classList.toggle("dark", v === "dark"), theme);
    for (const width of [1440, 390, 320]) {
      await page.setViewportSize({ width, height: 1000 }); await page.screenshot({ path: info.outputPath(`posts-${theme}-${width}.png`) });
      expect(await page.locator("dialog").evaluate(e => e.scrollWidth <= e.clientWidth + 1)).toBe(true);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
    }
  }
  await page.keyboard.press("Escape"); await expect(page.getByRole("dialog")).not.toBeVisible(); await expect(button("Posts")).toBeFocused();
  await button("Posts").click(); await button("All posts").click();
  state = "partial"; await button("Refresh posts").click(); await expect(page.getByRole("heading", { name: "Some posts are unavailable" })).toBeVisible(); await expect(page.getByRole("heading", { name: "No posts yet" })).not.toBeVisible();
  state = "empty"; await button("Refresh posts").click(); await expect(page.getByRole("heading", { name: "No posts yet" })).toBeVisible();
  state = "error"; await button("Refresh posts").click(); await expect(page.getByRole("heading", { name: "Posts unavailable" })).toBeVisible();
  state = "complete"; await button("Retry posts").click(); failDetail = true; await page.getByRole("button", { name: new RegExp(title) }).click();
  await expect(page.getByRole("heading", { name: "Post unavailable" })).toBeVisible(); failDetail = false; await button("Retry post").click(); await expect(button("Copy text")).toBeVisible();
  await page.keyboard.press("Escape"); await button("Third person").click(); await button("Posts").click(); await page.keyboard.press("Escape"); await expect(page.locator("[data-office-view=third]")).toBeVisible();
  expect(errors).toEqual([]);
});
