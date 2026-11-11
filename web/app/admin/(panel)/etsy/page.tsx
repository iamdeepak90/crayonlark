import { AlertTriangle, Check, ExternalLink, FileDown, Pencil, Rocket, X } from "lucide-react";
import Link from "next/link";
import ActionButton from "@/components/admin/ActionButton";
import ConnectCard from "@/components/admin/ConnectCard";
import { EtsyDailyForm, SendBackButton } from "@/components/admin/EtsyControls";
import { Card, PageTitle, StatTile, fileUrl, fmtDate, fmtDay, money } from "@/components/admin/ui";
import { Button, buttonVariants } from "@/components/ui/button";
import { serverApi } from "@/lib/api";
import type { EtsyBookCard, EtsyReview } from "@/lib/types";

function Problems({ problems }: { problems: Record<string, string[]> }) {
  const all = Object.values(problems).flat();
  if (!all.length) return null;
  return (
    <ul role="alert" className="flex flex-col gap-1 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200">
      {all.map((p) => (
        <li key={p} className="flex gap-2">
          <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden="true" /> {p}
        </li>
      ))}
    </ul>
  );
}

function Mockups({ keys, size = "h-36" }: { keys: string[]; size?: string }) {
  if (!keys.length) return <p className="text-sm text-muted-foreground">Listing photos are being made…</p>;
  return (
    <ul className="flex gap-2 overflow-x-auto pb-1">
      {keys.map((k) => (
        <li key={k} className="shrink-0">
          <a href={fileUrl(k)} target="_blank" rel="noreferrer">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={fileUrl(k)} alt="Etsy listing photo" loading="lazy" className={`${size} rounded-md border bg-white`} />
          </a>
        </li>
      ))}
    </ul>
  );
}

function WaitingBook({ b }: { b: EtsyBookCard }) {
  const l = b.listing;
  const problems = l ? Object.values(l.problems).flat().length : 0;
  return (
    <Card
      title={
        <Link className="hover:underline" href={`/books/${b.id}`}>
          {b.title}
        </Link>
      }
    >
      <div className="flex flex-col gap-4">
        <Mockups keys={b.mockups} />
        {l ? (
          <div className="grid gap-4 lg:grid-cols-3">
            <div className="flex flex-col gap-2 lg:col-span-2">
              <p className="font-medium">{l.title}</p>
              <details className="text-sm text-muted-foreground">
                <summary className="cursor-pointer select-none text-foreground">Description</summary>
                <p className="mt-2 whitespace-pre-line">{l.description}</p>
              </details>
              <ul className="flex flex-wrap gap-1">
                {l.tags.map((t) => (
                  <li key={t} className="rounded-md bg-secondary px-2 py-0.5 text-xs">
                    {t}
                  </li>
                ))}
              </ul>
            </div>
            <dl className="grid h-fit grid-cols-2 gap-x-3 gap-y-1 text-sm">
              <dt className="text-muted-foreground">Price</dt>
              <dd className="font-medium">{money(l.price_cents)}</dd>
              <dt className="text-muted-foreground">Coloring pages</dt>
              <dd>{b.pages}</dd>
              <dt className="text-muted-foreground">Color example</dt>
              <dd>{b.color_reference ? "yes, in the corner" : "no"}</dd>
              <dt className="text-muted-foreground">PDF files</dt>
              <dd className="flex flex-wrap gap-2">
                {Object.entries(l.file_keys).map(([paper, key]) => (
                  <a key={paper} href={fileUrl(key)} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 font-medium underline underline-offset-4">
                    <FileDown className="size-3.5" aria-hidden="true" />
                    {paper === "a4" ? "A4" : "Letter"}
                  </a>
                ))}
                {!Object.keys(l.file_keys).length && <span className="text-muted-foreground">being built…</span>}
              </dd>
            </dl>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">The listing text is missing. Use Continue on the book page.</p>
        )}
        <details>
          <summary className="cursor-pointer select-none text-sm">All {b.page_ids.length} coloring pages</summary>
          <ul className="mt-2 grid grid-cols-4 gap-2 sm:grid-cols-6 lg:grid-cols-10">
            {b.page_ids.map((pid) => (
              <li key={pid}>
                <a href={`/api/admin/images/${pid}/file?variant=cleaned`} target="_blank" rel="noreferrer">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={`/api/admin/images/${pid}/file?variant=thumb`} alt={`Page ${pid}`} loading="lazy" className="aspect-[3/4] w-full rounded-md border bg-white object-contain" />
                </a>
              </li>
            ))}
          </ul>
        </details>
        {l && <Problems problems={l.problems} />}
        <div className="flex flex-wrap gap-2">
          {problems ? (
            <Button variant="success" disabled>
              <Check aria-hidden="true" /> Fix {problems} problem(s) first
            </Button>
          ) : (
            <ActionButton
              path={`/api/admin/books/${b.id}/etsy/approve`}
              label="Approve for Etsy"
              icon={<Check aria-hidden="true" />}
              variant="success"
              success="Approved: added to the Etsy queue"
            />
          )}
          <Link href={`/books/${b.id}/listings`} className={buttonVariants({ variant: "outline" })}>
            <Pencil aria-hidden="true" /> Edit text
          </Link>
          <SendBackButton bookId={b.id} />
        </div>
      </div>
    </Card>
  );
}

