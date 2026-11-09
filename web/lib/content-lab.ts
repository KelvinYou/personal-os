import type { LabCollection, Measurement } from "./content-lab.gen";
import type { ContentStation } from "./office-departments";

export function contentBrief(station: ContentStation, problem: string, audience: string, evidence: string, destination: "local" | "client") {
  const task = station === "research"
    ? "Research at least three topic candidates. Inspect reader demand, ordinary competitor posts as well as high performers, and primary sources. Recommend one candidate with limitations. Never invent search volume or competitor metrics."
    : station === "production" ? "Produce one XHS carousel package: post.md, verification.md, prompts.md, ordered final images and publish.txt. Verify claims before images, then inspect every page."
      : station === "review" ? "Review the actual content package against factual, visual and publication checks. Name specific changes; do not infer publication or owner acceptance."
        : "Review recorded seven-day evidence against the account's own median at comparable ages and traffic coverage. Name the next single-variable experiment. Insufficient evidence stays incomplete.";
  return `Use the social-post skill and follow its current topic gate.\nReader problem: ${problem.trim()}\nAudience: ${audience.trim()}\nAvailable evidence / target post: ${evidence.trim() || "Not supplied; distinguish unknown from observed."}\n\n${task}\n\nResolve account identity and post conventions from data/posts/brand.md and data/posts/README.md. Use data/posts/<topic>-YYYY-MM-DD/. Record gate results, readiness, publication and measurements only in the optional lab.yaml record; run make posts-check after writes. Keep sources and prose in post.md. Never mark ready without actual images, copy and owner acceptance. Do not publish, interact with platform users, commit or spawn agents.\n\n${destination === "local" ? "LOCAL TASK: Office network access is disabled. Use existing local evidence only. If online research or image generation is needed, return an explicit client handoff instead of claiming success." : "CLIENT HANDOFF: Use available official web/image tools; report missing capabilities honestly. Return files to the private post folder, then refresh Content Lab. Copying this brief is not task execution."}`;
}

/** One observation per post in an explicit 7–8 day window; don't mix traffic types. */
export function sevenDayResults(collection: LabCollection): { postId: string; measurement: Measurement; ageHours: number }[] {
  return collection.items.flatMap(item => {
    const record = item.record;
    if (!record?.publication) return [];
    const start = Date.parse(record.publication.published_at);
    const match = record.measurements.map(m => ({ measurement: m, ageHours: (Date.parse(m.observed_at) - start) / 3600000 }))
      .filter(m => m.ageHours >= 168 && m.ageHours < 192).sort((a, b) => a.ageHours - b.ageHours)[0];
    return match ? [{ postId: item.post_id, ...match }] : [];
  });
}
export function median(values: number[]): number | null {
  if (!values.length) return null;
  const sorted = [...values].sort((a, b) => a - b), mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}
