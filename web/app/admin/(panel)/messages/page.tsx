import { Badge, Card, PageTitle, fmtDate } from "@/components/admin/ui";
import { serverApi } from "@/lib/api";

type Msg = { id: number; name: string; email: string; message: string; spam: boolean; created_at: string };

export default async function MessagesPage() {
  const rows = await serverApi<Msg[]>("/api/admin/messages");
  return (
    <>
      <PageTitle>Contact messages</PageTitle>
      <div className="space-y-3">
        {rows.map((m) => (
          <Card key={m.id}>
            <div className="mb-1 flex flex-wrap items-center gap-2 text-sm">
              <b>{m.name}</b>
              <a className="font-medium text-foreground underline-offset-4 underline" href={`mailto:${m.email}`}>
                {m.email}
              </a>
              <span className="text-slate-500">{fmtDate(m.created_at)}</span>
              {m.spam && <Badge value="spam" />}
            </div>
            <p className="whitespace-pre-wrap text-sm">{m.message}</p>
          </Card>
        ))}
        {!rows.length && <Card>No messages yet.</Card>}
      </div>
    </>
  );
}
