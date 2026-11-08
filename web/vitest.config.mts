import path from "node:path";
import { defineConfig } from "vitest/config";

// Unit and contract tests live in tests/**/*.test.ts. Real-browser suites are separate (tests/browser/*.spec.ts, `make test-browser`).
export default defineConfig({
  // tsconfig keeps `jsx: preserve` for Next; tests that render TSX need the automatic runtime.
  oxc: { jsx: { runtime: "automatic" } },
  resolve: { alias: { "@": path.resolve(import.meta.dirname) } },
  test: { include: ["tests/**/*.test.ts"], environment: "node" },
});
