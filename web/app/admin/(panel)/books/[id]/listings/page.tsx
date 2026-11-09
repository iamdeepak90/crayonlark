import { Check } from "lucide-react";
import Link from "next/link";
import ActionButton from "@/components/admin/ActionButton";
import ListingEditor from "@/components/admin/ListingEditor";
import { Badge, Card, PageTitle } from "@/components/admin/ui";
import { serverApi } from "@/lib/api";
import type { ListingsResponse } from "@/lib/types";

export default async function ListingsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const data = await serverApi<ListingsResponse>(`/api/admin/books/${id}/listings`);
  const awaiting = data.book.status === "awaiting_listing_approval";
  const blocked = data.listings.filter((l) => Object.keys(l.problems).length > 0).length;
  const kdp = data.listings.filter((l) => l.platform === "kdp");
  const etsy = data.listings.filter((l) => l.platform === "etsy");
  return (
    <>
      <PageTitle
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Badge value={data.book.status} />
            {awaiting && (
              <>
                <ActionButton path={`/api/admin/books/${id}/listings/redraft`} label="Redraft all" variant="outline" confirm="Throw away these drafts and ask the listing agent again?" />
                <ActionButton path={`/api/admin/books/${id}/listings/approve`} label={blocked ? `Fix ${blocked} first` : "Approve all listings"} icon={<Check aria-hidden="true" />} variant="success" />
              </>
            )}
          </div>
        }
      >
        <Link href={`/books/${id}`} className="text-slate-500 hover:underline">
          {data.book.title}
        </Link>{" "}
        · Listings
      </PageTitle>
      {data.book.status === "listing_draft" && <Card className="mb-4">The listing agent is writing drafts. Refresh in a moment.</Card>}
      {!data.listings.length && data.book.status !== "listing_draft" && <Card>No listings yet.</Card>}
      <div className="grid gap-4 xl:grid-cols-2">
        {kdp.map((l) => (
          <Card key={l.id} title="Amazon KDP" className="xl:col-span-2">
            <ListingEditor item={l} />
          </Card>
        ))}
        {etsy.map((l) => (
          <Card
            key={l.id}
            title={`Etsy · ${l.product_kind.replaceAll("_", " ")}`}
            actions={
              awaiting && l.status !== "rejected" ? (
                <ActionButton path={`/api/admin/listings/${l.id}/decision`} body={{ approve: false }} label="Skip this product" variant="outline" />
              ) : undefined
            }
          >
            <ListingEditor item={l} />
          </Card>
        ))}
      </div>
    </>
  );
}
