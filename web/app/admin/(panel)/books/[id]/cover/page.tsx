import Link from "next/link";
import CoverControls from "@/components/admin/CoverControls";
import { Badge, Card, PageTitle, fileUrl, fmtDate } from "@/components/admin/ui";
import { serverApi } from "@/lib/api";
import type { CoversResponse } from "@/lib/types";

export default async function CoverPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const data = await serverApi<CoversResponse>(`/api/admin/books/${id}/covers`);
  const [latest, ...older] = data.covers;
  const status = data.book.status;
  return (
    <>
      <PageTitle actions={<Badge value={status} />}>
        <Link href={`/books/${id}`} className="text-slate-500 hover:underline">
          {data.book.title}
        </Link>{" "}
        · Cover
      </PageTitle>
      {!latest && <Card>No cover yet. It is built automatically after the interior; check Jobs if this takes long.</Card>}
      {latest && (
        <div className="grid gap-4 lg:grid-cols-3">
          <Card title={`Version ${latest.version}`} className="lg:col-span-2" actions={<Badge value={latest.approval} />}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={fileUrl(latest.files.preview)} alt="Full cover wrap: back, spine and front" className="w-full rounded-lg border bg-white" />
            <p className="mt-2 text-xs text-slate-500">
              Back · spine · front. Full wrap {latest.width_in.toFixed(3)} × {latest.height_in.toFixed(3)} in, spine {latest.spine_in.toFixed(3)} in,{" "}
              {data.book.page_count} pages. The white box on the back is kept free for the KDP barcode.
            </p>
          </Card>
          <div className="space-y-4">
            <Card title="Phone size">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={fileUrl(latest.files.phone)} alt="Front cover at phone thumbnail size" className="mx-auto w-40 rounded border shadow" />
              <p className="mt-2 text-xs text-slate-500">Is the title readable at this size?</p>
            </Card>
            <Card title="Decide">
              <CoverControls
                bookId={data.book.id}
                coverId={latest.id}
                pending={status === "awaiting_cover_approval" && latest.approval === "pending"}
                canRebuild={["building", "awaiting_cover_approval"].includes(status)}
                themes={data.themes}
                images={data.approved_images}
              />
              <ul className="mt-4 space-y-1 text-sm">
                <li>
                  <a className="text-sky-800 underline" href={fileUrl(latest.files.pdf)}>cover.pdf</a> (print file)
                </li>
                <li>Theme: {String(latest.options.theme ?? "—")}</li>
                <li>Cover image AI-generated: {latest.ai_generated ? "yes" : "no"}</li>
                <li className="text-slate-500">Built {fmtDate(latest.created_at)}</li>
              </ul>
            </Card>
          </div>
        </div>
      )}
      {older.length > 0 && (
        <Card title="Earlier versions" className="mt-4">
          <ul className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-6">
            {older.map((c) => (
              <li key={c.id} className="text-center text-xs">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={fileUrl(c.files.phone)} alt={`Cover version ${c.version}`} loading="lazy" className="mx-auto w-full rounded border" />
                v{c.version} <Badge value={c.approval} />
              </li>
            ))}
          </ul>
        </Card>
      )}
    </>
  );
}
