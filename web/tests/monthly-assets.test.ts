import { expect, test } from "vitest";
import { createElement as h } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { TrackedAssetsChart } from "@/components/tracked-assets-chart";
import { AllocationBar } from "@/components/allocation-bar";
import { FinanceJournal } from "@/components/finance-journal";
import fixture from "@/app/design-system/finance-activity.fixture.json";
import type { ActivityReport } from "@/lib/activity";

test("asset history renders Python-projected changes without exposing amounts", () => {
  const html = renderToStaticMarkup(h(TrackedAssetsChart, { points: fixture.points, months: (fixture as ActivityReport).months, asOf: fixture.as_of }));
  expect(html).toContain("20.00");
  expect(html).toContain("5.00");
  expect(html).not.toContain("12,000.00");
  expect(html).toContain("Monthly asset change");
});
test("missing history, empty allocation and missing journal remain explicit", () => {
  expect(renderToStaticMarkup(h(TrackedAssetsChart, { points: [], months: [], asOf: "2026-10-04" }))).toContain("No asset snapshots");
  expect(renderToStaticMarkup(h(AllocationBar, { slices: [] }))).toContain("No priced assets");
  expect(renderToStaticMarkup(h(FinanceJournal, { entries: [], state: "missing" }))).toContain("No transaction journal yet");
});
