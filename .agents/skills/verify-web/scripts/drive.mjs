#!/usr/bin/env node
// Drive one user journey on the verify instance and write evidence.
// Usage (run from web/ so @playwright/test resolves):
//   node ../.agents/skills/verify-web/scripts/drive.mjs --port 3041 --route /flows \
//     --heading "Flows" [--wait-for "css" | "iframe >> css"]... [--click "Button name"]...
//     [--expect-text "text"]... [--label flows] [--width 390] [--full] [--dark]
// Always fails on page errors and on horizontal page scroll (UI rule: none at 320px).
// Evidence: web/test-results/verify-web/<stamp>-<label>/ {before.png, after.png, evidence.json}
// Records every step, page errors, console errors, and non-GET /api/ requests (side effects).
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

// ESM resolves bare imports from this file's folder; resolve Playwright from web/ (the cwd) instead.
const { chromium } = createRequire(path.join(process.cwd(), "package.json"))("@playwright/test");

const args = process.argv.slice(2);
const one = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const many = k => args.flatMap((a, i) => (a === k ? [args[i + 1]] : []));
const port = one("--port", process.env.VERIFY_PORT ?? "3041");
const route = one("--route", "/");
const heading = one("--heading");
const label = one("--label", route.replace(/[^a-z0-9]+/gi, "-").replace(/^-|-$/g, "") || "root");
const clicks = many("--click");
const texts = many("--expect-text");
const waits = many("--wait-for"); // CSS selectors that must exist before "before.png" (e.g. a WebGL canvas)
const width = Number(one("--width", "1440"));
const full = args.includes("--full"); // full-page after.png, for sections below the fold
const dark = args.includes("--dark"); // same class toggle the browser specs use

const stamp = new Date().toISOString().replace(/[:.]/g, "-");
const out = path.resolve("test-results", "verify-web", `${stamp}-${label}`);
fs.mkdirSync(out, { recursive: true });

const evidence = { route, port: Number(port), width, started_at: new Date().toISOString(), steps: [], page_errors: [], console_errors: [], failed_responses: [], writes: [], result: "fail" };
const step = (action, outcome, ok = true) => { evidence.steps.push({ action, outcome, ok }); if (!ok) throw new Error(`${action}: ${outcome}`); };

const browser = await chromium.launch({ channel: process.env.CHROME_PATH ? undefined : "chrome", executablePath: process.env.CHROME_PATH, args: ["--enable-webgl", "--use-gl=angle", "--use-angle=swiftshader"] });
try {
  const page = await browser.newPage({ viewport: { width, height: 1000 } });
  page.on("pageerror", e => evidence.page_errors.push(e.message));
  page.on("console", m => { if (m.type() === "error") evidence.console_errors.push(m.text()); });
  page.on("response", r => { if (r.status() >= 400) evidence.failed_responses.push(`${r.status()} ${r.url()}`); });
  page.on("request", r => { if (!["GET", "HEAD"].includes(r.method()) && r.url().includes("/api/")) evidence.writes.push(`${r.method()} ${r.url()}`); });

  const res = await page.goto(`http://127.0.0.1:${port}${route}`, { waitUntil: "domcontentloaded", timeout: 120_000 });
  step(`goto ${route}`, `HTTP ${res?.status()}`, (res?.status() ?? 0) < 400);
  if (heading) {
    await page.getByRole("heading", { name: heading, level: 1 }).first().waitFor({ timeout: 60_000 });
    step(`expect h1 "${heading}"`, "visible");
  }
  for (const sel of waits) {
    // "iframe-css >> inner-css" waits inside a same-origin iframe (e.g. the home viewer).
    const [outer, inner] = sel.split(" >> ");
    const target = inner ? page.frameLocator(outer).locator(inner) : page.locator(sel);
    await target.first().waitFor({ timeout: 120_000 });
    step(`wait for ${sel}`, "present");
  }
  if (dark) {
    await page.evaluate(() => document.documentElement.classList.add("dark"));
    step("dark appearance", "html.dark set");
  }
  await page.screenshot({ path: path.join(out, "before.png"), fullPage: false, caret: "initial" });
  for (const name of clicks) {
    await page.getByRole("button", { name, exact: true }).or(page.getByRole("link", { name, exact: true })).first().click({ timeout: 30_000 });
    step(`click "${name}"`, "clicked");
  }
  for (const t of texts) {
    await page.getByText(t).first().waitFor({ timeout: 30_000 });
    step(`expect text "${t}"`, "visible");
  }
  await page.screenshot({ path: path.join(out, "after.png"), fullPage: full, caret: "initial" });
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - innerWidth);
  step("no horizontal page scroll", overflow > 1 ? `page is ${overflow}px wider than the viewport` : "ok", overflow <= 1);
  step("page errors", evidence.page_errors.length ? evidence.page_errors.join(" | ") : "none", evidence.page_errors.length === 0);
  evidence.result = "pass";
} catch (e) {
  evidence.error = String(e?.message ?? e);
} finally {
  evidence.finished_at = new Date().toISOString();
  fs.writeFileSync(path.join(out, "evidence.json"), JSON.stringify(evidence, null, 2));
  await browser.close();
  console.log(`[Status: ${evidence.result === "pass" ? "OK" : "Critical"}] ${route} → ${out}`);
  process.exitCode = evidence.result === "pass" ? 0 : 1;
}
