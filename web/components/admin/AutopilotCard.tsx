"use client";

import { AlertTriangle, Bot, LoaderCircle } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import type { AutopilotStatus } from "@/lib/types";
import { Badge, Card } from "./ui";

const field = "h-8 w-20 rounded-lg border bg-background px-2 text-sm";

/** Switch the Autopilot on/off and tune it. Everything between my two approvals runs by itself. */
export default function AutopilotCard({ status }: { status: AutopilotStatus }) {
  const router = useRouter();
  const [keep, setKeep] = useState(status.keep_books);
  const [perDay, setPerDay] = useState(status.new_books_per_day);
  const [themes, setThemes] = useState(status.themes.join("\n"));
  const [busy, setBusy] = useState(false);

  async function save(enabled: boolean) {
    setBusy(true);
    try {
      const themeList = themes.split("\n").map((t) => t.trim()).filter(Boolean);
      await api("/api/admin/autopilot", { method: "PUT", body: { enabled, keep_books: keep, new_books_per_day: perDay, themes: themeList } });
      toast.success(enabled ? "Autopilot is on" : "Autopilot is off");
      router.refresh();
    } catch (e) {
      toast.error("Could not save", { description: e instanceof Error ? e.message : undefined });
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card
      title={
        <span className="flex items-center gap-2">
          <Bot className="size-4" aria-hidden="true" /> Autopilot
        </span>
      }
      actions={<Badge value={status.enabled ? "on" : "off"} tone={status.enabled ? "ok" : "neutral"} />}
    >
      <div className="flex flex-col gap-4 text-sm">
        <p className="text-muted-foreground">
          When on, it picks niche ideas, starts books, makes the pictures and keeps only the ones that pass both checks (pixel QA and the AI vision check). You only do{" "}
          <strong className="text-foreground">Approve for Etsy</strong> and <strong className="text-foreground">Pick for KDP</strong>. You see every page before anything goes on Etsy.
        </p>
        {status.problems.length > 0 && (
          <ul role="alert" className="flex flex-col gap-1 rounded-lg border border-amber-300 bg-amber-50 p-3 text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200">
            {status.problems.map((p) => (
              <li key={p} className="flex gap-2">
                <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden="true" /> {p} Fix it in Settings → AI.
              </li>
            ))}
          </ul>
        )}
        <p>
          {status.stock} books in production or waiting · {status.proposed_niches} niche ideas left
        </p>
        <div className="flex flex-wrap items-end gap-4">
          <label className="grid gap-1">
            <span className="text-muted-foreground">Keep this many books going</span>
            <input type="number" min={1} max={30} value={keep} onChange={(e) => setKeep(Number(e.target.value))} className={field} />
          </label>
          <label className="grid gap-1">
            <span className="text-muted-foreground">New books per day (max)</span>
            <input type="number" min={1} max={5} value={perDay} onChange={(e) => setPerDay(Number(e.target.value))} className={field} />
          </label>
        </div>
        <details>
          <summary className="cursor-pointer select-none">Research themes ({status.themes.length})</summary>
          <label className="mt-2 grid gap-1">
            <span className="text-muted-foreground">One per line. When the niche ideas run out it researches the least-used theme (once a day).</span>
            <textarea value={themes} onChange={(e) => setThemes(e.target.value)} rows={8} className="rounded-lg border bg-background px-2 py-1" />
          </label>
        </details>
        <div className="flex flex-wrap gap-2">
          {status.enabled ? (
            <>
              <Button variant="outline" disabled={busy} onClick={() => save(true)}>
                {busy && <LoaderCircle className="animate-spin" aria-hidden="true" />} Save
              </Button>
              <Button variant="ghost" disabled={busy} onClick={() => save(false)}>
                Switch off
              </Button>
            </>
          ) : (
            <Button variant="success" disabled={busy} onClick={() => save(true)}>
              {busy ? <LoaderCircle className="animate-spin" aria-hidden="true" /> : <Bot aria-hidden="true" />} Switch Autopilot on
            </Button>
          )}
        </div>
      </div>
    </Card>
  );
}
