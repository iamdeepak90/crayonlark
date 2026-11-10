"use client";

import { LoaderCircle, Palette } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";

/**
 * "Colour example in the corner" switch for a niche (its books follow) or one book.
 * Etsy printable PDFs only: KDP books stay black & white (colour ink costs far more).
 */
export default function ColorRefToggle({ kind, id, enabled }: { kind: "niche" | "book"; id: number; enabled: boolean }) {
  const router = useRouter();
  const [on, setOn] = useState(enabled);
  const [busy, setBusy] = useState(false);

  async function change(next: boolean) {
    setBusy(true);
    setOn(next);
    try {
      if (kind === "niche") {
        const r = await api<{ books_updated: number }>(`/api/admin/niches/${id}/color-reference`, { body: { enabled: next } });
        const books = r.books_updated ? ` and ${r.books_updated} book${r.books_updated > 1 ? "s" : ""}` : "";
        toast.success(`Color examples ${next ? "on" : "off"} for this niche${books}`);
      } else {
        await api(`/api/admin/books/${id}`, { method: "PATCH", body: { color_reference: next } });
        toast.success(`Color examples ${next ? "on" : "off"} for this book`, {
          description: next ? "Made for every cleaned page; they appear in the Etsy PDFs." : undefined,
        });
      }
      router.refresh();
    } catch (e) {
      setOn(!next);
      toast.error("Could not change color examples", { description: e instanceof Error ? e.message : undefined });
    } finally {
      setBusy(false);
    }
  }

  return (
    <label className="flex items-start gap-2 text-sm" title="Etsy printable PDFs only. KDP books stay black & white.">
      <input type="checkbox" className="mt-0.5" checked={on} disabled={busy} onChange={(e) => change(e.target.checked)} />
      <span>
        <span className="inline-flex items-center gap-1 font-medium">
          {busy ? <LoaderCircle className="size-3.5 animate-spin" aria-hidden="true" /> : <Palette className="size-3.5" aria-hidden="true" />}
          Color example in the corner
        </span>
        <span className="block text-xs text-muted-foreground">Etsy printables only. KDP stays black & white.</span>
      </span>
    </label>
  );
}
