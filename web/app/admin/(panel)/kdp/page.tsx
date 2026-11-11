import { AlertTriangle, Ban, Check, ExternalLink, Image as ImageIcon, Pencil, RotateCcw } from "lucide-react";
import Link from "next/link";
import ActionButton from "@/components/admin/ActionButton";
import { Badge, Card, PageTitle, StatTile, fileUrl, fmtDate, fmtDay, money } from "@/components/admin/ui";
import { Button, buttonVariants } from "@/components/ui/button";
import { serverApi } from "@/lib/api";
import type { KdpCandidate, KdpCandidates } from "@/lib/types";

function Stats({ c }: { c: KdpCandidate }) {
  const s = c.stats;
  const cells: [string, string][] = [
    ["Days on Etsy", s.days_on_etsy.toFixed(0)],
    ["Views", String(s.views)],
    ["Favourites", String(s.favorites)],
    ["Sales", String(s.sales)],
    ["Revenue", money(s.revenue_cents)],
    ["Conversion", s.conversion === null ? "—" : `${s.conversion}%`],
    ["Score", s.score.toFixed(1)],
  ];
  return (
    <dl className="grid grid-cols-4 overflow-hidden rounded-lg border text-sm sm:grid-cols-7">
      {cells.map(([k, v]) => (
        <div key={k} className="border-b border-r p-2 last:border-r-0 sm:border-b-0">
          <dt className="text-xs text-muted-foreground">{k}</dt>
          <dd className={k === "Score" ? "text-lg font-semibold tabular-nums" : "font-medium tabular-nums"}>{v}</dd>
        </div>
      ))}
    </dl>
  );
}

