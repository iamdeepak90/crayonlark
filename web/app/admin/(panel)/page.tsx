import Link from "next/link";
import { AlertTriangle, Bell, BookOpen, ChevronRight, Inbox, Lightbulb, Package, Plus, Store, Trophy, Users, Wallet } from "lucide-react";
import AutopilotCard from "@/components/admin/AutopilotCard";
import { Badge, ButtonLink, PageTitle, StatTile, fmtDay } from "@/components/admin/ui";
import { serverApi } from "@/lib/api";
import type { AutopilotStatus, BookSummary, Dashboard, EtsyReview, KdpCandidates } from "@/lib/types";

const COLUMNS: { title: string; statuses: string[] }[] = [
  { title: "Ideas & images", statuses: ["idea", "niche_approved", "concepts_ready", "images_generating", "images_qa", "awaiting_image_approval"] },
  { title: "Building", statuses: ["cleaning", "building", "listing_draft"] },
  { title: "Etsy approval", statuses: ["awaiting_etsy_approval"] },
  { title: "Etsy queue", statuses: ["etsy_queued"] },
  { title: "On Etsy", statuses: ["on_etsy"] },
  { title: "KDP", statuses: ["kdp_pack_ready", "kdp_uploaded", "proof_ordered", "live"] },
];

const NEEDS_ME: Record<string, { label: string; href: (id: number) => string }> = {
  awaiting_image_approval: { label: "Approve images", href: (id) => `/books/${id}/images` },
  awaiting_etsy_approval: { label: "Approve for Etsy", href: () => "/etsy" },
  kdp_pack_ready: { label: "Upload to KDP", href: () => "/packs" },
};

type Todo = { key: string; label: string; detail: string; href: string };

