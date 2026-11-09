// What waits on the owner outside the Lab radar (docs/design/office-world.md "Town attention").
// One definition for the department buttons, the attention queue and the tab title.
// Content Lab follows the phone push kinds (scripts/lib/office/push.py: content_review, content_failed).
// Ideas are excluded: an idea only becomes work once the owner says go, so it is backlog, not a wait.
import type { LabItem } from "./content-lab.gen";
import type { ProposalView } from "./finance-research.gen";
import type { ContentStation, FinanceStation } from "./office-departments";

export type TownWait =
  | { department: "content"; station: ContentStation; count: number; label: string }
  | { department: "finance"; station: FinanceStation; count: number; label: string };

const plural = (count: number, one: string, many: string) => `${count} ${count === 1 ? one : many}`;
const closed = new Set(["published", "archived"]);

export function contentWaits(items: LabItem[]): TownWait[] {
  const open = items.flatMap(item => item.record && !closed.has(item.record.stage) ? [item.record] : []);
  const review = open.filter(record => record.stage === "review" && record.pipeline.status === "idle").length;
  const failed = open.filter(record => record.pipeline.status === "failed").length;
  const waits: TownWait[] = [];
  if (review) waits.push({ department: "content", station: "review", count: review, label: plural(review, "post to review", "posts to review") });
  if (failed) waits.push({ department: "content", station: "production", count: failed, label: plural(failed, "run failed", "runs failed") });
  return waits;
}

/** Proposals the Finance manager prepared that still need the owner's decision. */
export function researchWaitCount(proposals: Pick<ProposalView, "status">[]): number {
  return proposals.filter(view => view.status === "ready_for_review").length;
}

export function researchWaits(count: number | null): TownWait[] {
  return count ? [{ department: "finance", station: "research", count, label: plural(count, "proposal to review", "proposals to review") }] : [];
}

export const waitTotal = (waits: TownWait[]) => waits.reduce((sum, wait) => sum + wait.count, 0);
export const waitNote = (waits: TownWait[], department: TownWait["department"]) => waits.filter(wait => wait.department === department).map(wait => wait.label).join(" · ");
