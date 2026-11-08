import Link from "next/link";
import { Badge, Card, PageTitle } from "@/components/admin/ui";
import { serverApi } from "@/lib/api";
import type { BookSummary, Dashboard } from "@/lib/types";

const COLUMNS: { title: string; statuses: string[] }[] = [
  { title: "Ideas & concepts", statuses: ["idea", "niche_approved", "concepts_ready"] },
  { title: "Images", statuses: ["images_generating", "images_qa", "awaiting_image_approval"] },
  { title: "Build", statuses: ["cleaning", "building", "awaiting_cover_approval"] },
  { title: "Listings", statuses: ["listing_draft", "awaiting_listing_approval"] },
  { title: "KDP", statuses: ["kdp_pack_ready", "kdp_uploaded", "proof_ordered"] },
  { title: "Live", statuses: ["live"] },
];

const NEEDS_ME = new Set(["awaiting_image_approval", "awaiting_cover_approval", "awaiting_listing_approval", "kdp_pack_ready"]);

function nextAction(b: BookSummary): string | null {
  switch (b.status) {
    case "awaiting_image_approval":
      return `/books/${b.id}/images`;
    case "awaiting_cover_approval":
      return `/books/${b.id}/cover`;
    case "awaiting_listing_approval":
    case "listing_draft":
      return `/books/${b.id}/listings`;
    case "kdp_pack_ready":
      return `/packs`;
    default:
      return null;
  }
}

export default async function PipelinePage() {
  const [books, dash] = await Promise.all([serverApi<BookSummary[]>("/api/admin/books"), serverApi<Dashboard>("/api/admin/dashboard")]);
  const k = dash.kdp_slots;
  const b = dash.budget;
  return (
    <>
      <PageTitle actions={<Link href="/books/new" className="rounded-lg bg-ink px-3 py-1.5 text-sm font-semibold text-white">+ New book</Link>}>
        Pipeline
      </PageTitle>
      <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card title="KDP slots this week">
          <p className="text-3xl font-bold">
            {k.paperback_left}
            <span className="text-base font-normal text-slate-500"> / {k.paperback_limit} paperback left</span>
          </p>
          <p className="text-sm text-slate-600">
            {k.hardcover_left} / {k.hardcover_limit} hardcover · resets {new Date(k.resets_at).toUTCString().slice(0, 16)} 00:00 UTC
          </p>
        </Card>
        <Card title="API spend">
          <p className="text-3xl font-bold">
            ₹{b.spent_inr.toFixed(0)}
            <span className="text-base font-normal text-slate-500"> / ₹{b.cap_inr.toFixed(0)}</span>
          </p>
          <div className="mt-2 h-2 rounded bg-slate-100" role="progressbar" aria-valuenow={Math.round(b.ratio * 100)} aria-valuemin={0} aria-valuemax={100}>
            <div className={`h-2 rounded ${b.state === "ok" ? "bg-emerald-500" : b.state === "warn" ? "bg-amber-500" : "bg-rose-600"}`} style={{ width: `${Math.min(100, b.ratio * 100)}%` }} />
          </div>
        </Card>
        <Card title="Niche ideas">
          <p className="text-3xl font-bold">{dash.pending_niches}</p>
          <Link href="/niches" className="text-sm font-semibold text-sky-800 underline">waiting for review</Link>
        </Card>
        <Card title="Failed jobs">
          <p className={`text-3xl font-bold ${dash.failed_jobs ? "text-rose-700" : ""}`}>{dash.failed_jobs}</p>
          <Link href="/jobs?status=failed" className="text-sm font-semibold text-sky-800 underline">open job monitor</Link>
        </Card>
      </div>
      <div className="grid gap-4 md:grid-cols-3 xl:grid-cols-6">
        {COLUMNS.map((col) => {
          const items = books.filter((bk) => col.statuses.includes(bk.status));
          return (
            <section key={col.title} className="rounded-2xl bg-slate-100 p-3" aria-label={col.title}>
              <h2 className="mb-2 text-sm font-bold uppercase tracking-wide text-slate-600">
                {col.title} <span className="text-slate-400">({items.length})</span>
              </h2>
              <ul className="space-y-2">
                {items.map((bk) => {
                  const action = nextAction(bk);
                  return (
                    <li key={bk.id} className={`rounded-xl bg-white p-3 shadow-sm ${NEEDS_ME.has(bk.status) ? "ring-2 ring-sun" : ""}`}>
                      <Link href={`/books/${bk.id}`} className="font-semibold hover:underline">
                        {bk.title}
                      </Link>
                      <div className="mt-1 flex flex-wrap items-center gap-1">
                        <Badge value={bk.status} />
                        {bk.etsy_status !== "none" && <Badge value={bk.etsy_status} />}
                      </div>
                      <p className="mt-1 text-xs text-slate-500">
                        {bk.counts.approved ?? 0} approved · {bk.counts.pending ?? 0} pending
                        {bk.kdp_week_start ? ` · KDP week ${bk.kdp_week_start}` : ""}
                      </p>
                      {action && (
                        <Link href={action} className="mt-2 inline-block text-sm font-semibold text-coral-dark underline">
                          Review →
                        </Link>
                      )}
                    </li>
                  );
                })}
              </ul>
            </section>
          );
        })}
      </div>
    </>
  );
}
