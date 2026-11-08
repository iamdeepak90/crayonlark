import Link from "next/link";
import ActionButton from "@/components/admin/ActionButton";
import ManualKdpSteps from "@/components/admin/ManualKdpSteps";
import { Badge, Card, PageTitle, fileUrl } from "@/components/admin/ui";
import { serverApi } from "@/lib/api";
import type { KdpSlots, PackRow } from "@/lib/types";

export default async function PacksPage() {
  const { slots, packs } = await serverApi<{ slots: KdpSlots; packs: PackRow[] }>("/api/admin/packs");
  return (
    <>
      <PageTitle>KDP upload packs</PageTitle>
      <Card title={`This week (from ${slots.week_start}, Sunday UTC)`} className="mb-4">
        <p className="text-sm">
          Paperback slots left: <b>{slots.paperback_left}</b> of {slots.paperback_limit} · Hardcover slots left: <b>{slots.hardcover_left}</b> of {slots.hardcover_limit}
        </p>
        <p className="mt-1 text-xs text-slate-500">
          Next weeks:{" "}
          {slots.upcoming.map((w) => `${w.week_start} (${w.paperback} pb, ${w.hardcover} hc)`).join(" · ")}. Upload by hand on KDP only inside a book&apos;s slot week.
        </p>
      </Card>
      {!packs.length && <Card>No packs yet. A pack is built when you approve a book&apos;s listings.</Card>}
      <div className="space-y-4">
        {packs.map((p) => (
          <Card
            key={p.id}
            title={
              <Link href={`/books/${p.id}`} className="hover:underline">
                {p.title}
              </Link>
            }
            actions={<Badge value={p.status} />}
          >
            <div className="grid gap-4 md:grid-cols-3">
              <div className="text-sm">
                <p>
                  Slot week: <b>{p.kdp_week_start ?? "assigning…"}</b>
                </p>
                <p>
                  {p.format}, {p.page_count} pages
                </p>
                {p.kdp_asin && <p>ASIN {p.kdp_asin}</p>}
                {p.amazon_url && (
                  <a className="text-sky-800 underline" href={p.amazon_url} target="_blank" rel="noreferrer">
                    Amazon page
                  </a>
                )}
              </div>
              <ul className="text-sm">
                {p.pack_key ? (
                  <li>
                    <a className="font-semibold text-sky-800 underline" href={fileUrl(p.pack_key)}>
                      ⬇ KDP upload pack (.zip)
                    </a>
                  </li>
                ) : (
                  <li className="text-slate-500">pack is being built…</li>
                )}
                {p.interior_key && (
                  <li>
                    <a className="text-sky-800 underline" href={fileUrl(p.interior_key)}>interior.pdf</a>
                  </li>
                )}
                {p.cover_key && (
                  <li>
                    <a className="text-sky-800 underline" href={fileUrl(p.cover_key)}>cover.pdf</a>
                  </li>
                )}
                {p.etsy.map((e) => (
                  <li key={e.id} className="text-slate-700">
                    Etsy {e.product_kind.replaceAll("_", " ")}:{" "}
                    {Object.entries(e.file_keys).map(([paper, key]) => (
                      <a key={paper} className="mr-2 text-sky-800 underline" href={fileUrl(key)}>
                        {paper}
                      </a>
                    ))}
                    {!Object.keys(e.file_keys).length && <span className="text-slate-500">building…</span>}
                  </li>
                ))}
              </ul>
              <div className="flex flex-col items-start gap-2">
                <ManualKdpSteps bookId={p.id} status={p.status} />
                {p.status === "kdp_pack_ready" && <ActionButton path={`/api/admin/books/${p.id}/pack/rebuild`} label="Rebuild pack" variant="ghost" />}
              </div>
            </div>
          </Card>
        ))}
      </div>
    </>
  );
}
