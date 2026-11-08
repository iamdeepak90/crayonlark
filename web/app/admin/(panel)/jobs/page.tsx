import Link from "next/link";
import ActionButton from "@/components/admin/ActionButton";
import { Badge, PageTitle, fmtDate } from "@/components/admin/ui";
import { serverApi } from "@/lib/api";
import type { Job } from "@/lib/types";

export default async function JobsPage({ searchParams }: { searchParams: Promise<{ status?: string }> }) {
  const { status } = await searchParams;
  const jobs = await serverApi<Job[]>(`/api/admin/jobs${status ? `?status=${status}` : ""}`);
  return (
    <>
      <PageTitle>Job monitor</PageTitle>
      <div className="mb-3 flex gap-2 text-sm">
        {["", "queued", "running", "failed", "succeeded"].map((s) => (
          <Link key={s} href={s ? `/jobs?status=${s}` : "/jobs"} className={`rounded-lg px-2 py-1 font-semibold ${status === s || (!status && !s) ? "bg-ink text-white" : "bg-white"}`}>
            {s || "all"}
          </Link>
        ))}
      </div>
      <div className="overflow-x-auto rounded-2xl bg-white shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase text-slate-500">
            <tr>
              <th className="p-3">Job</th>
              <th className="p-3">Book</th>
              <th className="p-3">Status</th>
              <th className="p-3">Tries</th>
              <th className="p-3">Created</th>
              <th className="p-3">Error</th>
              <th className="p-3" />
            </tr>
          </thead>
          <tbody>
            {jobs.map((j) => (
              <tr key={j.id} className="border-t align-top">
                <td className="p-3 font-mono text-xs">
                  {j.name.replace("crayonlark.", "")}
                  <div className="text-slate-400">{j.queue}</div>
                </td>
                <td className="p-3">{j.book_id ? <Link className="underline" href={`/books/${j.book_id}`}>#{j.book_id}</Link> : "—"}</td>
                <td className="p-3"><Badge value={j.status} /></td>
                <td className="p-3">{j.attempts}</td>
                <td className="p-3 whitespace-nowrap">{fmtDate(j.created_at)}</td>
                <td className="max-w-md p-3">
                  {j.error ? (
                    <details>
                      <summary className="cursor-pointer text-rose-700">{j.error.split("\n")[0].slice(0, 120)}</summary>
                      <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap text-xs">{j.error}</pre>
                    </details>
                  ) : null}
                </td>
                <td className="p-3">{(j.status === "failed" || j.status === "queued") && <ActionButton path={`/api/admin/jobs/${j.id}/retry`} label="Retry" variant="ghost" />}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!jobs.length && <p className="p-4 text-slate-500">No jobs.</p>}
      </div>
    </>
  );
}
