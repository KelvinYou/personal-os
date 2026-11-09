// Team collaboration acceptance through the real UI. All office endpoints are routed to synthetic evidence.
// (The old script's `--live` mode, which spent model usage on a real two-agent run, is not carried over.)
import fs from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";

test.use({ reducedMotion: "reduce" });

interface Agent { id: string; task_id: string; thread_id: string; parent_id: string | null; role: string; assignment: string; status: string; result: string | null; updated_at: string }
interface TeamTask { id: string; skill_id: string; instruction: string; collaboration: string; status: string; started_at: string }
interface Snapshot {
  schema_version: number; thread_id: string | null; turn_id: string | null; status: string; activity: string; error: string | null;
  messages: { id: string; role: string; text: string }[]; input_request: null; poll_interval_ms: number; max_prompt_chars: number;
  updated_at: string; task: TeamTask | null; agents: Agent[];
}
interface SendAction { action: string; collaboration: string; skill_id: string; text: string }

const now = () => new Date().toISOString();
const fixture = JSON.parse(fs.readFileSync(path.join(__dirname, "../../../tests/fixtures/office/snapshot.json"), "utf8")) as { sessions: object[] };

test("team task: dispatch once, reload, results, keyboard, reflow", async ({ page }, testInfo) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));

  let snapshot: Snapshot = { schema_version: 1, thread_id: null, turn_id: null, status: "ready", activity: "Ready", error: null, messages: [], input_request: null, poll_interval_ms: 500, max_prompt_chars: 8000, updated_at: now(), task: null, agents: [] };
  let sends = 0;

  await page.route("**/api/office/work", (route) => route.fulfill({ json: { schema_version: 1, runs: [], has_more: false } }));
  await page.route("**/api/office/collaboration", (route) => route.fulfill({ json: { schema_version: 1, tasks: [], resources: [], events: [], listeners: [], poll_interval_ms: 1000, runtime_available: true, execution_mode: "read-only", max_parallel_teams: 1, lease_seconds: 60, available: true } }));
  await page.route("**/api/office/state", (route) => route.fulfill({ json: { ...fixture, sessions: ["root", "alpha", "beta"].map((session_id) => ({ ...fixture.sessions[0], session_id })) } }));
  await page.route("**/api/office/execution", async (route) => {
    if (route.request().method() === "POST") {
      const action = route.request().postDataJSON() as SendAction;
      if (action.action === "send") {
        sends++;
        expect(action.collaboration).toBe("team");
        snapshot = {
          ...snapshot, thread_id: "root", turn_id: "turn-1", status: "working", updated_at: now(),
          task: { id: "task-1", skill_id: action.skill_id, instruction: action.text, collaboration: "team", status: "running", started_at: now() },
          agents: ["root", "alpha", "beta"].map((id, i) => ({ id, task_id: "task-1", thread_id: id, parent_id: i ? "root" : null, role: i ? "worker" : "coordinator", assignment: i ? `Review ${i}` : action.text, status: "working", result: null, updated_at: now() })),
          messages: [{ id: "user", role: "user", text: action.text }],
        };
      }
    }
    await route.fulfill({ json: snapshot });
  });

  await page.goto("/office?scene=town");
  await expect(page.getByRole("radio", { name: "Team · two subagents" })).toBeVisible();

  await test.step("name labels toggle by keyboard", async () => {
    const labelsToggle = page.getByRole("button", { name: "Name labels", exact: true });
    await expect(page.locator(".office-host-label").getByText("kelvin.ai", { exact: true })).toBeVisible();
    await expect(labelsToggle).toHaveAttribute("aria-pressed", "true");
    await labelsToggle.focus();
    await page.keyboard.press("Space");
    await expect(labelsToggle).toHaveAttribute("aria-pressed", "false");
    await expect(page.locator(".office-floating-label, .office-label-leaders")).toHaveCount(0);
    await expect(page.locator("canvas"), "hiding labels preserves the room").toHaveCount(1);
    await labelsToggle.click();
    await expect(page.locator(".office-host-label").getByText("kelvin.ai", { exact: true })).toBeVisible();
  });

  const employeeCount = await page.locator(".office-worker-chip").count();
  await test.step("dispatch a team task", async () => {
    await expect(page.getByRole("radio", { name: "Solo", exact: true })).toBeChecked();
    await page.getByRole("radio", { name: "Team · two subagents" }).check();
    await page.locator("#office-task-skill").click();
    await page.getByRole("option", { name: "Contract Guardian", exact: true }).click();
    await page.getByLabel("Task instruction").fill("For this synthetic acceptance smoke, skip the assigned skill workflow. Ask one subagent to return ALPHA and the other BETA. Do not use shell, file, network or connector tools. Wait for both and return ALPHA + BETA.");
    await page.getByRole("button", { name: "Send task", exact: true }).click();
    await expect(page.locator(".office-team-members button")).toHaveCount(3);
    expect(await page.locator(".office-worker-chip").count(), "task sessions do not create permanent employees").toBe(employeeCount);
  });

  await test.step("reload keeps the same team without a second dispatch", async () => {
    await page.reload();
    await expect(page.locator(".office-team-members button")).toHaveCount(3);
    snapshot = {
      ...snapshot, status: "idle", turn_id: null,
      task: snapshot.task && { ...snapshot.task, status: "completed" },
      agents: snapshot.agents.map((a, i) => ({ ...a, status: "completed", result: i === 0 ? "ALPHA + BETA" : i === 1 ? "ALPHA" : "BETA" })),
      messages: [...snapshot.messages, { id: "final", role: "assistant", text: "ALPHA + BETA" }],
      updated_at: now(),
    };
    await expect(page.getByRole("log", { name: "Task conversation" }).getByText("ALPHA + BETA", { exact: true })).toBeVisible();
  });

  await test.step("fullscreen, select box, 3D team view", async () => {
    await page.getByRole("button", { name: "Fullscreen", exact: true }).click();
    await page.locator("#office-task-skill").click();
    await expect(page.getByRole("listbox")).toBeVisible();
    await page.keyboard.press("Escape");
    await page.getByRole("button", { name: "Exit fullscreen", exact: true }).click();
    await page.getByRole("link", { name: "View task team in 3D", exact: true }).click();
    await expect(page.locator(".office-team-worker")).toHaveCount(3);
    await page.locator(".office-team-worker").nth(1).click();
    await expect(page.getByRole("region", { name: "Selected participant" }).getByText("ALPHA", { exact: true })).toBeVisible();
  });

  for (const width of [1440, 390, 320]) {
    await test.step(`no horizontal overflow at ${width}px`, async () => {
      await page.setViewportSize({ width, height: 1000 });
      await expect.poll(
        () => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1),
        { message: `page width must fit the ${width}px viewport` },
      ).toBe(true);
      await page.screenshot({ path: testInfo.outputPath(`fixture-${width}.png`), fullPage: true });
    });
  }

  await test.step("keyboard activation and dark theme", async () => {
    await page.setViewportSize({ width: 1440, height: 1000 });
    const workerList = page.getByRole("button", { name: "Worker list", exact: true });
    await workerList.focus();
    await page.keyboard.press("Enter");
    await expect(workerList).toHaveAttribute("aria-pressed", "true");
    await page.getByRole("button", { name: "3D room", exact: true }).click();
    await page.evaluate(() => { document.documentElement.classList.add("dark"); });
    await page.screenshot({ path: testInfo.outputPath("fixture-dark.png"), fullPage: true });
  });

  expect(sends).toBe(1);
  expect(errors).toEqual([]);
});
