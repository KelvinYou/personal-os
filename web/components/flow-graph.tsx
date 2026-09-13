"use client";

import { useMemo, useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  type Edge,
  type Node,
} from "reactflow";
import "reactflow/dist/style.css";
import type { FlowEdge, FlowGraph, FlowNode } from "@/lib/flows";

const KIND_LABEL: Record<FlowNode["kind"], string> = {
  "make-target": "make",
  script: "script",
  "data-path": "data",
  submodule: "submodule",
};

const KIND_SHAPE: Record<FlowNode["kind"], string> = {
  "make-target": "rounded-md",
  script: "rounded-md",
  "data-path": "rounded-full",
  submodule: "rounded-md border-2 border-dashed",
};

// Categorical series slots reused from the dashboard's chart palette
// (globals.css) — stable across light/dark since they're CSS vars.
const GROUP_COLORS = ["var(--series-1)", "var(--series-2)", "var(--series-3)", "var(--series-4)"];

function colorForGroup(group: string | null | undefined, groupIndex: Map<string, number>): string {
  if (!group) return "hsl(var(--muted-foreground))";
  const idx = groupIndex.get(group) ?? 0;
  return GROUP_COLORS[idx % GROUP_COLORS.length];
}

const RANK_COL_WIDTH = 260;
const ROW_HEIGHT = 64;

function layout(nodes: FlowNode[]): Node[] {
  const byRank = new Map<number, FlowNode[]>();
  for (const n of nodes) {
    const bucket = byRank.get(n.rank) ?? [];
    bucket.push(n);
    byRank.set(n.rank, bucket);
  }
  const groupIndex = new Map<string, number>();
  for (const n of nodes) {
    if (n.group && !groupIndex.has(n.group)) groupIndex.set(n.group, groupIndex.size);
  }

  const out: Node[] = [];
  for (const [rank, bucket] of byRank) {
    bucket.forEach((n, row) => {
      const color = colorForGroup(n.group, groupIndex);
      out.push({
        id: n.id,
        position: { x: rank * RANK_COL_WIDTH, y: row * ROW_HEIGHT },
        data: { label: n.label, node: n },
        className: `${KIND_SHAPE[n.kind]} border bg-card px-3 py-2 text-xs text-card-foreground`,
        style: {
          borderColor: color,
          borderWidth: n.kind === "submodule" ? 2 : 1,
        },
      });
    });
  }
  return out;
}

function toEdges(edges: FlowEdge[]): Edge[] {
  return edges.map((e, i) => ({
    id: `${e.from}->${e.to}-${i}`,
    source: e.from,
    target: e.to,
    label: e.kind,
    animated: e.kind === "invokes",
    style: { stroke: "hsl(var(--border))" },
    labelStyle: { fill: "hsl(var(--muted-foreground))", fontSize: 10 },
    labelBgStyle: { fill: "hsl(var(--card))" },
  }));
}

export function FlowGraphView({ graph }: { graph: FlowGraph }) {
  const [selected, setSelected] = useState<FlowNode | null>(null);
  const nodes = useMemo(() => layout(graph.nodes), [graph.nodes]);
  const edges = useMemo(() => toEdges(graph.edges), [graph.edges]);

  const related = useMemo(() => {
    if (!selected) return null;
    const reads = graph.edges.filter((e) => e.from === selected.id && e.kind === "reads");
    const writes = graph.edges.filter((e) => e.from === selected.id && e.kind === "writes");
    const invokedBy = graph.edges.filter((e) => e.to === selected.id && e.kind === "invokes");
    const invokes = graph.edges.filter((e) => e.from === selected.id && e.kind === "invokes");
    return { reads, writes, invokedBy, invokes };
  }, [selected, graph.edges]);

  return (
    <div className="relative h-[70vh] w-full overflow-hidden rounded-xl border">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        proOptions={{ hideAttribution: true }}
        onNodeClick={(_, node) => setSelected((node.data as { node: FlowNode }).node)}
        onPaneClick={() => setSelected(null)}
      >
        <Background />
        <Controls />
        <MiniMap
          nodeColor={() => "hsl(var(--muted-foreground))"}
          maskColor="rgba(0,0,0,0.08)"
          pannable
          zoomable
        />
      </ReactFlow>

      {selected && (
        <div className="absolute right-3 top-3 w-72 rounded-lg border bg-card p-4 text-xs shadow-lg">
          <div className="flex items-center justify-between gap-2">
            <span className="font-mono text-[11px] text-muted-foreground">
              {KIND_LABEL[selected.kind]}
            </span>
            <button
              type="button"
              onClick={() => setSelected(null)}
              className="text-muted-foreground hover:text-foreground"
            >
              ✕
            </button>
          </div>
          <div className="mt-1 break-all font-medium text-foreground">{selected.label}</div>
          {selected.group && (
            <div className="mt-1 text-muted-foreground">flow group: {selected.group}</div>
          )}
          {typeof selected.meta?.summary === "string" && selected.meta.summary && (
            <p className="mt-2 text-muted-foreground">{selected.meta.summary}</p>
          )}
          {related && (
            <div className="mt-3 space-y-1 text-muted-foreground">
              {related.invokedBy.length > 0 && (
                <div>invoked by: {related.invokedBy.map((e) => e.from).join(", ")}</div>
              )}
              {related.invokes.length > 0 && (
                <div>invokes: {related.invokes.map((e) => e.to).join(", ")}</div>
              )}
              {related.reads.length > 0 && (
                <div>reads: {related.reads.map((e) => e.to.replace("path:", "")).join(", ")}</div>
              )}
              {related.writes.length > 0 && (
                <div>writes: {related.writes.map((e) => e.to.replace("path:", "")).join(", ")}</div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
