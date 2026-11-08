import { Activity, CircleCheck, CircleHelp, Coffee, Pause, TriangleAlert } from "lucide-react";
import type { OfficeState } from "@/lib/office-contract";

export const stateLabels: Record<OfficeState, string> = { working: "Working", waiting: "Waiting for you", idle: "Turn ended", completed: "Completed", error: "Failed", unknown: "Status unknown" };
export const stateIcons = { working: Activity, waiting: Pause, idle: Coffee, completed: CircleCheck, error: TriangleAlert, unknown: CircleHelp };
export function OfficeStatus({ state, label }: { state: OfficeState; label?: string }) {
  const Icon = stateIcons[state];
  return <span className={`office-status state-${state}`}><Icon size={12} aria-hidden="true" />{label ?? stateLabels[state]}</span>;
}
