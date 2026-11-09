import Link from "next/link";
import ActionButton from "@/components/admin/ActionButton";
import KdpCsvUpload from "@/components/admin/KdpCsvUpload";
import { Card, PageTitle, fmtDate } from "@/components/admin/ui";
import { serverApi } from "@/lib/api";
import type { SalesResponse, WeeklyReport } from "@/lib/types";

const PERIODS = [7, 30, 90, 365];

function money(value: number, currency: string): string {
  try {
    return new Intl.NumberFormat("en-IN", { style: "currency", currency }).format(value);
  } catch {
    return `${value.toFixed(2)} ${currency}`; // unknown currency code
  }
}

const th = "px-2 py-1 text-left font-semibold whitespace-nowrap";
const td = "px-2 py-1 whitespace-nowrap";

export default async function SalesPage({ searchParams }: { searchParams: Promise<{ days?: string }> }) {
  const { days: raw } = await searchParams;
  const days = PERIODS.includes(Number(raw)) ? Number(raw) : 90;
  const [s, report] = await Promise.all([serverApi<SalesResponse>(`/api/admin/sales?days=${days}`), serverApi<WeeklyReport>("/api/admin/reports/weekly")]);
  return (
    <>
      <PageTitle
        actions={
          <nav aria-label="Period" className="flex gap-1">
            {PERIODS.map((d) => (
              <Link key={d} href={`/sales?days=${d}`} aria-current={d === days ? "page" : undefined} className={`rounded-lg px-2 py-1 text-sm font-semibold ${d === days ? "bg-ink text-white" : "bg-white ring-1 ring-slate-200"}`}>
                {d} days
              </Link>
            ))}
          </nav>
        }
      >
        Sales
      </PageTitle>
      <p className="mb-4 text-sm text-slate-600">
        {s.start} to {s.end}
      </p>
      <div className="mb-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {s.by_platform.map((p) => (
          <Card key={`${p.platform}-${p.currency}`} title={`${p.platform === "kdp" ? "KDP" : "Etsy"} · ${p.currency}`}>
            <p className="text-3xl font-bold">{money(p.revenue, p.currency)}</p>
            <p className="text-sm text-slate-600">{p.units} units</p>
          </Card>
        ))}
        {!s.by_platform.length && <p className="text-slate-500 sm:col-span-2">No sales in this period yet.</p>}
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="Import sales">
          <h3 className="text-sm font-bold">Etsy</h3>
          {s.etsy_configured ? (
            <ActionButton path="/api/admin/sales/etsy-sync" label="Sync Etsy now" variant="ghost" success="Sync started: refresh in a minute." />
          ) : (
            <p className="text-sm text-slate-500">Etsy keys are not set, so syncing is off (see docs/API_KEYS.md).</p>
          )}
          <p className="mt-1 text-xs text-slate-500">Last Etsy import: {fmtDate(s.last_etsy_import)}</p>
          <h3 className="mt-4 text-sm font-bold">KDP</h3>
          <KdpCsvUpload />
          <p className="mt-1 text-xs text-slate-500">Last KDP import: {fmtDate(s.last_kdp_import)}</p>
        </Card>
        <Card title="By book" className="min-w-0 lg:col-span-2">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-slate-200">
                <tr><th className={th}>Book</th><th className={th}>Units</th><th className={th}>Revenue</th></tr>
              </thead>
              <tbody>
                {s.by_book.map((b) => (
                  <tr key={`${b.book_id}-${b.currency}`} className="border-b border-slate-100">
                    <td className={td}>{b.book_id ? <Link href={`/books/${b.book_id}`} className="text-sky-800 underline">{b.title}</Link> : <span className="text-slate-500">{b.title}</span>}</td>
                    <td className={td}>{b.units}</td>
                    <td className={td}>{money(b.revenue, b.currency)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!s.by_book.length && <p className="mt-2 text-sm text-slate-500">Nothing sold in this period.</p>}
          </div>
        </Card>
        <Card title={`Recent sales (${s.rows.length}${s.rows.length >= 300 ? ", newest 300" : ""})`} className="min-w-0 lg:col-span-3">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-slate-200">
                <tr>
                  <th className={th}>Day</th><th className={th}>Platform</th><th className={th}>Title</th><th className={th}>Marketplace</th><th className={th}>Units</th><th className={th}>Revenue</th>
                </tr>
              </thead>
              <tbody>
                {s.rows.map((r) => (
                  <tr key={r.id} className="border-b border-slate-100">
                    <td className={td}>{r.sold_on}</td>
                    <td className={td}>{r.platform === "kdp" ? "KDP" : "Etsy"}</td>
                    <td className={td}>{r.book_id ? <Link href={`/books/${r.book_id}`} className="text-sky-800 underline">{r.title}</Link> : r.title}</td>
                    <td className={td}>{r.marketplace || "—"}</td>
                    <td className={td}>{r.units}</td>
                    <td className={td}>{money(r.revenue, r.currency)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!s.rows.length && <p className="mt-2 text-sm text-slate-500">No sales rows yet. Sync Etsy or upload a KDP report.</p>}
          </div>
        </Card>
        <Card title="Weekly report" className="min-w-0 lg:col-span-3" actions={<ActionButton path="/api/admin/reports/weekly/send" label="Send now" variant="ghost" success="Queued: goes to Telegram and email." />}>
          <p className="mb-2 text-sm text-slate-600">Preview of the report that is sent every week (Telegram + email).</p>
          <pre className="max-h-96 overflow-auto rounded-lg bg-slate-50 p-3 text-xs whitespace-pre-wrap">{report.text}</pre>
        </Card>
      </div>
    </>
  );
}
