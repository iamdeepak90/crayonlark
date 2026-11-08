import Link from "next/link";
import ActionButton from "@/components/admin/ActionButton";
import ManualKdpSteps from "@/components/admin/ManualKdpSteps";
import { Badge, Card, PageTitle, fileUrl, fmtDate } from "@/components/admin/ui";
import Uploader from "@/components/admin/Uploader";
import { serverApi } from "@/lib/api";
import type { BookDetail } from "@/lib/types";

const AI_FIELDS: [string, string][] = [
  ["ai_interior_images", "Interior images"],
  ["ai_cover_image", "Cover image"],
  ["ai_text", "Text"],
];

export default async function BookPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const b = await serverApi<BookDetail>(`/api/admin/books/${id}`);
  const f = b.fields;
  const pending = b.images.filter((i) => i.approval === "pending").length;
  const canUpload = ["niche_approved", "concepts_ready", "images_generating", "images_qa", "awaiting_image_approval"].includes(b.status);
  return (
    <>
      <PageTitle
        actions={
          <div className="flex flex-wrap gap-2">
            <Badge value={b.status} />
            {b.etsy_status !== "none" && <Badge value={b.etsy_status} />}
          </div>
        }
      >
        {b.title}
      </PageTitle>
      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="Images" className="lg:col-span-2" actions={<Link href={`/books/${b.id}/images`} className="text-sm font-semibold text-sky-800 underline">Open approval grid →</Link>}>
          <p className="mb-3 text-sm text-slate-600">
            {b.images.length} images · {b.approved_count} approved · {pending} pending
          </p>
          {canUpload && <Uploader bookId={b.id} />}
          <ul className="mt-4 grid grid-cols-4 gap-2 sm:grid-cols-6 lg:grid-cols-8">
            {b.images.slice(0, 48).map((i) => (
              <li key={i.id} className={`overflow-hidden rounded-lg border-2 ${i.approval === "approved" ? "border-emerald-500" : i.approval === "rejected" ? "border-rose-400 opacity-50" : "border-slate-200"}`}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={`/api/admin/images/${i.id}/file?variant=thumb`} alt={i.scene_title} loading="lazy" className="aspect-[3/4] w-full bg-white object-contain" />
              </li>
            ))}
          </ul>
        </Card>
        <Card title="Details">
          <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-sm">
            <dt className="text-slate-500">Slug</dt>
            <dd className="truncate">{b.slug}</dd>
            <dt className="text-slate-500">Trim</dt>
            <dd>{b.trim}</dd>
            <dt className="text-slate-500">Pages</dt>
            <dd>{b.page_count || "—"}</dd>
            <dt className="text-slate-500">Series</dt>
            <dd>
              {b.series || "—"} #{b.volume}
            </dd>
            <dt className="text-slate-500">KDP week</dt>
            <dd>{b.kdp_week_start ?? "—"}</dd>
            <dt className="text-slate-500">ASIN</dt>
            <dd>{String(f.kdp_asin ?? "—")}</dd>
          </dl>
          <h3 className="mt-4 text-sm font-bold">AI disclosure</h3>
          <ul className="text-sm">
            {AI_FIELDS.map(([k, label]) => (
              <li key={k}>
                {f[k] ? "🤖" : "✋"} {label}: {f[k] ? "AI-generated" : "not AI"}
              </li>
            ))}
            {f.ai_tools ? <li className="text-slate-600">Tools: {String(f.ai_tools)}</li> : null}
          </ul>
          <h3 className="mt-4 text-sm font-bold">Files</h3>
          <ul className="text-sm">
            {b.interior_key && (
              <li>
                <a className="text-sky-800 underline" href={fileUrl(b.interior_key)}>interior.pdf</a>
              </li>
            )}
            {b.cover_key && (
              <li>
                <a className="text-sky-800 underline" href={fileUrl(b.cover_key)}>cover.pdf</a>
              </li>
            )}
            {b.pack_key && (
              <li>
                <a className="text-sky-800 underline" href={fileUrl(b.pack_key)}>KDP upload pack (.zip)</a>
              </li>
            )}
            {!b.interior_key && !b.cover_key && <li className="text-slate-500">nothing built yet</li>}
          </ul>
        </Card>
        <Card title="Next steps" className="lg:col-span-2">
          <div className="flex flex-wrap gap-2">
            {b.status === "awaiting_image_approval" && <Link className="rounded-lg bg-ink px-3 py-1.5 text-sm font-semibold text-white" href={`/books/${b.id}/images`}>Review images</Link>}
            {b.status === "awaiting_cover_approval" && <Link className="rounded-lg bg-ink px-3 py-1.5 text-sm font-semibold text-white" href={`/books/${b.id}/cover`}>Review cover</Link>}
            {["listing_draft", "awaiting_listing_approval"].includes(b.status) && <Link className="rounded-lg bg-ink px-3 py-1.5 text-sm font-semibold text-white" href={`/books/${b.id}/listings`}>Edit & approve listings</Link>}
            <ManualKdpSteps bookId={b.id} status={b.status} />
            <ActionButton path={`/api/admin/books/${b.id}/status/archive`} label="Archive" variant="ghost" confirm="Archive this book?" />
          </div>
        </Card>
        <Card title="Recent jobs">
          <ul className="space-y-1 text-sm">
            {b.jobs.map((j) => (
              <li key={j.id} className="flex items-center justify-between gap-2">
                <span className="truncate">{j.name.replace("crayonlark.", "")}</span>
                <Badge value={j.status} />
              </li>
            ))}
            {!b.jobs.length && <li className="text-slate-500">none</li>}
          </ul>
          <p className="mt-2 text-xs text-slate-500">Updated {fmtDate(b.updated_at)}</p>
        </Card>
      </div>
    </>
  );
}
