import { CreditCard, House, Car, CircleHelp } from "lucide-react";
import type { Report } from "@/lib/report";
import { myr } from "@/lib/utils";

const labels: Record<string, string> = { credit_card: "Credit card", housing: "Home loan", auto: "Car loan" };
const debtIcons = { credit_card: CreditCard, housing: House, auto: Car };
export function LiabilitiesPanel({ report: r }: { report: Report }) {
  return (
    <div className="grid gap-4 md:grid-cols-3">
      {r.liabilities.accounts.map(debt => {
        const Icon = debtIcons[debt.type as keyof typeof debtIcons] ?? CircleHelp;
        return (
        <article key={debt.key} className="debt-card">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="flex items-center gap-2 font-medium"><Icon size={17} aria-hidden="true" className="text-muted-foreground" />{labels[debt.type] ?? debt.type}</h3>
            <span className={`debt-label ${debt.outstanding_myr === null || debt.stale ? "text-warning" : "text-muted-foreground"}`}>
              {debt.outstanding_myr === null ? "Principal missing" : debt.stale ? "Balance stale" : "Recorded balance"}
            </span>
          </div>
          <p className="num mt-5 text-2xl font-semibold tracking-tight">{debt.outstanding_myr === null ? "Unknown" : myr(debt.outstanding_myr)}</p>
          <p className="mt-2 break-words text-xs text-muted-foreground">{debt.key.replaceAll("_", " ")}</p>
          <dl className="mt-5 space-y-3 text-sm">
            <div className="flex justify-between gap-3"><dt className="text-muted-foreground">Monthly payment</dt><dd className="num">{debt.monthly_myr === null ? "Not recorded" : myr(debt.monthly_myr)}</dd></div>
            {debt.monthly_full_myr !== null && <div className="flex justify-between gap-3"><dt className="text-muted-foreground">Full installment</dt><dd className="num">{myr(debt.monthly_full_myr)}</dd></div>}
            <div className="flex justify-between gap-3"><dt className="text-muted-foreground">Balance observed</dt><dd>{debt.as_of ?? "Not recorded"}</dd></div>
            {debt.type === "credit_card" && <>
              <div className="flex justify-between gap-3"><dt className="text-muted-foreground">Statement due</dt><dd className="num">{debt.statement_due_myr === null ? "Not recorded" : myr(debt.statement_due_myr)}</dd></div>
              <div className="flex justify-between gap-3"><dt className="text-muted-foreground">Payment deadline</dt><dd>{debt.payment_due_date ?? "Not recorded"}</dd></div>
            </>}
          </dl>
          {debt.notes && <details className="mt-5 border-t pt-3 text-xs leading-relaxed text-muted-foreground"><summary className="cursor-pointer">Payment notes</summary><p className="mt-2">{debt.notes}</p></details>}
        </article>
      ); })}
      {!r.liabilities.accounts.length && <p className="text-sm text-muted-foreground">No liabilities recorded. This does not establish that you have no debt.</p>}
    </div>
  );
}
