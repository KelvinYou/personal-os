import type { NextConfig } from "next";

// Local-only dashboard: it reads private finance data off the filesystem and is
// never deployed. See docs/plan-wealth-dashboard.md §1.2.
const config: NextConfig = {
  // Keep a preview build separate when another local dev server is running.
  distDir: process.env.NEXT_DIST_DIR || ".next",
};

export default config;
