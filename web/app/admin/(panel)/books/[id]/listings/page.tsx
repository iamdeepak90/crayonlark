import { ArrowRight } from "lucide-react";
import Link from "next/link";
import ActionButton from "@/components/admin/ActionButton";
import ListingEditor from "@/components/admin/ListingEditor";
import { Badge, ButtonLink, Card, PageTitle } from "@/components/admin/ui";
import { serverApi } from "@/lib/api";
import type { ListingsResponse } from "@/lib/types";

const CAN_REDRAFT = ["listing_draft", "awaiting_etsy_approval"];

export default async function ListingsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const data = await serverApi<ListingsResponse>(`/api/admin/books/${id}/listings`);
  const status = data.book.status;
  const kdp = data.listings.filter((l) => l.platform === "kdp");
  const etsy = data.listings.filter((l) => l.platform === "etsy" && l.status !== "rejected");
  return (
    <>
      <PageTitle
        description="Edit the text here. Approving happens on the two approval screens: the Etsy listing on Approve for Etsy, the KDP listing on Pick for KDP."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Badge value={status} />
            {CAN_REDRAFT.includes(status) && (
              <ActionButton path={`/api/admin/books/${id}/listings/redraft`} label="Write new text" variant="outline" confirm="Throw away this text and ask the listing agent again?" success="The listing agent is writing new text" />
            )}
            {status === "awaiting_etsy_approval" && (
              <ButtonLink href="/etsy">
                Approve for Etsy <ArrowRight aria-hidden="true" />
              </ButtonLink>
            )}
            {status === "on_etsy" && (
              <ButtonLink href="/kdp">
                Pick for KDP <ArrowRight aria-hidden="true" />
              </ButtonLink>
            )}
          </div>
        }
      >
        <Link href={`/books/${id}`} className="text-muted-foreground hover:underline">
          {data.book.title}
        </Link>{" "}
        · Listings
      </PageTitle>
      {!data.listings.length && <Card>The listing agent is writing the text. Refresh in a moment.</Card>}
      <div className="grid gap-4 xl:grid-cols-2">
        {etsy.map((l) => (
          <Card key={l.id} title="Etsy (printable PDF)">
            <ListingEditor item={l} />
          </Card>
        ))}
        {kdp.map((l) => (
          <Card key={l.id} title="Amazon KDP (paperback, only if picked)">
            <ListingEditor item={l} />
          </Card>
        ))}
      </div>
    </>
  );
}
