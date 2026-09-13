import { readFile } from "node:fs/promises";
import path from "node:path";

const REPO_ROOT = path.resolve(process.cwd(), "..");
const FLOWS_JSON = path.join(REPO_ROOT, "web", "public", "flows.json");

export type FlowNodeKind = "make-target" | "script" | "data-path" | "submodule";
export type FlowEdgeKind = "depends-on" | "invokes" | "reads" | "writes" | "provides";

export interface FlowNode {
  id: string;
  label: string;
  kind: FlowNodeKind;
  group?: string | null;
  rank: number;
  meta: Record<string, unknown>;
}

export interface FlowEdge {
  from: string;
  to: string;
  kind: FlowEdgeKind;
}

export interface FlowGraph {
  generated_at: string;
  input_hash: string;
  nodes: FlowNode[];
  edges: FlowEdge[];
}

/**
 * Reads web/public/flows.json — produced by `make flows`
 * (scripts/flow_graph.py), not computed by the web app itself. `make doctor`
 * flags it when it's drifted out of sync with the Makefile/scripts.
 */
export async function loadFlowGraph(): Promise<FlowGraph | null> {
  try {
    const raw = await readFile(FLOWS_JSON, "utf-8");
    return JSON.parse(raw) as FlowGraph;
  } catch {
    return null;
  }
}
