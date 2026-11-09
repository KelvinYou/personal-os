import path from "node:path";
import { loadOfficeSkills } from "@/lib/office-skills";
import type { Metadata } from "next";
import { OfficeWorkspace } from "@/components/office/office-workspace";
import { TownWorkspace } from "@/components/office/town-workspace";
import { loadReport, type LoadResult, type Report } from "@/lib/report";
import { financeEntrance, taskEntrance } from "@/lib/office-finance";
import { workbenchCommand } from "@/lib/finance-workbench-server";import sampleReport from "../../../tests/fixtures/report_contract.json";
import "./office.css";
import "./finance-department.css";
import "./content-lab.css";

export const metadata: Metadata = {
  title: "Town · Lab, Finance & Content Lab · Personal OS",
  description: "One flat town for agent attention, financial review and content research, production and results.",
};

export const dynamic = "force-dynamic";

async function financeFor(demo: boolean) {
  // Demo never reads private finance files: the canonical report fixture is synthetic.
  const [finance, workbench] = await Promise.all([
    demo ? Promise.resolve<LoadResult>({ ok: true, report: sampleReport as Report }) : loadReport(),
    workbenchCommand("read", undefined, demo).catch(() => null),
  ]);
  return { finance, financeNotice: taskEntrance(workbench, financeEntrance(finance)) };
}

// Default: the town (Lab radar + Finance). `?scene=town` keeps the frozen classic garden town
// (docs/design/office-attention-radar.md §7).
export default async function OfficePage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const params = await searchParams;
  if (params.scene === "town") {
    try { return <TownWorkspace roster={loadOfficeSkills(path.resolve(process.cwd(), ".."))} />; }
    catch { return <TownWorkspace roster={[]} rosterError="Cannot read the repository skill roster. Check .agents/skills and reload." />; }
  }
  const finance = await financeFor(params.mode === "demo");
  try { return <OfficeWorkspace roster={loadOfficeSkills(path.resolve(process.cwd(), ".."))} {...finance} />; }
  catch { return <OfficeWorkspace roster={[]} rosterError="Cannot read the repository skill roster. Check .agents/skills and reload." {...finance} />; }
}
