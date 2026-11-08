import fs from "node:fs";
import { defineConfig } from "@playwright/test";

// Real-browser regression suites: tests/browser/*.spec.ts. Run with `make test-browser` (or `npm run test:browser`).
// Starts an isolated Next dev server. Software-rendered WebGL is slow, so timeouts are generous and tests poll instead of sleeping.
const port = Number(process.env.TEST_PORT ?? 3027);
const baseURL = `http://127.0.0.1:${port}`;
const executablePath = process.env.CHROME_PATH && fs.existsSync(process.env.CHROME_PATH) ? process.env.CHROME_PATH : undefined;

export default defineConfig({
  testDir: "tests/browser",
  testMatch: "**/*.spec.ts",
  timeout: 240_000,
  expect: { timeout: 20_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  outputDir: "test-results",
  use: {
    baseURL,
    viewport: { width: 1440, height: 1000 },
    ...(executablePath ? {} : { channel: "chrome" }),
    launchOptions: { ...(executablePath ? { executablePath } : {}), args: ["--enable-webgl", "--use-gl=angle", "--use-angle=swiftshader"] },
    screenshot: "only-on-failure",
  },
  webServer: {
    command: `npx next dev -p ${port}`,
    url: `${baseURL}/office?mode=demo`,
    reuseExistingServer: true,
    timeout: 180_000,
    env: { NEXT_DIST_DIR: `.next-browser-${port}` },
  },
});
