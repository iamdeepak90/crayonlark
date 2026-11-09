"use client";

import { Check, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";
import { Button } from "./ui";

/** Approve / reject the latest cover, or queue a new version with other options. */
export default function CoverControls({
  bookId,
  coverId,
  pending,
  canRebuild,
  themes,
  images,
}: {
  bookId: number;
  coverId: number | null;
  pending: boolean;
  canRebuild: boolean;
  themes: string[];
  images: { id: number; scene_title: string }[];
}) {
  const router = useRouter();
  const [theme, setTheme] = useState("");
  const [hero, setHero] = useState("");
  const [blurb, setBlurb] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  async function run(fn: () => Promise<unknown>, done: string) {
    setBusy(true);
    setMsg("");
    try {
      await fn();
      setMsg(done);
      router.refresh();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      {pending && coverId && (
        <div className="flex flex-wrap gap-2">
          <Button variant="success" disabled={busy} onClick={() => run(() => api(`/api/admin/covers/${coverId}/decision`, { body: { approve: true } }), "Cover approved. The listing agent is writing listings.")}>
            <Check aria-hidden="true" /> Approve cover
          </Button>
          <Button variant="destructive" disabled={busy} onClick={() => run(() => api(`/api/admin/covers/${coverId}/decision`, { body: { approve: false } }), "Rejected. A new version is being built.")}>
            <X aria-hidden="true" /> Reject (build new version)
          </Button>
        </div>
      )}
      {canRebuild && (
        <form
          className="grid gap-2 sm:grid-cols-2"
          onSubmit={(e) => {
            e.preventDefault();
            const body: Record<string, unknown> = {};
            if (theme) body.theme = theme;
            if (hero) body.hero_image_id = Number(hero);
            if (blurb.trim()) body.blurb = blurb.trim();
            run(() => api(`/api/admin/books/${bookId}/covers`, { body }), "New version queued. Refresh in a minute.");
          }}
        >
          <label className="text-sm">
            Colour theme
            <select value={theme} onChange={(e) => setTheme(e.target.value)} className="mt-1 block w-full rounded-lg border px-2 py-1">
              <option value="">next in rotation</option>
              {themes.map((t) => (
                <option key={t}>{t}</option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            Front picture
            <select value={hero} onChange={(e) => setHero(e.target.value)} className="mt-1 block w-full rounded-lg border px-2 py-1">
              <option value="">next in rotation</option>
              {images.map((i) => (
                <option key={i.id} value={i.id}>
                  #{i.id} {i.scene_title}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm sm:col-span-2">
            Back blurb (optional)
            <textarea value={blurb} maxLength={600} onChange={(e) => setBlurb(e.target.value)} rows={2} className="mt-1 block w-full rounded-lg border px-2 py-1" />
          </label>
          <div>
            <Button variant="outline" disabled={busy} type="submit">
              Build another version
            </Button>
          </div>
        </form>
      )}
      {msg && <p role="status" className="text-sm text-slate-700">{msg}</p>}
    </div>
  );
}
