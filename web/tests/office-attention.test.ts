// Town attention outside the Lab radar (docs/design/office-world.md). Synthetic records only.
import assert from "node:assert/strict";
import { test } from "vitest";
import type { LabItem } from "@/lib/content-lab.gen";
import { contentWaits, researchWaitCount, researchWaits, waitNote, waitTotal } from "@/lib/office-attention";

const item = (stage: string, status: string): LabItem => ({ post_id: `${stage}-${status}`, revision: null, record: { stage, pipeline: { status } } } as unknown as LabItem);

test("content waits count idle review and failed runs, matching the phone push kinds", () => {
  const waits = contentWaits([item("review", "idle"), item("review", "idle"), item("production", "failed"), item("review", "running"), item("idea", "idle"), item("ready", "idle")]);
  assert.deepEqual(waits.map(w => [w.station, w.count, w.label]), [["review", 2, "2 posts to review"], ["production", 1, "1 run failed"]]);
});

test("ideas, closed posts and records without workflow metadata never wait on the owner", () => {
  const unrecorded = { post_id: "legacy", revision: null, record: null } as unknown as LabItem;
  assert.deepEqual(contentWaits([item("idea", "idle"), item("archived", "failed"), item("published", "idle"), unrecorded]), []);
});

test("research waits are proposals ready for review; unavailable research adds nothing", () => {
  assert.equal(researchWaitCount([{ status: "ready_for_review" }, { status: "accepted" }, { status: "revise" }, { status: "ready_for_review" }]), 2);
  assert.deepEqual(researchWaits(1).map(w => [w.department, w.station, w.label]), [["finance", "research", "1 proposal to review"]]);
  assert.deepEqual(researchWaits(0), []);
  assert.deepEqual(researchWaits(null), []);
});

test("total and per-department note combine every wait", () => {
  const waits = [...contentWaits([item("review", "idle"), item("production", "failed")]), ...researchWaits(3)];
  assert.equal(waitTotal(waits), 5);
  assert.equal(waitNote(waits, "content"), "1 post to review · 1 run failed");
  assert.equal(waitNote(waits, "finance"), "3 proposals to review");
});
