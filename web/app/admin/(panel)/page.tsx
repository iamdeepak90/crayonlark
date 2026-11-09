import Link from "next/link";
import { AlertTriangle, BookOpen, ChevronRight, Inbox, Lightbulb, Plus, Users, Wallet, Bell, Package } from "lucide-react";
import { Badge, ButtonLink, PageTitle, StatTile } from "@/components/admin/ui";
import { serverApi } from "@/lib/api";
import type { BookSummary, Dashboard } from "@/lib/types";

const COLUMNS: { title: string; statuses: string[] }[] = [
  { title: "Ideas & concepts", statuses: ["idea", "niche_approved", "concepts_ready"] },
  { title: "Images", statuses: ["images_generating", "images_qa", "awaiting_image_approval"] },
  { title: "Build", statuses: ["cleaning", "building", "awaiting_cover_approval"] },
  { title: "Listings", statuses: ["listing_draft", "awaiting_listing_approval"] },
  { title: "KDP", statuses: ["kdp_pack_ready", "kdp_uploaded", "proof_ordered"] },
  { title: "Live", statuses: ["live"] },
];

const NEEDS_ME: Record<string, string> = {
  awaiting_image_approval: "Approve images",
  awaiting_cover_approval: "Approve cover",
  awaiting_listing_approval: "Approve listing",
  kdp_pack_ready: "Upload to KDP",
};

function nextAction(b: BookSummary): string | null {
  switch (b.status) {
    case "awaiting_image_approval":
      return `/books/${b.id}/images`;
    case "awaiting_cover_approval":
      return `/books/${b.id}/cover`;
    case "awaiting_listing_approval":
    case "listing_draft":
      return `/books/${b.id}/listings`;
    case "kdp_pack_ready":
      return `/packs`;
    default:
      return null;
  }
}

type Todo = { key: string; label: string; detail: string; href: string };

export default async function PipelinePage() {
  const [books, dash] = await Promise.all([serverApi<BookSummary[]>("/api/admin/books"), serverApi<Dashboard>("/api/admin/dashboard")]);
  const k = dash.kdp_slots;
  const b = dash.budget;
  const pct = Math.round(b.ratio * 100);

  const todos: Todo[] = [
    ...books
      .filter((bk) => NEEDS_ME[bk.status])
      .map((bk) => ({ key: `book-${bk.id}`, label: NEEDS_ME[bk.status], detail: bk.title, href: nextAction(bk) ?? `/books/${bk.id}` })),
    ...(dash.pending_niches
      ? [{ key: "niches", label: "Review niche ideas", detail: `${dash.pending_niches} proposed`, href: "/niches" }]
      : []),
    ...(dash.posts_to_review
      ? [{ key: "posts", label: "Review blog drafts", detail: `${dash.posts_to_review} waiting`, href: "/blog" }]
      : []),
  ];

  return (
    <>
      <PageTitle
        description="Every book from idea to live, and what is waiting for your decision."
        actions={
          <ButtonLink href="/books/new">
            <Plus aria-hidden="true" /> New book
          </ButtonLink>
        }
      >
        Pipeline
      </PageTitle>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatTile label="Needs you" icon={<Bell />} value={dash.needs_you} sub={dash.needs_you ? "approvals and reviews" : "all clear"} />
        <StatTile
          label="KDP slots this week"
          icon={<Package />}
          value={
            <>
              {k.paperback_left}
              <span className="text-base font-normal text-muted-foreground"> / {k.paperback_limit}</span>
            </>
          }
          sub={`paperback left · ${k.hardcover_left}/${k.hardcover_limit} hardcover · resets ${new Date(k.resets_at).toUTCString().slice(0, 11)}`}
          href="/packs"
        />
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
        <StatTile label="Live books" icon={<BookOpen />} value={dash.books_by_status.live ?? 0} sub={`${books.length} in total`} />
        <StatTile label="Subscribers" icon={<Users />} value={dash.subscribers} sub="confirmed" href="/subscribers" />
        <StatTile label="Messages" icon={<Inbox />} value={dash.messages} sub="from the contact form" href="/messages" />
        <StatTile label="Niche ideas" icon={<Lightbulb />} value={dash.pending_niches} sub="waiting for review" href="/niches" />
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
          Board
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
                    const action = nextAction(bk);
                    const needs = NEEDS_ME[bk.status];
                    return (
                      <li key={bk.id} className="rounded-lg border bg-card p-3 shadow-xs">
                        <Link href={`/books/${bk.id}`} className="block text-sm font-medium leading-snug hover:underline">
                          {bk.title}
                        </Link>
                        <div className="mt-2 flex flex-wrap items-center gap-1">
                          <Badge value={bk.status} />
                          {bk.etsy_status !== "none" && <Badge value={`etsy ${bk.etsy_status}`} tone="neutral" />}
                        </div>
                        <p className="mt-2 text-xs text-muted-foreground">
                          {bk.counts.approved ?? 0} approved · {bk.counts.pending ?? 0} pending
                          {bk.kdp_week_start ? ` · week ${bk.kdp_week_start}` : ""}
                        </p>
                        {action && needs && (
                          <Link href={action} className="mt-2 inline-flex items-center gap-1 text-xs font-medium underline-offset-4 hover:underline">
                            {needs} <ChevronRight className="size-3" aria-hidden="true" />
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
    </>
  );
}
