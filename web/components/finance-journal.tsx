import type { Transaction } from "@/lib/activity";
import { Private } from "@/components/shared/privacy";
import { DataState } from "@/components/shared/data-state";
import { accountLabel } from "@/lib/utils";

export function FinanceJournal({ entries, state }: { entries: Transaction[]; state: "missing" | "partial" }) {
  return <div className="space-y-4">
    <p className="text-sm leading-relaxed text-muted-foreground">Partial activity record. Transactions explain reported events; they do not update balances again. Complete dated cash flows are needed before investment returns can be calculated.</p>
    {!entries.length ? <DataState state="empty" title={state === "missing" ? "No transaction journal yet" : "No transactions recorded"} description="Record confirmed events using the finance activity command. A missing event does not mean zero spending or zero return." /> :
      <div role="region" aria-label="Recorded transactions" tabIndex={0} className="overflow-x-auto">
        <table className="w-full text-sm">
          <caption className="sr-only">Confirmed events in their original currency; coverage is partial</caption>
          <thead><tr className="border-b text-left text-xs text-muted-foreground"><th className="py-3 pr-3 font-medium">Date / event</th><th className="px-3 py-3 font-medium">Account / details</th><th className="py-3 pl-3 text-right font-medium">Amount</th></tr></thead>
          <tbody>{entries.map(entry => <tr key={entry.id} className="border-b align-top last:border-0">
            <th scope="row" className="py-3 pr-3 text-left font-normal"><span className="block whitespace-nowrap">{entry.occurred_on ?? "Date unknown"}</span><span className="block text-xs text-muted-foreground">Recorded {entry.recorded_on}</span><span className="mt-1 block capitalize">{entry.kind}</span></th>
            <td className="min-w-40 px-3 py-3"><span className="block">{accountLabel(entry.account)}{entry.counter_account && ` → ${accountLabel(entry.counter_account)}`}</span><span className="block text-xs leading-relaxed text-muted-foreground"><Private>{entry.description}</Private></span>{entry.symbol && <span className="num mt-1 block text-xs"><Private>{entry.quantity} shares · {entry.symbol}</Private></span>}</td>
            <td className="num whitespace-nowrap py-3 pl-3 text-right"><Private>{entry.currency} {entry.amount.toLocaleString("en", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</Private>{entry.kind === "buy" || entry.kind === "sell" ? <span className="mt-1 block text-xs text-muted-foreground">{entry.fees == null ? "Fees unknown" : <Private>Fees {entry.currency} {entry.fees.toFixed(2)}</Private>}</span> : null}</td>
          </tr>)}</tbody>
        </table>
      </div>}
    <details className="border-t pt-3 text-sm"><summary className="cursor-pointer py-2">Record a transaction</summary><p className="mt-2 text-muted-foreground">Tell the assistant the amount, currency, account, actual date and event type, or use the documented stdin command. Leave unknown dates and fees blank. Holdings remain edited separately.</p><code className="mt-3 block break-all text-xs">.venv/bin/python scripts/finance_activity.py add &lt; event.json</code><p className="mt-2 text-xs text-muted-foreground">Schema and examples: docs/design/finance-overview.md</p></details>
  </div>;
}
