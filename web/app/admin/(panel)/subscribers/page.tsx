import { Badge, Card, PageTitle, fileUrl, fmtDate } from "@/components/admin/ui";
import { serverApi } from "@/lib/api";

type Data = {
  counts: Record<string, number>;
  free_printable: { key: string; title: string; pages: number } | null;
  subscribers: { id: number; email: string; status: string; source: string; created_at: string; confirmed_at: string | null }[];
};

export default async function SubscribersPage() {
  const d = await serverApi<Data>("/api/admin/subscribers");
  return (
    <>
      <PageTitle
        actions={
          <a href="/api/admin/subscribers.csv" className="rounded-lg bg-ink px-3 py-1.5 text-sm font-semibold text-white">
            ⬇ Export confirmed (CSV)
          </a>
        }
      >
        Subscribers
      </PageTitle>
      <div className="mb-4 grid gap-4 md:grid-cols-2">
        <Card title="Counts">
          <p className="text-sm">
            Confirmed <b>{d.counts.confirmed ?? 0}</b> · pending {d.counts.pending ?? 0} · unsubscribed {d.counts.unsubscribed ?? 0}
          </p>
          <p className="mt-1 text-xs text-slate-500">Only confirmed (double opt-in) addresses are exported.</p>
        </Card>
        <Card title="Free printable">
          {d.free_printable ? (
            <p className="text-sm">
              {d.free_printable.title} ({d.free_printable.pages} pages) ·{" "}
              <a className="text-sky-800 underline" href={fileUrl(d.free_printable.key)}>
                PDF
              </a>
            </p>
          ) : (
            <p className="text-sm text-slate-600">Not set. Open a book and click “Use as free printable”.</p>
          )}
        </Card>
      </div>
      <Card>
        <table className="w-full text-left text-sm">
          <thead className="text-slate-500">
            <tr>
              <th className="py-1">Email</th>
              <th>Status</th>
              <th>Signed up</th>
              <th>Confirmed</th>
            </tr>
          </thead>
          <tbody>
            {d.subscribers.map((s) => (
              <tr key={s.id} className="border-t border-slate-100">
                <td className="py-1">{s.email}</td>
                <td>
                  <Badge value={s.status} />
                </td>
                <td>{fmtDate(s.created_at)}</td>
                <td>{fmtDate(s.confirmed_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!d.subscribers.length && <p className="text-sm text-slate-500">No sign-ups yet.</p>}
      </Card>
    </>
  );
}
