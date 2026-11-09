// Screenshot one local HTML file to PNG with system Chrome (same launcher as verify-web).
// Usage: node scripts/render_html.mjs <in.html> <out.png> <width> <height>
// Resolves @playwright/test from web/node_modules; no network; waits for fonts.
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const { chromium } = createRequire(path.join(root, "web/package.json"))("@playwright/test");
const [input, output, width, height] = process.argv.slice(2);
if (!input || !output || !Number(width) || !Number(height)) { console.error("usage: render_html.mjs in.html out.png width height"); process.exit(2); }

const browser = await chromium.launch({ channel: process.env.CHROME_PATH ? undefined : "chrome", executablePath: process.env.CHROME_PATH, args: ["--allow-file-access-from-files"] });
try {
  const page = await browser.newPage({ viewport: { width: Number(width), height: Number(height) }, deviceScaleFactor: 1 });
  await page.route(/^https?:/, route => route.abort());
  await page.goto(pathToFileURL(path.resolve(input)).href);
  await page.evaluate(() => document.fonts.ready);
  const fonts = await page.evaluate(() => [...document.fonts].filter(f => f.status === "error").map(f => f.family));
  await page.screenshot({ path: path.resolve(output), clip: { x: 0, y: 0, width: Number(width), height: Number(height) } });
  console.log(JSON.stringify({ ok: true, output: path.resolve(output), failed_fonts: fonts }));
} finally { await browser.close(); }
