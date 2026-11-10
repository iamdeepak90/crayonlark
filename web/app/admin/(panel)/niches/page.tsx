import { ArrowRight } from "lucide-react";
import Link from "next/link";
import NicheDecision from "@/components/admin/NicheDecision";
import NicheForm from "@/components/admin/NicheForm";
import { Badge, Card, PageTitle, fmtDate } from "@/components/admin/ui";
import { serverApi } from "@/lib/api";
import type { AIProviders } from "@/lib/types";
import { buttonVariants } from "@/components/ui/button";

type Niche = { id: number; book_id: number | null; theme: string; name: string; age_range: string; angle: string; risks: string; seasonality: string; notes: string; source: string; status: string; approved_by: string | null; created_at: string };

export default async function NichesPage() {
  const [niches, ai] = await Promise.all([serverApi<Niche[]>("/api/admin/niches"), serverApi<AIProviders>("/api/admin/ai/providers")]);
  return (
    <>
      <PageTitle description="Approve a niche and its book is created for you; the concept agent then writes the scene prompts.">Niche ideas</PageTitle>
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-3 lg:col-span-2">
          {niches.map((n) => (
            <Card key={n.id} title={<span>{n.name} <span className="text-sm font-normal text-slate-500">· {n.theme} · ages {n.age_range}</span></span>} actions={<Badge value={n.status} />}>
              {n.angle && <p className="text-sm"><strong>Angle:</strong> {n.angle}</p>}
              {n.risks && <p className="text-sm text-rose-800"><strong>Risks:</strong> {n.risks}</p>}
              {n.seasonality && <p className="text-sm"><strong>Season:</strong> {n.seasonality}</p>}
              {n.notes && <p className="text-sm text-slate-600">{n.notes}</p>}
              <p className="mt-1 text-xs text-slate-500">{n.source} · {fmtDate(n.created_at)}{n.approved_by ? ` · decided by ${n.approved_by}` : ""}</p>
              <div className="mt-3 flex gap-2">
                {n.status === "proposed" && <NicheDecision id={n.id} name={n.name} />}
                {n.status === "approved" && n.book_id && (
                  <Link href={`/books/${n.book_id}`} className={buttonVariants({ variant: "outline", size: "sm" })}>
                    Open book <ArrowRight aria-hidden="true" />
                  </Link>
                )}
                {n.status === "approved" && !n.book_id && (
                  <Link href={`/books/new?niche=${n.id}`} className={buttonVariants({ size: "sm" })}>Create book</Link>
                )}
              </div>
            </Card>
          ))}
          {!niches.length && <p className="text-slate-500">No niche ideas yet. Add one, or ask the research agent.</p>}
        </div>
        <NicheForm webSearch={ai.keys.websearch} />
      </div>
    </>
  );
}
