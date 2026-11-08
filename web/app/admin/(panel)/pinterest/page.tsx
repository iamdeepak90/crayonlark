import ActionButton from "@/components/admin/ActionButton";
import ConnectCard from "@/components/admin/ConnectCard";
import { Badge, Card, PageTitle, fileUrl, fmtDate } from "@/components/admin/ui";
import { serverApi } from "@/lib/api";
import type { PinItem, PinterestOverview } from "@/lib/types";

function PinRow({ p }: { p: PinItem }) {
  return (
    <li className="flex items-center gap-3 border-b border-slate-100 py-2 text-sm last:border-0">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={fileUrl(p.image_key)} alt="" loading="lazy" className="h-16 w-11 rounded border object-cover" />
      <div className="min-w-0 flex-1">
        <p className="truncate font-semibold">{p.title}</p>
        <p className="truncate text-xs text-slate-500">{p.link}</p>
        {p.error && <p className="truncate text-xs text-rose-700">{p.error}</p>}
      </div>
      <span className="text-xs text-slate-600">{fmtDate(p.posted_at ?? p.scheduled_at)}</span>
      <Badge value={p.status} />
      {p.status === "scheduled" && <ActionButton path={`/api/admin/pins/${p.id}/cancel`} label="Cancel" variant="ghost" />}
      {p.status === "failed" && <ActionButton path={`/api/admin/pins/${p.id}/retry`} label="Retry" variant="ghost" />}
    </li>
  );
}

export default async function PinterestPage() {
  const data = await serverApi<PinterestOverview>("/api/admin/pinterest");
  return (
    <>
      <PageTitle>Pinterest</PageTitle>
      <ConnectCard name="pinterest" label="Pinterest" configured={data.configured} connection={data.connection}>
        {data.connection.connected && (
          <div className="mt-3">
            <ActionButton path="/api/admin/pinterest/boards/sync" label="Sync boards from Pinterest" variant="ghost" />
          </div>
        )}
      </ConnectCard>
      <div className="grid gap-4 lg:grid-cols-3">
        <Card title={`Scheduled (${data.upcoming.length})`} className="lg:col-span-2">
          <p className="mb-2 text-xs text-slate-500">Pins are planned when a book&apos;s Etsy listings go live, 3–5 a day, and posted one at a time every 15 minutes.</p>
          <ul>
            {data.upcoming.map((p) => (
              <PinRow key={p.id} p={p} />
            ))}
            {!data.upcoming.length && <li className="text-sm text-slate-500">nothing scheduled</li>}
          </ul>
        </Card>
        <Card title="Boards">
          <ul className="text-sm">
            {data.boards.map((b) => (
              <li key={b.id} className="flex justify-between py-0.5">
                <span>{b.name}</span>
                <span className="text-xs text-slate-500">{b.pinterest_board_id ? "on Pinterest" : "created on first pin"}</span>
              </li>
            ))}
            {!data.boards.length && <li className="text-slate-500">none yet</li>}
          </ul>
        </Card>
        <Card title="Recently posted / failed" className="lg:col-span-3">
          <ul>
            {data.recent.map((p) => (
              <PinRow key={p.id} p={p} />
            ))}
            {!data.recent.length && <li className="text-sm text-slate-500">none yet</li>}
          </ul>
        </Card>
      </div>
    </>
  );
}
