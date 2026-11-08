import Link from "next/link";
import { PageTitle, fmtDate } from "@/components/admin/ui";
import { serverApi } from "@/lib/api";

type Entry = { id: number; at: string; actor: string; action: string; entity_type: string; entity_id: string; details: Record<string, unknown> };

export default async function AuditPage({ searchParams }: { searchParams: Promise<{ page?: string }> }) {
  const page = Number((await searchParams).page ?? 0);
  const rows = await serverApi<Entry[]>(`/api/admin/audit?limit=100&offset=${page * 100}`);
  return (
    <>
      <PageTitle>Audit log</PageTitle>
      <div className="overflow-x-auto rounded-2xl bg-white shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase text-slate-500">
            <tr>
              <th className="p-3">When</th>
              <th className="p-3">Who</th>
              <th className="p-3">Action</th>
              <th className="p-3">Entity</th>
              <th className="p-3">Details</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className="border-t align-top">
                <td className="p-3 whitespace-nowrap">{fmtDate(r.at)}</td>
                <td className="p-3">{r.actor}</td>
                <td className="p-3 font-mono text-xs">{r.action}</td>
                <td className="p-3">{r.entity_type === "book" ? <Link className="underline" href={`/books/${r.entity_id}`}>book #{r.entity_id}</Link> : `${r.entity_type} #${r.entity_id}`}</td>
                <td className="max-w-md p-3 font-mono text-xs break-all text-slate-600">{Object.keys(r.details ?? {}).length ? JSON.stringify(r.details) : ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mt-3 flex gap-3 text-sm">
        {page > 0 && <Link className="underline" href={`/audit?page=${page - 1}`}>← newer</Link>}
        {rows.length === 100 && <Link className="underline" href={`/audit?page=${page + 1}`}>older →</Link>}
      </div>
    </>
  );
}
