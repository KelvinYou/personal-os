// Exercise the actual page with an independently specified report/failure fixture.
import assert from "node:assert/strict";
import { renderToStaticMarkup } from "react-dom/server";
import { test, vi } from "vitest";

const state = vi.hoisted(() => ({
  failure: false,
  report: {
    summary: { passed: 0, failed: 0, conclusive: 0, inconclusive: 0, unreviewed: 0, runs: 0 },
    errors: [], configurations: [], cases: [], corpus_version: "test-fixture",
  },
}));
vi.mock("@/lib/skill-regressions", () => ({
  loadSkillRegressions: async () => {
    if (state.failure) throw new Error("Synthetic report source unavailable");
    return state.report;
  },
}));

import Page from "@/app/skill-regressions/page";

test("empty report explains absence without claiming a passing evaluation", async () => {
  state.failure = false;
  const html = renderToStaticMarkup(await Page());
  assert.match(html, /No configurations to compare/);
  assert.match(html, /An empty report is not evidence that checks passed/);
  assert.match(html, /Not available|Unreviewed/);
  assert.doesNotMatch(html, /<table/);
});

test("load failure preserves skip destination, recovery and diagnostic evidence", async () => {
  state.failure = true;
  const html = renderToStaticMarkup(await Page());
  assert.match(html, /<main id="main-content"/);
  assert.match(html, /<h1[^>]*>Skill regressions<\/h1>/);
  assert.match(html, /<h2[^>]*>Skill evidence unavailable<\/h2>/);
  assert.match(html, /href="\/skill-regressions"[^>]*>Try again/);
  assert.match(html, /<summary[^>]*>Local diagnostic<\/summary>/);
  assert.match(html, /Synthetic report source unavailable/);
  assert.doesNotMatch(html, /Passed runs|Configuration comparison/);
});
