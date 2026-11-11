import Link from "next/link";
import { AlertTriangle, Check, ChevronRight, Circle } from "lucide-react";
import AutopilotCard from "@/components/admin/AutopilotCard";
import { Badge, ButtonLink, PageTitle, StatTile, fmtDay } from "@/components/admin/ui";
import { serverApi } from "@/lib/api";
import type { AutopilotStatus, BookSummary, Dashboard, EtsyReview, KdpCandidates, SetupStatus } from "@/lib/types";

const COLUMNS: { title: string; statuses: string[] }[] = [
  { title: "Being made", statuses: ["idea", "niche_approved", "concepts_ready", "images_generating", "images_qa", "awaiting_image_approval", "cleaning", "building", "listing_draft"] },
  { title: "Approve for Etsy", statuses: ["awaiting_etsy_approval"] },
  { title: "Etsy queue", statuses: ["etsy_queued"] },
  { title: "On Etsy", statuses: ["on_etsy"] },
  { title: "KDP", statuses: ["kdp_pack_ready", "kdp_uploaded", "proof_ordered", "live"] },
];

type Todo = { key: string; label: string; detail: string; href: string };

/** The owner's whole job: finish setup once, approve books for Etsy, pick some for KDP, upload. */
export default async function TodayPage() {
  const [books, dash, etsy, kdp, auto, setup] = await Promise.all([
    serverApi<BookSummary[]>("/api/admin/books"),
    serverApi<Dashboard>("/api/admin/dashboard"),
    serverApi<EtsyReview>("/api/admin/etsy/review"),
    serverApi<KdpCandidates>("/api/admin/kdp/candidates"),
    serverApi<AutopilotStatus>("/api/admin/autopilot"),
    serverApi<SetupStatus>("/api/admin/setup"),
  ]);
  const k = dash.kdp_slots;
  const b = dash.budget;
  const packs = books.filter((bk) => bk.status === "kdp_pack_ready");

  const todos: Todo[] = [
    ...(etsy.waiting.length
      ? [{ key: "etsy", label: "Approve for Etsy", detail: `${etsy.waiting.length} finished book(s)`, href: "/etsy" }]
      : []),
    ...(kdp.candidates.length && k.paperback_left
      ? [{ key: "kdp", label: "Pick for KDP", detail: `${k.paperback_left} slot(s) free this week · best: ${kdp.candidates[0].title}`, href: "/kdp" }]
      : []),
    ...packs.map((bk) => ({ key: `pack-${bk.id}`, label: "Upload to KDP", detail: bk.title, href: "/packs" })),
    ...(!dash.autopilot
      ? books
          .filter((bk) => bk.status === "awaiting_image_approval")
          .map((bk) => ({ key: `img-${bk.id}`, label: "Approve images", detail: bk.title, href: `/books/${bk.id}/images` }))
      : []),
  ];

  return (
    <>
      <PageTitle description="You approve finished books for Etsy and pick the best for KDP. Everything else runs by itself.">Today</PageTitle>

      {!setup.ready && (
        <section aria-labelledby="setup-h" className="mb-6 rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-100">
          <h2 id="setup-h" className="font-semibold">Finish setup (once)</h2>
          <ul className="mt-2 flex flex-col gap-1">
            {setup.items.map((i) => (
              <li key={i.id} className="flex items-center gap-2">
                {i.done ? <Check className="size-4 shrink-0" aria-label="done" /> : <Circle className="size-4 shrink-0" aria-label="to do" />}
                <span className={i.done ? "line-through opacity-70" : ""}>{i.label}</span>
              </li>
            ))}
          </ul>
          <div className="mt-3">
            <ButtonLink href="/settings">Open Settings</ButtonLink>
          </div>
        </section>
      )}

      <section aria-labelledby="todo-h">
        <h2 id="todo-h" className="text-sm font-semibold tracking-tight">
          Waiting for you
        </h2>
        {todos.length ? (
          <ul className="mt-3 divide-y overflow-hidden rounded-lg border bg-card shadow-xs">
            {todos.map((t) => (
              <li key={t.key}>
                <Link href={t.href} className="flex items-center gap-3 px-4 py-3 text-sm transition-colors hover:bg-accent/50">
                  <span className="size-1.5 shrink-0 rounded-lg bg-amber-500" aria-hidden="true" />
                  <span className="font-medium">{t.label}</span>
                  <span className="min-w-0 truncate text-muted-foreground">{t.detail}</span>
                  <ChevronRight className="ml-auto size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-3 rounded-lg border border-dashed px-4 py-6 text-center text-sm text-muted-foreground">Nothing to do. New books show up here when they are ready.</p>
        )}
      </section>

      <div className="mt-6">
        <AutopilotCard status={auto} />
      </div>

      {etsy.low_stock && etsy.connected && (
        <p className="mt-3 flex items-start gap-2 text-sm text-amber-900 dark:text-amber-200">
          <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          Only {etsy.days_of_stock} day(s) of books in the Etsy queue. Approve the waiting ones to keep one going live every day.
        </p>
      )}

      <div className="mt-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatTile label="Etsy queue" value={etsy.queue.length} sub={`${etsy.live_today}/${etsy.daily.per_day} live today${etsy.connected ? "" : " · Etsy not connected"}`} href="/etsy#queue" />
        <StatTile label="On Etsy" value={dash.books_by_status.on_etsy ?? 0} sub="ranked for KDP" href="/kdp" />
        <StatTile label="KDP slots this week" value={`${k.paperback_left} / ${k.paperback_limit}`} sub={`next free ${fmtDay(kdp.next_free_week)} · ~${kdp.per_month}/month`} href="/packs" />
        <StatTile label="AI spend this month" value={`₹${b.spent_inr.toFixed(0)}`} sub={`of ₹${b.cap_inr.toFixed(0)}${dash.failed_jobs ? ` · ${dash.failed_jobs} failed job(s)` : ""}`} href="/costs" tone={b.state === "stop" ? "bad" : undefined} />
      </div>

      <details className="mt-8">
        <summary className="cursor-pointer select-none text-sm font-semibold tracking-tight">Every book ({books.length})</summary>
        <div className="mt-3 grid items-start gap-3 md:grid-cols-3 xl:grid-cols-5">
          {COLUMNS.map((col) => {
            const items = books.filter((bk) => col.statuses.includes(bk.status));
            return (
              <section key={col.title} className="rounded-lg bg-secondary/60 p-2" aria-label={col.title}>
                <h3 className="flex items-center justify-between px-1.5 pb-2 pt-1 text-xs font-medium text-muted-foreground">
                  {col.title}
                  <span className="tabular-nums">{items.length}</span>
                </h3>
                <ul className="space-y-2">
                  {items.map((bk) => (
                    <li key={bk.id} className="rounded-lg border bg-card p-3 shadow-xs">
                      <Link href={`/books/${bk.id}`} className="block text-sm font-medium leading-snug hover:underline">
                        {bk.title}
                      </Link>
                      <div className="mt-2 flex flex-wrap items-center gap-1">
                        <Badge value={bk.status} />
                        {bk.kdp_skipped && <Badge value="not for KDP" tone="neutral" />}
                      </div>
                    </li>
                  ))}
                  {!items.length && <li className="px-1.5 pb-1 text-xs text-muted-foreground">Empty</li>}
                </ul>
              </section>
            );
          })}
        </div>
      </details>
    </>
  );
}