function Candidate({ c, rank, week }: { c: KdpCandidate; rank: number; week: string }) {
  const problems = c.kdp_listing ? Object.values(c.kdp_listing.problems).flat() : [];
  const coverRejected = c.cover?.approval === "rejected";
  const blocked = !c.ready || problems.length > 0 || coverRejected;
  const young = c.stats.days_on_etsy < 7;
  return (
    <Card
      title={
        <span className="flex flex-wrap items-center gap-2">
          <span className="text-muted-foreground tabular-nums">#{rank}</span>
          <Link className="hover:underline" href={`/books/${c.id}`}>
            {c.title}
          </Link>
          {young && <Badge value="under a week on Etsy" tone="neutral" />}
          {c.kdp_skipped && <Badge value="not for KDP" tone="neutral" />}
        </span>
      }
      actions={
        c.etsy_url ? (
          <a href={c.etsy_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-sm font-medium underline underline-offset-4">
            Etsy <ExternalLink className="size-3.5" aria-hidden="true" />
          </a>
        ) : undefined
      }
    >
      <div className="grid gap-4 md:grid-cols-[8rem_1fr]">
        <div>
          {c.cover?.files.phone ? (
            <a href={fileUrl(c.cover.files.preview)} target="_blank" rel="noreferrer">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={fileUrl(c.cover.files.phone)} alt={`KDP cover version ${c.cover.version}`} className="w-32 rounded-md border bg-white" />
            </a>
          ) : (
            <div className="grid aspect-[3/4] w-32 place-items-center rounded-md border border-dashed text-xs text-muted-foreground">no cover yet</div>
          )}
          {c.cover && (
            <p className="mt-1 text-xs text-muted-foreground">
              cover v{c.cover.version} · {c.cover.approval}
            </p>
          )}
        </div>
        <div className="flex min-w-0 flex-col gap-3">
          <Stats c={c} />
          <p className="text-xs text-muted-foreground">
            {c.stats.stats_at ? `Etsy stats from ${fmtDate(c.stats.stats_at)}.` : "No Etsy stats yet (they sync every morning)."} {c.designs} designs · {c.pages ?? "—"} pages
          </p>
          {c.kdp_listing ? (
            <p className="text-sm">
              <span className="font-medium">{c.kdp_listing.title}</span>
              {c.kdp_listing.subtitle && <span className="text-muted-foreground">: {c.kdp_listing.subtitle}</span>} · {money(c.kdp_listing.price_cents)}
            </p>
          ) : (
            <p className="text-sm text-muted-foreground">No KDP listing text yet.</p>
          )}
          {(problems.length > 0 || coverRejected) && (
            <ul role="alert" className="flex flex-col gap-1 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200">
              {coverRejected && (
                <li className="flex gap-2">
                  <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden="true" /> The latest cover was rejected: a new one is being built.
                </li>
              )}
              {problems.map((p) => (
                <li key={p} className="flex gap-2">
                  <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden="true" /> {p}
                </li>
              ))}
            </ul>
          )}
          <div className="flex flex-wrap gap-2">
            {blocked ? (
              <Button variant="success" disabled>
                <Check aria-hidden="true" /> {c.ready ? "Fix the problems first" : "Cover or listing missing"}
              </Button>
            ) : (
              <ActionButton
                path={`/api/admin/books/${c.id}/kdp/approve`}
                body={{ cover_id: c.cover?.id }}
                label="Approve for KDP"
                icon={<Check aria-hidden="true" />}
                variant="success"
                confirm={`Approve this cover and listing for KDP? The upload pack is built for the week of ${fmtDay(week)}.`}
                success="Approved: the KDP upload pack is being built"
              />
            )}
            <Link href={`/books/${c.id}/cover`} className={buttonVariants({ variant: "outline" })}>
              <ImageIcon aria-hidden="true" /> Cover options
            </Link>
            <Link href={`/books/${c.id}/listings`} className={buttonVariants({ variant: "outline" })}>
              <Pencil aria-hidden="true" /> Edit KDP text
            </Link>
            {c.kdp_skipped ? (
              <ActionButton path={`/api/admin/books/${c.id}/kdp/skip`} body={{ skip: false }} label="Put back on the list" icon={<RotateCcw aria-hidden="true" />} variant="ghost" />
            ) : (
              <ActionButton path={`/api/admin/books/${c.id}/kdp/skip`} body={{ skip: true }} label="Not for KDP" icon={<Ban aria-hidden="true" />} variant="ghost" success="Hidden from the KDP list (it stays on Etsy)" />
            )}
          </div>
        </div>
      </div>
    </Card>
  );
}

export default async function KdpPage({ searchParams }: { searchParams: Promise<{ show_skipped?: string }> }) {
  const { show_skipped } = await searchParams;
  const showSkipped = show_skipped === "1";
  const d = await serverApi<KdpCandidates>(`/api/admin/kdp/candidates${showSkipped ? "?show_skipped=true" : ""}`);
  const k = d.slots;
  return (
    <>
      <PageTitle
        description={`Approval 2 of 2. Books live on Etsy, best first. Approve only the ones worth a paperback: approving takes the next free KDP week and builds the upload pack. ${k.paperback_limit} paperbacks a week, about ${d.per_month} a month.`}
        actions={
          <Link href={showSkipped ? "/kdp" : "/kdp?show_skipped=1"} className={buttonVariants({ variant: "outline", size: "sm" })}>
            {showSkipped ? "Hide 'not for KDP'" : "Show 'not for KDP'"}
          </Link>
        }
      >
        Pick for KDP
      </PageTitle>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatTile label="Candidates" value={d.candidates.length} sub="on Etsy, not yet on KDP" />
        <StatTile label="Slots this week" value={`${k.paperback_left} / ${k.paperback_limit}`} sub={`resets ${fmtDay(k.resets_at)}`} href="/packs" />
        <StatTile label="Next free week" value={fmtDay(d.next_free_week)} sub={`to ${fmtDay(d.next_free_week_end)}`} />
        <StatTile label="Per month" value={`≈ ${d.per_month}`} sub="paperbacks (KDP weekly limit)" />
      </div>
      <p className="mt-3 text-xs text-muted-foreground">Score = {d.score_help}. Books under a week count as one week, so wait a few days before judging a new book.</p>

      <section className="mt-8 flex flex-col gap-4" aria-label="KDP candidates">
        {d.candidates.length ? (
          d.candidates.map((c, i) => <Candidate key={c.id} c={c} rank={i + 1} week={d.next_free_week} />)
        ) : (
          <p className="rounded-lg border border-dashed px-4 py-6 text-center text-sm text-muted-foreground">
            No candidates yet. Books show up here once they are live on Etsy.
          </p>
        )}
      </section>
    </>
  );
}
