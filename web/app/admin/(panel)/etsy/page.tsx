import { Check } from "lucide-react";
import Link from "next/link";
import ActionButton from "@/components/admin/ActionButton";
import ConnectCard from "@/components/admin/ConnectCard";
import { Badge, Card, PageTitle, fileUrl } from "@/components/admin/ui";
import { serverApi } from "@/lib/api";
import type { EtsyOverview } from "@/lib/types";

export default async function EtsyPage() {
  const data = await serverApi<EtsyOverview>("/api/admin/etsy");
  const ready = data.configured && data.connection.connected;
  return (
    <>
      <PageTitle>Etsy drafts</PageTitle>
      <ConnectCard name="etsy" label="Etsy" configured={data.configured} connection={data.connection}>
        {data.remaining_today !== null && <p className="mt-2 text-xs text-slate-500">API calls left today: {data.remaining_today}</p>}
      </ConnectCard>
      {!data.books.length && <Card>No approved Etsy listings yet. They appear here after you approve a book&apos;s listings.</Card>}
      <div className="space-y-4">
        {data.books.map((b) => {
          const blocked = Object.keys(b.problems).length > 0;
          return (
            <Card
              key={b.id}
              title={
                <Link className="hover:underline" href={`/books/${b.id}/listings`}>
                  {b.title}
                </Link>
              }
              actions={<Badge value={b.etsy_status} />}
            >
              {blocked && (
                <ul role="alert" className="mb-3 rounded-lg bg-amber-50 p-2 text-sm text-amber-900">
                  {Object.entries(b.problems).map(([id, errs]) => (
                    <li key={id}>
                      Listing #{id}: {errs.join("; ")}
                    </li>
                  ))}
                </ul>
              )}
              <div className="space-y-4">
                {b.listings.map((l) => (
                  <div key={l.id} className="rounded-lg border border-slate-200 p-3">
                    <div className="mb-2 flex flex-wrap items-center gap-2 text-sm">
                      <b>{l.product_kind.replaceAll("_", " ")}</b>
                      <span className="truncate text-slate-600">{l.title}</span>
                      <span>${(l.price_cents / 100).toFixed(2)}</span>
                      {l.etsy && <Badge value={l.etsy.state} />}
                      {l.etsy?.url && (
                        <a className="font-medium text-foreground underline-offset-4 underline" href={l.etsy.url} target="_blank" rel="noreferrer">
                          view on Etsy
                        </a>
                      )}
                      {l.etsy?.error && <span className="text-rose-700">{l.etsy.error.slice(0, 160)}</span>}
                    </div>
                    <ul className="flex gap-2 overflow-x-auto">
                      {l.mockups.map((k) => (
                        <li key={k} className="shrink-0">
                          <a href={fileUrl(k)}>
                            {/* eslint-disable-next-line @next/next/no-img-element */}
                            <img src={fileUrl(k)} alt="Listing photo" loading="lazy" className="h-24 rounded border" />
                          </a>
                        </li>
                      ))}
                      {!l.mockups.length && <li className="text-sm text-slate-500">mockups are being built…</li>}
                    </ul>
                  </div>
                ))}
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                <ActionButton path={`/api/admin/books/${b.id}/mockups`} label="Rebuild mockups" variant="outline" />
                {ready && b.etsy_status === "none" && <ActionButton path={`/api/admin/books/${b.id}/etsy/drafts`} label="Create Etsy drafts" />}
                {b.etsy_status === "etsy_drafts_created" && (
                  <>
                    <ActionButton path={`/api/admin/books/${b.id}/etsy/drafts`} label="Retry uploads" variant="outline" />
                    <ActionButton path={`/api/admin/books/${b.id}/etsy/approve-publish`} label="Approve & publish on Etsy" icon={<Check aria-hidden="true" />} variant="success" confirm="Publish these listings on Etsy now? They go live for buyers." />
                  </>
                )}
              </div>
            </Card>
          );
        })}
      </div>
    </>
  );
}