export default async function TodayPage() {
  const [books, dash, etsy, kdp, auto] = await Promise.all([
    serverApi<BookSummary[]>("/api/admin/books"),
    serverApi<Dashboard>("/api/admin/dashboard"),
    serverApi<EtsyReview>("/api/admin/etsy/review"),
    serverApi<KdpCandidates>("/api/admin/kdp/candidates"),
    serverApi<AutopilotStatus>("/api/admin/autopilot"),
  ]);
  const k = dash.kdp_slots;
  const b = dash.budget;
  const pct = Math.round(b.ratio * 100);
  const packsReady = books.filter((bk) => bk.status === "kdp_pack_ready").length;

  const todos: Todo[] = [
    ...books
      .filter((bk) => NEEDS_ME[bk.status])
      .map((bk) => ({ key: `book-${bk.id}`, label: NEEDS_ME[bk.status].label, detail: bk.title, href: NEEDS_ME[bk.status].href(bk.id) })),
    ...(kdp.candidates.length && k.paperback_left
      ? [{ key: "kdp", label: "Pick books for KDP", detail: `${kdp.candidates.length} on Etsy · ${k.paperback_left} slot(s) left this week`, href: "/kdp" }]
      : []),
    ...(dash.pending_niches && !auto.enabled ? [{ key: "niches", label: "Review niche ideas", detail: `${dash.pending_niches} proposed`, href: "/niches" }] : []),
    ...(dash.posts_to_review ? [{ key: "posts", label: "Review blog drafts", detail: `${dash.posts_to_review} waiting`, href: "/blog" }] : []),
  ];

  return (
    <>
      <PageTitle
        description="Two decisions per book: approve it for Etsy, then pick the best sellers for KDP. With the Autopilot on, everything else runs by itself."
        actions={
          <ButtonLink href="/books/new">
            <Plus aria-hidden="true" /> New book
          </ButtonLink>
        }
      >
        Today
      </PageTitle>

      {etsy.low_stock && (
        <p role="alert" className="mb-4 flex items-start gap-2 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200">
          <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          <span>
            Only {etsy.days_of_stock} day(s) of books left in the Etsy queue ({etsy.daily.per_day} goes live per day). Approve waiting books or start new ones;{" "}
            {etsy.in_production} in production.
          </span>
        </p>
      )}

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatTile label="1. Approve for Etsy" icon={<Store />} value={etsy.waiting.length} sub={etsy.waiting.length ? "finished books waiting" : "nothing waiting"} href="/etsy" />
        <StatTile
          label="Etsy queue"
          icon={<Store />}
          value={
            <>
              {etsy.queue.length}
              <span className="text-base font-normal text-muted-foreground"> books</span>
            </>
          }
          sub={`${etsy.days_of_stock} days of stock · ${etsy.live_today}/${etsy.daily.per_day} live today${etsy.connected ? "" : " · Etsy not connected"}`}
          href="/etsy#queue"
          tone={etsy.low_stock ? "bad" : undefined}
        />
        <StatTile
          label="2. Pick for KDP"
          icon={<Trophy />}
          value={kdp.candidates.length}
          sub={`on Etsy, ranked by results · next free week ${fmtDay(kdp.next_free_week)}`}
          href="/kdp"
        />
        <StatTile
          label="KDP slots this week"
          icon={<Package />}
          value={
            <>
              {k.paperback_left}
              <span className="text-base font-normal text-muted-foreground"> / {k.paperback_limit}</span>
            </>
          }
          sub={`${packsReady} pack(s) to upload · about ${kdp.per_month} paperbacks a month`}
          href="/packs"
        />
      </div>

      <div className="mt-6">
        <AutopilotCard status={auto} />
      </div>

      <section className="mt-10" aria-labelledby="todo-h">
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
          <p className="mt-3 rounded-lg border border-dashed px-4 py-6 text-center text-sm text-muted-foreground">Nothing needs your decision right now.</p>
        )}
      </section>

      <section className="mt-10" aria-labelledby="board-h">
        <h2 id="board-h" className="text-sm font-semibold tracking-tight">
          Every book
        </h2>
        <div className="mt-3 grid items-start gap-3 md:grid-cols-3 xl:grid-cols-6">
          {COLUMNS.map((col) => {
            const items = books.filter((bk) => col.statuses.includes(bk.status));
            return (
              <section key={col.title} className="rounded-lg bg-secondary/60 p-2" aria-label={col.title}>
                <h3 className="flex items-center justify-between px-1.5 pb-2 pt-1 text-xs font-medium text-muted-foreground">
                  {col.title}
                  <span className="tabular-nums">{items.length}</span>
                </h3>
                <ul className="space-y-2">
                  {items.map((bk) => {
                    const needs = NEEDS_ME[bk.status];
                    return (
                      <li key={bk.id} className="rounded-lg border bg-card p-3 shadow-xs">
                        <Link href={`/books/${bk.id}`} className="block text-sm font-medium leading-snug hover:underline">
                          {bk.title}
                        </Link>
                        <div className="mt-2 flex flex-wrap items-center gap-1">
                          <Badge value={bk.status} />
                          {bk.kdp_skipped && <Badge value="not for KDP" tone="neutral" />}
                        </div>
                        {bk.kdp_week_start && <p className="mt-2 text-xs text-muted-foreground">KDP week {fmtDay(bk.kdp_week_start)}</p>}
                        {needs && (
                          <Link href={needs.href(bk.id)} className="mt-2 inline-flex items-center gap-1 text-xs font-medium underline-offset-4 hover:underline">
                            {needs.label} <ChevronRight className="size-3" aria-hidden="true" />
                          </Link>
                        )}
                      </li>
                    );
                  })}
                  {!items.length && <li className="px-1.5 pb-1 text-xs text-muted-foreground">Empty</li>}
                </ul>
              </section>
            );
          })}
        </div>
      </section>

      <section className="mt-10" aria-labelledby="more-h">
        <h2 id="more-h" className="text-sm font-semibold tracking-tight">
          Everything else
        </h2>
        <div className="mt-3 grid grid-cols-2 gap-3 lg:grid-cols-3">
          <StatTile
            label="API spend this month"
            icon={<Wallet />}
            value={
              <>
                ₹{b.spent_inr.toFixed(0)}
                <span className="text-base font-normal text-muted-foreground"> / ₹{b.cap_inr.toFixed(0)}</span>
              </>
            }
            sub={
              <div className="mt-2 h-1.5 overflow-hidden rounded-lg bg-secondary" role="progressbar" aria-label="API budget used" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
                <div className={`h-full rounded-lg ${b.state === "ok" ? "bg-primary" : b.state === "warn" ? "bg-amber-500" : "bg-rose-600"}`} style={{ width: `${Math.min(100, pct)}%` }} />
              </div>
            }
            href="/costs"
          />
          <StatTile label="Failed jobs" icon={<AlertTriangle />} value={dash.failed_jobs} tone={dash.failed_jobs ? "bad" : undefined} sub="open job monitor" href="/jobs?status=failed" />
          <StatTile label="Needs you" icon={<Bell />} value={dash.needs_you} sub={dash.needs_you ? "approvals and reviews" : "all clear"} />
          <StatTile label="Live on Amazon" icon={<BookOpen />} value={dash.books_by_status.live ?? 0} sub={`${books.length} books in total`} />
          <StatTile label="Subscribers" icon={<Users />} value={dash.subscribers} sub="confirmed" href="/subscribers" />
          <StatTile label="Messages" icon={<Inbox />} value={dash.messages} sub="from the contact form" href="/messages" />
          <StatTile label="Niche ideas" icon={<Lightbulb />} value={dash.pending_niches} sub="waiting for review" href="/niches" />
        </div>
      </section>
    </>
  );
}
