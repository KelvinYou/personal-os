// Deterministic workbench acceptance: answer a question, review/accept a saved result, history, reflow, source failure.
// All private endpoints are routed to synthetic evidence.
import fs from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";

test.use({ reducedMotion: "reduce" });

interface Run {
  schema_version: number;
  task: { id: string; instruction: string; skill_id: string; status: string; collaboration: string; started_at: string };
  status: string; result: string; agents: never[]; artifacts: string[]; updated_at: string; error: null;
  revision: number; review: string; reviewed_at: null;
}
interface ReviewBody { task_id: string; revision: number; review: string }
interface ExecAction { action: string }
interface Snapshot {
  schema_version: number; thread_id: string; turn_id: string | null; status: string; activity: string; error: null; messages: never[];
  input_request: { id: string; questions: object[] } | null; poll_interval_ms: number; max_prompt_chars: number; updated_at: string;
  task: { id: string; instruction: string; skill_id: string; status: string; collaboration: string; started_at: string }; agents: never[];
}

const now = "2026-11-03T08:00:00Z";
const fixture: unknown = JSON.parse(fs.readFileSync(path.join(__dirname, "../../../tests/fixtures/office/snapshot.json"), "utf8"));
const makeRun = (id: string, instruction: string): Run => ({
  schema_version: 1,
  task: { id, instruction, skill_id: "contract-guardian", status: "completed", collaboration: "solo", started_at: now },
  status: "idle", result: "Reviewed the fixture. All acceptance checks passed.", agents: [], artifacts: ["docs/result.md"],
  updated_at: now, error: null, revision: 0, review: "pending", reviewed_at: null,
});

test("workbench: answer, review, artifact, history, reflow, source failure", async ({ page }, testInfo) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));

  const runs: Run[] = [makeRun("run-1", "Review the task contract")];
  let snapshot: Snapshot = {
    schema_version: 1, thread_id: "root", turn_id: "turn-1", status: "waiting", activity: "Waiting for your answer", error: null, messages: [],
    input_request: { id: "input-1", questions: [{ id: "choice", header: "Scope", question: "Which scope should I review?", options: null, isSecret: false }] },
    poll_interval_ms: 500, max_prompt_chars: 8000, updated_at: now,
    task: { id: "active", instruction: "Review the new workflow", skill_id: "contract-guardian", status: "running", collaboration: "solo", started_at: now }, agents: [],
  };
  let sends = 0, answers = 0, unavailable = false;
  const boardTask = { id: "board-1", title: "Resolve shared task blocker", description: "A prerequisite is missing", status: "blocked", revision: 0, assignee: null, recipient: null, depends_on: [], resources: [], result: "Waiting for API evidence", parent_id: null, managed: false, role: null, thread_id: null, runner_pid: null, created_at: 1, updated_at: 1 };

  await page.route("**/api/office/state", (r) => r.fulfill({ json: fixture }));
  await page.route("**/api/office/collaboration", (r) => r.fulfill({ json: { schema_version: 1, tasks: [boardTask], resources: [], events: [], poll_interval_ms: 1000, runtime_available: true, execution_mode: "read-only", max_parallel_teams: 1, lease_seconds: 60, available: true, listeners: [] } }));
  await page.route("**/api/office/work", async (r) => {
    if (unavailable) return r.fulfill({ status: 503, json: { error: { code: "history_unavailable" } } });
    if (r.request().method() === "POST") {
      const body = r.request().postDataJSON() as ReviewBody;
      const run = runs.find((x) => x.task.id === body.task_id);
      expect(run).toBeDefined();
      if (!run) return;
      expect(body.revision).toBe(run.revision);
      run.review = body.review;
      run.revision++;
      return r.fulfill({ json: run });
    }
    return r.fulfill({ json: { schema_version: 1, runs, has_more: false } });
  });
  await page.route("**/api/office/work/artifact?*", (r) => r.fulfill({ contentType: "text/plain", body: "# Verified deliverable\nUseful artifact text" }));
  await page.route("**/api/office/execution", async (r) => {
    if (r.request().method() === "POST") {
      const action = r.request().postDataJSON() as ExecAction;
      if (action.action === "answer") {
        answers++;
        snapshot = { ...snapshot, status: "idle", input_request: null, turn_id: null, task: { ...snapshot.task, status: "completed" }, updated_at: new Date(Date.parse(now) + 1000).toISOString() };
      }
      if (action.action === "send") sends++;
    }
    await r.fulfill({ json: snapshot });
  });

  const button = (name: string) => page.getByRole("button", { name, exact: true });

  await page.goto("/office");
  await expect(button("Answer question")).toBeVisible();
  await expect(page.getByRole("radio", { name: "Solo", exact: true })).toBeChecked();

  await test.step("answer the pending question", async () => {
    await button("Answer question").click();
    await expect(page.locator("#office-answer")).toBeFocused();
    await page.locator("#office-answer").fill("The complete workflow");
    await button("Send answer").click();
    await expect(button("Answer question")).toHaveCount(0);
    expect(answers).toBe(1);
  });

  await test.step("review result, open artifact, accept / request changes / accept", async () => {
    await button("Review result: Review the task contract").click();
    await expect(page.getByRole("region", { name: "Saved task result" })).toBeVisible();
    await button("docs/result.md").click();
    await expect(page.getByText("# Verified deliverable\nUseful artifact text", { exact: true })).toBeVisible();
    await button("Accept result").focus();
    await page.keyboard.press("Enter");
    await expect(button("Accepted")).toBeVisible();
    await button("Request changes").click();
    await expect(page.getByText("CHANGES REQUESTED", { exact: true })).toBeVisible();
    await button("Accept result").click();
    await expect(button("Accepted")).toBeVisible();
  });

  await test.step("acceptance survives reload via history", async () => {
    await page.reload();
    await button("Task history · 1").click();
    await page.getByRole("button").filter({ hasText: "Review the task contract" }).click();
    await expect(button("Accepted")).toBeVisible();
  });

  await test.step("prepare follow-up fills the prompt without dispatching", async () => {
    await button("Prepare follow-up").click();
    await expect(page.locator("#office-task-prompt")).toHaveValue(/Review the task contract/);
    expect(sends).toBe(0);
  });

  for (const width of [1440, 390, 320]) {
    await test.step(`no horizontal overflow at ${width}px`, async () => {
      await page.setViewportSize({ width, height: 1000 });
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.screenshot({ fullPage: true, path: testInfo.outputPath(`workbench-${width}.png`) });
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `overflow at ${width}`).toBe(true);
    });
  }

  await test.step("dark theme screenshot", async () => {
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.evaluate(() => document.documentElement.classList.add("dark"));
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ fullPage: true, path: testInfo.outputPath("workbench-dark.png") });
  });

  await test.step("history source failure keeps last-known records and disables review", async () => {
    unavailable = true;
    await button("Refresh work").click();
    await expect(page.getByText("Task history is unavailable. Last-known records are retained.", { exact: true })).toBeVisible();
    await expect(button("Accepted")).toBeDisabled();
    unavailable = false;
    const old = makeRun("old-run", "Previously running task");
    old.status = "working";
    old.task.status = "running";
    old.result = "";
    runs.push(old);
    await button("Refresh work").click();
    await expect(page.getByText("LAST-KNOWN RUN · CURRENT STATUS UNKNOWN", { exact: true })).toBeVisible();
    await button("Inspect work").click();
    await expect(button("Accept result")).toBeDisabled();
  });

  expect(errors).toEqual([]);
});
