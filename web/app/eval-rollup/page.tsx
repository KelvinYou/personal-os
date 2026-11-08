import { EvalSignalChart } from "@/components/eval-signal-chart";
import { DataState } from "@/components/shared/data-state";
import { SectionCard } from "@/components/shared/section-card";
import { Stat } from "@/components/shared/stat";
import { StatusBadge } from "@/components/status-badge";
import { loadCorrectionRecurrence, loadEvalRollupHistory } from "@/lib/eval-rollup";
import { pct } from "@/lib/utils";

// Always re-read: rollup-*.json changes outside the app's knowledge (make eval-rollup).
export const dynamic = "force-dynamic";

export default async function Page() {
  const [history, corrections] = await Promise.all([loadEvalRollupHistory(), loadCorrectionRecurrence()]);
  const latest = history[history.length - 1];

  const topSignal = latest
    ? Object.entries(latest.signals).sort((a, b) => b[1].share_pct - a[1].share_pct)[0]
    : undefined;

  return (
    <main id="main-content" className="container max-w-5xl space-y-10 py-10 md:py-14">
      <header>
        <h1 className="text-xl font-semibold tracking-tight md:text-2xl">
          Agent Signals
        </h1>
        <p className="mt-2 text-xs text-muted-foreground">
          本地视图，不部署 · 数字全部来自{" "}
          <code>scripts/session_eval.py --rollup-history</code>，此页不重算 ·
          一次 eval 说明不了问题，同一个 signal 在一个月里过半 session 出现才算
          AGENTS.md 的 bug
        </p>
      </header>

      {latest && (
        <section>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Stat label="最新月份" value={latest.month} />
            <Stat label="Session 数" value={latest.session_count} />
            <Stat
              label="未 Review"
              value={`${latest.unreviewed_count}/${latest.session_count}`}
              accent={latest.unreviewed_count > 0 ? "muted" : undefined}
            />
            <Stat
              label="最高频 Signal"
              value={topSignal ? topSignal[0] : "—"}
              hint={topSignal ? pct(topSignal[1].share_pct, 0) : undefined}
              accent={
                topSignal && topSignal[1].share_pct >= latest.bug_share_threshold_pct
                  ? "down"
                  : undefined
              }
            />
          </div>
        </section>
      )}

      <SectionCard
        title="Signal 趋势"
        description="按月的 signal 占比（占当月 session 总数的百分比），只画前 4 个高频 signal"
      >
        <EvalSignalChart history={history} />
      </SectionCard>

      {history.length > 0 && (
        <SectionCard
          title="月度明细"
          description={`超过 ${latest?.bug_share_threshold_pct ?? 50}% 标 Warning —— 不是"这次做得差"，是"AGENTS.md 该改了"`}
        >
          <div className="overflow-x-auto" role="region" aria-label="月度 signal 明细" tabIndex={0}>
            <table className="w-full min-w-[30rem] text-sm [&_td]:whitespace-nowrap [&_th]:whitespace-nowrap">
              <thead>
                <tr className="border-b text-left text-[11px] uppercase tracking-wide text-muted-foreground">
                  <th className="pb-2 pr-3 font-medium">月份</th>
                  <th className="pb-2 pr-3 text-right font-medium">Sessions</th>
                  <th className="pb-2 pr-3 font-medium">Signal</th>
                  <th className="pb-2 text-right font-medium">占比</th>
                </tr>
              </thead>
              <tbody>
                {[...history].reverse().flatMap((r) => {
                  const rows = Object.entries(r.signals).sort(
                    (a, b) => b[1].share_pct - a[1].share_pct,
                  );
                  if (rows.length === 0) {
                    return (
                      <tr key={r.month} className="border-b last:border-0">
                        <td className="py-2 pr-3 text-foreground">{r.month}</td>
                        <td className="num py-2 pr-3 text-right">{r.session_count}</td>
                        <td className="py-2 pr-3 text-muted-foreground" colSpan={2}>
                          无 signal
                        </td>
                      </tr>
                    );
                  }
                  return rows.map(([code, s], i) => (
                    <tr key={`${r.month}-${code}`} className="border-b last:border-0">
                      <td className="py-2 pr-3 text-foreground">{i === 0 ? r.month : ""}</td>
                      <td className="num py-2 pr-3 text-right">
                        {i === 0 ? r.session_count : ""}
                      </td>
                      <td className="py-2 pr-3 text-foreground">{code}</td>
                      <td className="num py-2 text-right">
                        {s.share_pct >= r.bug_share_threshold_pct ? (
                          <StatusBadge severity="Warning">{pct(s.share_pct, 0)}</StatusBadge>
                        ) : (
                          pct(s.share_pct, 0)
                        )}
                      </td>
                    </tr>
                  ));
                })}
              </tbody>
            </table>
          </div>
        </SectionCard>
      )}

      <SectionCard
        title="纠错复发"
        description="来自 reports/corrections/ 每条纠错的 Class 字段。复发 = 之前已经出现过同一 class 的纠错——上一次的修正没挡住。升级强制层级后，这个比例应该下降"
      >
        {corrections === null ? (
          <DataState
            state="error"
            title="纠错记录读取失败"
            description={<>在仓库根目录跑 <code>python3 scripts/session_eval.py --corrections</code> 查看错误。</>}
          />
        ) : corrections.length === 0 ? (
          <DataState
            state="empty"
            title="还没有纠错记录"
            description={<>纠错写入 <code>reports/corrections/pending.md</code> 后会出现在这里。</>}
          />
        ) : (
          <div className="overflow-x-auto" role="region" aria-label="纠错复发明细" tabIndex={0}>
            <table className="w-full min-w-[32rem] text-sm [&_td]:whitespace-nowrap [&_th]:whitespace-nowrap">
              <thead>
                <tr className="border-b text-left text-[11px] uppercase tracking-wide text-muted-foreground">
                  <th className="pb-2 pr-3 font-medium">月份</th>
                  <th className="pb-2 pr-3 text-right font-medium">纠错数</th>
                  <th className="pb-2 pr-3 text-right font-medium">复发</th>
                  <th className="pb-2 pr-3 text-right font-medium">复发率</th>
                  <th className="pb-2 font-medium">复发的 class</th>
                </tr>
              </thead>
              <tbody>
                {[...corrections].reverse().map((r) => {
                  const classes = [...new Set(r.repeat_entries.map((e) => e.class))];
                  return (
                    <tr key={r.month} className="border-b align-top last:border-0">
                      <td className="py-2 pr-3 text-foreground">{r.month}</td>
                      <td className="num py-2 pr-3 text-right">{r.logged}</td>
                      <td className="num py-2 pr-3 text-right">{r.repeats}</td>
                      <td className="num py-2 pr-3 text-right">
                        {r.repeat_rate_pct === null ? "—" : pct(r.repeat_rate_pct, 0)}
                      </td>
                      <td className="py-2 text-foreground">
                        {classes.length ? classes.join(", ") : <span className="text-muted-foreground">无</span>}
                        {r.unclassified > 0 && (
                          <span className="block text-xs text-muted-foreground">{r.unclassified} 条未标 class，复发数偏低</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </SectionCard>

      <footer className="border-t pt-6 text-[11px] leading-relaxed text-muted-foreground">
        <code>judgement</code> / <code>agents_md_change</code> / <code>notes</code>{" "}
        字段永远不在这份汇总里——它们是人工或 /meta-coach 填的评审字段，本页只读
        signals 计数，不代替评审。
      </footer>
    </main>
  );
}
