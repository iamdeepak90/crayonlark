import Link from "next/link";
import { Badge, Card, PageTitle, fmtDate } from "@/components/admin/ui";
import { serverApi } from "@/lib/api";
import type { CostCall, CostsResponse } from "@/lib/types";

const BAR: Record<string, string> = { ok: "bg-emerald-500", warn: "bg-amber-500", stop: "bg-rose-600" };
const STATE_TEXT: Record<string, string> = {
  ok: "Within budget.",
  warn: "Over 80 % of the monthly cap: paid calls still run, but keep an eye on it.",
  stop: "Monthly cap reached: paid AI calls are blocked until next month (offline and manual still work).",
};

const inr = (v: number) => `₹${v.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
const usd = (v: number) => `$${v.toFixed(v < 1 ? 4 : 2)}`;

function usage(c: CostCall): string {
  if (c.images) return `${c.images} image${c.images === 1 ? "" : "s"}`;
  if (c.input_tokens || c.output_tokens) return `${(c.input_tokens ?? 0).toLocaleString()} in / ${(c.output_tokens ?? 0).toLocaleString()} out`;
  return "—";
}

const th = "px-2 py-1 text-left font-semibold whitespace-nowrap";
const td = "px-2 py-1 whitespace-nowrap";

export default async function CostsPage() {
  const c = await serverApi<CostsResponse>("/api/admin/costs");
  const pct = Math.min(100, Math.round(c.ratio * 100));
  const maxDay = Math.max(0, ...c.daily.map((d) => d.usd));
  return (
    <>
      <PageTitle>Costs · {c.month}</PageTitle>
      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="This month" className="lg:col-span-2">
          <p className="text-3xl font-bold">
            {inr(c.spent_inr)} <span className="text-base font-normal text-slate-500">of {inr(c.cap_inr)} · {usd(c.spent_usd)}</span>
          </p>
          <div className="mt-3 h-3 w-full overflow-hidden rounded-full bg-slate-100" role="progressbar" aria-label="Budget used" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
            <div className={`h-full ${BAR[c.state] ?? BAR.ok}`} style={{ width: `${pct}%` }} />
          </div>
          <p className="mt-2 text-sm text-slate-600">
            {pct} % used · {STATE_TEXT[c.state]} Rate used: ₹{c.usd_inr_rate} per $1.
          </p>
        </Card>
        <Card title="Daily spend">
          <ul className="space-y-1 text-sm">
            {c.daily.map((d) => (
              <li key={d.day} className="flex items-center gap-2">
                <span className="w-20 shrink-0 text-slate-600">{d.day.slice(5)}</span>
                <span className="h-2 flex-1 rounded bg-slate-100">
                  <span className="block h-2 rounded bg-sky-600" style={{ width: `${maxDay ? (d.usd / maxDay) * 100 : 0}%` }} />
                </span>
                <span className="w-24 shrink-0 text-right">{inr(d.usd * c.usd_inr_rate)}</span>
              </li>
            ))}
            {!c.daily.length && <li className="text-slate-500">No paid calls this month.</li>}
          </ul>
        </Card>
        <Card title="By agent" className="min-w-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-slate-200">
                <tr><th className={th}>Agent</th><th className={th}>Provider</th><th className={th}>Calls</th><th className={th}>Cost</th></tr>
              </thead>
              <tbody>
                {c.by_agent.map((a) => (
                  <tr key={`${a.agent}-${a.provider}`} className="border-b border-slate-100">
                    <td className={td}>{a.agent}</td>
                    <td className={td}>{a.provider}</td>
                    <td className={td}>{a.calls}</td>
                    <td className={td}>{inr(a.usd * c.usd_inr_rate)} <span className="text-slate-500">{usd(a.usd)}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!c.by_agent.length && <p className="mt-2 text-sm text-slate-500">Nothing yet this month.</p>}
          </div>
        </Card>
        <Card title="By book (all time)" className="min-w-0 lg:col-span-2">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-slate-200">
                <tr><th className={th}>Book</th><th className={th}>Calls</th><th className={th}>Cost</th></tr>
              </thead>
              <tbody>
                {c.by_book.map((b) => (
                  <tr key={b.book_id} className="border-b border-slate-100">
                    <td className={td}>
                      <Link href={`/books/${b.book_id}`} className="text-sky-800 underline">{b.title}</Link>
                    </td>
                    <td className={td}>{b.calls}</td>
                    <td className={td}>{inr(b.usd * c.usd_inr_rate)} <span className="text-slate-500">{usd(b.usd)}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!c.by_book.length && <p className="mt-2 text-sm text-slate-500">No book has paid calls yet.</p>}
          </div>
        </Card>
        <Card title="Recent calls (last 100)" className="min-w-0 lg:col-span-3">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-slate-200">
                <tr>
                  <th className={th}>Time</th><th className={th}>Agent</th><th className={th}>Provider / model</th><th className={th}>Kind</th>
                  <th className={th}>Usage</th><th className={th}>₹</th><th className={th}>$</th><th className={th}>Status</th><th className={th}>Book</th>
                </tr>
              </thead>
              <tbody>
                {c.recent.map((r) => (
                  <tr key={r.id} className="border-b border-slate-100">
                    <td className={td}>{fmtDate(r.at)}</td>
                    <td className={td}>{r.agent}</td>
                    <td className={td}>{r.provider} / <code className="text-xs">{r.model}</code></td>
                    <td className={td}>{r.kind}</td>
                    <td className={td}>{usage(r)}</td>
                    <td className={td}>{inr(r.inr)}</td>
                    <td className={td}>{usd(r.usd)}</td>
                    <td className={td}><Badge value={r.status} /></td>
                    <td className={td}>{r.book_id ? <Link href={`/books/${r.book_id}`} className="text-sky-800 underline">#{r.book_id}</Link> : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!c.recent.length && <p className="mt-2 text-sm text-slate-500">No AI calls recorded yet.</p>}
          </div>
        </Card>
      </div>
    </>
  );
}
