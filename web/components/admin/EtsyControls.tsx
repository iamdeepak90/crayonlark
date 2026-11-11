"use client";

import { LoaderCircle, Undo2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

const select = "h-8 rounded-lg border bg-background px-2 text-sm";
const pad = (n: number) => String(n).padStart(2, "0");
/** UTC hour → India time (UTC+5:30), e.g. 14 → "19:30". */
const ist = (hourUtc: number) => {
  const m = (hourUtc * 60 + 330) % 1440;
  return `${pad(Math.floor(m / 60))}:${pad(m % 60)}`;
};

/** How many approved books go live on Etsy per day, and from what hour (UTC). */
export function EtsyDailyForm({ perDay, hourUtc }: { perDay: number; hourUtc: number }) {
  const router = useRouter();
  const [n, setN] = useState(perDay);
  const [h, setH] = useState(hourUtc);
  const [busy, setBusy] = useState(false);
  const changed = n !== perDay || h !== hourUtc;
  return (
    <form
      className="flex flex-wrap items-end gap-3 text-sm"
      onSubmit={async (e) => {
        e.preventDefault();
        setBusy(true);
        try {
          await api("/api/admin/etsy/daily", { method: "PUT", body: { per_day: n, hour_utc: h } });
          toast.success("Daily Etsy schedule saved");
          router.refresh();
        } catch (err) {
          toast.error("Could not save", { description: err instanceof Error ? err.message : undefined });
        } finally {
          setBusy(false);
        }
      }}
    >
      <label className="grid gap-1">
        <span className="text-muted-foreground">Books per day</span>
        <select className={select} value={n} onChange={(e) => setN(Number(e.target.value))}>
          {[1, 2, 3, 4, 5].map((v) => (
            <option key={v}>{v}</option>
          ))}
        </select>
      </label>
      <label className="grid gap-1">
        <span className="text-muted-foreground">From (UTC)</span>
        <select className={select} value={h} onChange={(e) => setH(Number(e.target.value))}>
          {Array.from({ length: 24 }, (_, v) => (
            <option key={v} value={v}>
              {pad(v)}:00 ({ist(v)} IST)
            </option>
          ))}
        </select>
      </label>
      <Button type="submit" size="sm" variant="outline" disabled={busy || !changed}>
        {busy && <LoaderCircle className="animate-spin" aria-hidden="true" />}
        Save
      </Button>
    </form>
  );
}

/** Send a book back to the listing agent, with an optional note on what to change. */
export function SendBackButton({ bookId }: { bookId: number }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  return (
    <Button
      variant="outline"
      disabled={busy}
      onClick={async () => {
        const note = window.prompt("What should change? (optional; the listing text is written again)");
        if (note === null) return;
        setBusy(true);
        try {
          await api(`/api/admin/books/${bookId}/etsy/send-back`, { body: { note } });
          toast.success("Sent back: the listing text is being written again");
          router.refresh();
        } catch (err) {
          toast.error("Send back failed", { description: err instanceof Error ? err.message : undefined });
        } finally {
          setBusy(false);
        }
      }}
    >
      {busy ? <LoaderCircle className="animate-spin" aria-hidden="true" /> : <Undo2 aria-hidden="true" />}
      Send back
    </Button>
  );
}
