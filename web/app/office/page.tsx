import path from "node:path";
import { loadOfficeSkills } from "@/lib/office-skills";
import type { Metadata } from "next";
import { OfficeWorkspace } from "@/components/office/office-workspace";
import "./office.css";

export const metadata: Metadata = {
  title: "Virtual Office · Personal OS",
  description: "A local 3D office for Codex tasks, native agent teams, and private session observation.",
};

export const dynamic = "force-dynamic";
export default function OfficePage() {
  try { return <OfficeWorkspace roster={loadOfficeSkills(path.resolve(process.cwd(), ".."))} />; }
  catch { return <OfficeWorkspace roster={[]} rosterError="Cannot read the repository skill roster. Check .agents/skills and reload." />; }
}
