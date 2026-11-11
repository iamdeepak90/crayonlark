"use client";

import { CircleCheck, CircleX, LoaderCircle, Sparkles } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Input, Label, Textarea } from "@/components/ui/input";
import { api } from "@/lib/api";
import { Button, Card } from "./ui";

type Job = { status: string; error: string; result: { niche_ids?: number[]; dropped?: string[]; web_results?: number; web_error?: string | null } };
type Run = { state: "running" | "done" | "failed"; text: string; jobId?: string };

const POLL_MS = 2500;
const GIVE_UP_MS = 5 * 60 * 1000;

export default function NicheForm({ webSearch = true }: { webSearch?: boolean }) {
  const router = useRouter();
  const [run, setRun] = useState<Run | null>(null);
  const [addMsg, setAddMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const toastId = useRef<string | number | undefined>(undefined);

  useEffect(() => () => {
    if (timer.current) clearTimeout(timer.current);
  }, []);

  /** Follow the background job until it finishes, then show the new ideas (or the error). */
  function finish(next: Run) {
    setRun(next);
    setBusy(false);
    const opts = { id: toastId.current, description: next.text };
    if (next.state === "done") toast.success("Niche ideas ready", opts);
    else toast.error("Niche research failed", opts);
  }

  function follow(jobId: string, web: boolean, started: number) {
    timer.current = setTimeout(async () => {
      try {
        const j = await api<Job>(`/api/admin/jobs/${jobId}`);
        if (j.status === "succeeded") {
          const r = j.result;
          const n = r.niche_ids?.length ?? 0;
          const parts = [`${n} new niche idea${n === 1 ? "" : "s"} added below.`];
          if (r.dropped?.length) parts.push(`${r.dropped.length} dropped by the blocklist.`);
          if (web && r.web_error) parts.push(`Web search failed (${r.web_error.split("\n")[0]}), so only your notes were used.`);
          else if (web) parts.push(`${r.web_results ?? 0} web results used.`);
          finish({ state: "done", text: parts.join(" ") });
          router.refresh();
          return;
        }
        if (j.status === "failed") {
          finish({ state: "failed", text: j.error.split("\n")[0] || "The research job failed.", jobId });
          return;
        }
        if (Date.now() - started > GIVE_UP_MS) {
          finish({ state: "failed", text: "Still running after 5 minutes. Is the worker running? Check the job monitor.", jobId });
          return;
        }
        follow(jobId, web, started);
      } catch (e) {
        finish({ state: "failed", text: e instanceof Error ? e.message : "Could not read the job status.", jobId });
      }
    }, POLL_MS);
  }

  async function research(form: FormData) {
    setBusy(true);
    setRun(null);
    try {
      const r = await api<{ job_id: string; web_search: boolean }>("/api/admin/research", {
        body: { theme: form.get("theme"), competitor_notes: form.get("competitor_notes"), use_web: form.get("use_web") === "on" },
      });
      const text = `Research agent is working${r.web_search ? " (with web search)" : ""}… usually under a minute.`;
      setRun({ state: "running", text, jobId: r.job_id });
      toastId.current = toast.loading("Finding niche ideas…", { description: text });
      follow(r.job_id, r.web_search, Date.now());
    } catch (e) {
      toastId.current = undefined;
      finish({ state: "failed", text: e instanceof Error ? e.message : "failed" });
    }
  }

  async function add(form: FormData) {
    setBusy(true);
    setAddMsg("");
    try {
      await api("/api/admin/niches", { body: Object.fromEntries(form.entries()) });
      router.refresh();
    } catch (e) {
      setAddMsg(e instanceof Error ? e.message : "failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <Card title="Ask the research agent">
        <form action={research} className="grid gap-4">
          <div className="grid gap-2">
            <Label htmlFor="r-theme">Theme</Label>
            <Input id="r-theme" name="theme" required placeholder="ocean animals" />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="r-notes">Competitor notes (optional, paste your own research)</Label>
            <Textarea id="r-notes" name="competitor_notes" rows={4} />
          </div>
          <div className="grid gap-1">
            <Label className="font-normal">
              <input type="checkbox" name="use_web" defaultChecked={webSearch} disabled={!webSearch} />
              Use web search
            </Label>
            {!webSearch && <p className="text-xs text-muted-foreground">Off: add a free LangSearch or TinyFish key in Settings → Keys and connections → Web search.</p>}
          </div>
          <div>
            <Button disabled={busy}>
              {busy ? <LoaderCircle className="animate-spin" aria-hidden="true" /> : <Sparkles aria-hidden="true" />}
              Suggest 10 niches
            </Button>
          </div>
          {run && (
            <div
              role="status"
              className={`flex items-start gap-2 rounded-md border p-3 text-sm ${
                run.state === "failed" ? "border-destructive/30 bg-destructive/5 text-destructive" : "bg-secondary/50"
              }`}
            >
              {run.state === "running" && <LoaderCircle className="mt-0.5 size-4 shrink-0 animate-spin" aria-hidden="true" />}
              {run.state === "done" && <CircleCheck className="mt-0.5 size-4 shrink-0 text-emerald-600" aria-hidden="true" />}
              {run.state === "failed" && <CircleX className="mt-0.5 size-4 shrink-0" aria-hidden="true" />}
              <span>
                {run.text}{" "}
                {run.state === "failed" && run.jobId && (
                  <Link href="/jobs?status=failed" className="font-medium underline underline-offset-4">
                    Open job monitor
                  </Link>
                )}
              </span>
            </div>
          )}
        </form>
      </Card>
      <Card title="Add a niche by hand">
        <form action={add} className="grid gap-4">
          {[["theme", "Theme"], ["name", "Niche name"], ["age_range", "Age range"], ["angle", "Angle"], ["risks", "Risks"], ["seasonality", "Seasonality"]].map(([k, l]) => (
            <div key={k} className="grid gap-2">
              <Label htmlFor={`n-${k}`}>{l}</Label>
              <Input id={`n-${k}`} name={k} required={k === "theme" || k === "name"} defaultValue={k === "age_range" ? "4-8" : ""} />
            </div>
          ))}
          <label className="flex items-start gap-2 text-sm">
            <input type="checkbox" name="color_reference" value="true" className="mt-0.5" />
            <span>
              Color example in the corner of each page
              <span className="block text-xs text-muted-foreground">Etsy printables only. KDP stays black & white. Its books follow this setting.</span>
            </span>
          </label>
          <div>
            <Button disabled={busy}>Add niche</Button>
          </div>
          {addMsg && (
            <p role="alert" className="text-sm text-destructive">
              {addMsg}
            </p>
          )}
        </form>
      </Card>
    </div>
  );
}