export default async function EtsyPage() {
  const d = await serverApi<EtsyReview>("/api/admin/etsy/review");
  const hour = `${String(d.daily.hour_utc).padStart(2, "0")}:00 UTC`;
  return (
    <>
      <PageTitle
        description={`Approval 1 of 2. Every finished book comes here. Approved books join the queue and ${d.daily.per_day} goes live on Etsy each day from ${hour}, first approved first.`}
      >
        Approve for Etsy
      </PageTitle>

      {!d.connected && (
        <ConnectCard name="etsy" label="Etsy" configured={d.configured} connection={d.connection}>
          <p className="mt-2 text-sm text-muted-foreground">You can approve books now; the queue starts publishing once Etsy is connected.</p>
        </ConnectCard>
      )}

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatTile label="Waiting for you" value={d.waiting.length} sub="finished books" />
        <StatTile label="In the queue" value={d.queue.length} sub={`${d.days_of_stock} days of stock`} tone={d.low_stock ? "bad" : undefined} />
        <StatTile label="Live today" value={`${d.live_today} / ${d.daily.per_day}`} sub={d.connected ? `Etsy API calls left: ${d.remaining_today ?? "—"}` : "Etsy not connected"} />
        <StatTile label="In production" value={d.in_production} sub="books still being made" />
      </div>

      <section className="mt-10 flex flex-col gap-4" aria-labelledby="waiting-h">
        <h2 id="waiting-h" className="text-sm font-semibold tracking-tight">
          Waiting for approval
        </h2>
        {d.waiting.length ? (
          d.waiting.map((b) => <WaitingBook key={b.id} b={b} />)
        ) : (
          <p className="rounded-lg border border-dashed px-4 py-6 text-center text-sm text-muted-foreground">
            No finished books waiting. Books arrive here by themselves after you approve their images.
          </p>
        )}
      </section>

      <section id="queue" className="mt-10 scroll-mt-20" aria-labelledby="queue-h">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <h2 id="queue-h" className="text-sm font-semibold tracking-tight">
            Etsy queue
          </h2>
          <EtsyDailyForm perDay={d.daily.per_day} hourUtc={d.daily.hour_utc} />
        </div>
        {d.queue.length ? (
          <ol className="mt-3 divide-y overflow-hidden rounded-lg border bg-card shadow-xs">
            {d.queue.map((b) => (
              <li key={b.id} className="flex flex-wrap items-center gap-3 px-4 py-3 text-sm">
                <span className="w-24 shrink-0 font-medium tabular-nums">{fmtDay(b.planned_for)}</span>
                {b.mockups[0] && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={fileUrl(b.mockups[0])} alt="" className="h-12 rounded-md border bg-white" />
                )}
                <Link href={`/books/${b.id}`} className="min-w-0 flex-1 truncate hover:underline">
                  {b.title}
                </Link>
                {b.etsy?.error && <span className="text-xs text-destructive">{b.etsy.error.slice(0, 120)}</span>}
                <div className="flex gap-2">
                  {d.connected && (
                    <ActionButton
                      path={`/api/admin/books/${b.id}/etsy/publish-now`}
                      label="Publish now"
                      icon={<Rocket aria-hidden="true" />}
                      variant="outline"
                      confirm="Put this book live on Etsy now? Buyers can see it straight away."
                      success="Publishing: it will be live in a minute"
                    />
                  )}
                  <ActionButton
                    path={`/api/admin/books/${b.id}/etsy/unqueue`}
                    label="Remove"
                    icon={<X aria-hidden="true" />}
                    variant="ghost"
                    confirm="Take this book out of the queue? It goes back to 'waiting for approval'."
                    success="Removed from the queue"
                  />
                </div>
              </li>
            ))}
          </ol>
        ) : (
          <p className="mt-3 rounded-lg border border-dashed px-4 py-6 text-center text-sm text-muted-foreground">The queue is empty. Approve a book above to fill it.</p>
        )}
      </section>

      {d.recent.length > 0 && (
        <section className="mt-10" aria-labelledby="recent-h">
          <h2 id="recent-h" className="text-sm font-semibold tracking-tight">
            Recently live on Etsy
          </h2>
          <ul className="mt-3 divide-y overflow-hidden rounded-lg border bg-card shadow-xs">
            {d.recent.map((b) => (
              <li key={b.id} className="flex flex-wrap items-center gap-3 px-4 py-3 text-sm">
                <span className="w-40 shrink-0 text-muted-foreground">{fmtDate(b.etsy_live_at)}</span>
                <Link href={`/books/${b.id}`} className="min-w-0 flex-1 truncate hover:underline">
                  {b.title}
                </Link>
                {b.etsy?.url && (
                  <a href={b.etsy.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 font-medium underline underline-offset-4">
                    View on Etsy <ExternalLink className="size-3.5" aria-hidden="true" />
                  </a>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}
    </>
  );
}
