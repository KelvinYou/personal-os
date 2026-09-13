import { FlowGraphView } from "@/components/flow-graph";
import { SectionCard } from "@/components/shared/section-card";
import { StatusBadge } from "@/components/status-badge";
import { loadFlowGraph } from "@/lib/flows";

// Always re-read: flows.json is a `make flows` artifact, regenerated outside
// this app's knowledge.
export const dynamic = "force-dynamic";

export default async function Page() {
  const graph = await loadFlowGraph();

  if (!graph) {
    return (
      <main className="container max-w-2xl py-16">
        <div className="rounded-xl border border-critical/40 p-6">
          <StatusBadge severity="Critical">flows.json 缺失</StatusBadge>
          <p className="mt-3 text-sm text-muted-foreground">
            这个页面渲染 <code>scripts/flow_graph.py</code> 的输出，不自己抽取。
            在仓库根目录跑 <code>make flows</code> 生成 web/public/flows.json。
          </p>
        </div>
      </main>
    );
  }

  const kindCounts = graph.nodes.reduce<Record<string, number>>((acc, n) => {
    acc[n.kind] = (acc[n.kind] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <main className="container max-w-6xl space-y-8 py-10 md:py-14">
      <header>
        <h1 className="text-xl font-semibold tracking-tight md:text-2xl">
          Flows
        </h1>
        <p className="mt-2 text-xs text-muted-foreground">
          generated {new Date(graph.generated_at).toLocaleString("en-MY")} ·{" "}
          {graph.nodes.length} nodes / {graph.edges.length} edges · 结构部分（Makefile 依赖 /
          脚本读写）全自动派生，分组来自脚本里的 <code>{"# flow: <group>"}</code> 标注 ·
          过期检测见 <code>make doctor</code>
        </p>
      </header>

      <SectionCard
        title="Pipeline graph"
        description={`${kindCounts["make-target"] ?? 0} make targets · ${kindCounts["script"] ?? 0} scripts · ${kindCounts["data-path"] ?? 0} data paths · ${kindCounts["submodule"] ?? 0} submodules — 点节点看详情，拖动/滚轮缩放`}
      >
        <FlowGraphView graph={graph} />
      </SectionCard>

      <footer className="border-t pt-6 text-[11px] leading-relaxed text-muted-foreground">
        本页只渲染 <code>web/public/flows.json</code>；改了 Makefile / 脚本读写路径 /
        提交(<code>{"# flow:"}</code>)标注后跑 <code>make flows</code> 重新生成。
        submodule 之间的关系（repos/ai-stock-analysis、repos/notes 提供的数据）是
        <code>scripts/lib/flows/submodules.py</code> 里手工维护的小清单，不是自动推断的。
      </footer>
    </main>
  );
}
