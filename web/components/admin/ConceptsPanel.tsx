"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { ConceptsResponse, CostsResponse, ImageItem } from "@/lib/types";
import { Badge, Button, Card } from "./ui";

const POLL_MS = 5000;
const POLL_AFTER_ACTION_MS = 3 * 60 * 1000; // keep checking for a few minutes after starting a job

/** Scene prompts written by the concept agent, and the pictures made from them (AI or manual upload). */
export default function ConceptsPanel({ bookId }: { bookId: number }) {
  const router = useRouter();
  const [data, setData] = useState<ConceptsResponse | null>(null);
  const [rate, setRate] = useState<number | null>(null);
  const [count, setCount] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const [pollUntil, setPollUntil] = useState(0);

  const load = useCallback(async () => {
    try {
      setData(await api<ConceptsResponse>(`/api/admin/books/${bookId}/concepts`));
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "could not load scene prompts");
    }
  }, [bookId]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- fetch on mount; setState runs after the await
    load();
    // The ₹ rate is only for the estimate; show $ alone if this fails.
    api<CostsResponse>("/api/admin/costs").then((c) => setRate(c.usd_inr_rate), () => setRate(null));
  }, [load]);

  // While images are generating (or a job was just started), re-fetch every few seconds.
  useEffect(() => {
    const generating = data?.concepts.some((c) => c.status === "generating");
    if (!generating && Date.now() > pollUntil) return;
    const t = setTimeout(() => {
      load();
      router.refresh();
    }, POLL_MS);
    return () => clearTimeout(t);
  }, [data, pollUntil, load, router]);

  async function run(fn: () => Promise<string>) {
    setBusy(true);
    setMsg("");
    try {
      setMsg(await fn());
      setPollUntil(Date.now() + POLL_AFTER_ACTION_MS);
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "failed");
    } finally {
      setBusy(false);
      await load();
      router.refresh();
    }
  }

  if (!data) return <Card title="Scene prompts & AI images"><p className="text-sm text-slate-500">{msg || "Loading…"}</p></Card>;

  const manual = data.image_provider === "manual";
  const waiting = data.concepts.filter((c) => c.status === "pending");
  const n = count === "" ? waiting.length : Math.max(0, Math.min(waiting.length, Number(count) || 0));
  const estimate = n * data.price_per_image_usd;
  const all = [...data.concepts, ...data.failed].sort((a, b) => a.position - b.position);

  function writePrompts() {
    if (waiting.length && !window.confirm(`Replace the ${waiting.length} scene prompts that have no picture yet with new ones?`)) return;
    run(async () => {
      await api(`/api/admin/books/${bookId}/concepts`, { body: {} });
      return "Concept agent started. Scene prompts appear here in a minute.";
    });
  }

  const generate = (body: { count?: number; image_ids?: number[] }) =>
    run(async () => {
      const r = await api<{ queued: number; estimate_usd: number }>(`/api/admin/books/${bookId}/generate-images`, { body });
      return `Queued ${r.queued} image${r.queued === 1 ? "" : "s"} (≈ $${r.estimate_usd.toFixed(2)}). They go through QA, then wait for your approval.`;
    });

  async function copy(text: string, what: string) {
    try {
      await navigator.clipboard.writeText(text);
      setMsg(`Copied ${what}.`);
    } catch {
      setMsg("Could not copy: your browser blocked clipboard access.");
    }
  }

  const upload = (img: ImageItem, file: File) =>
    run(async () => {
      const form = new FormData();
      form.append("file", file);
      await api(`/api/admin/images/${img.id}/upload`, { form });
      return `Uploaded a picture for #${img.position} ${img.scene_title}. QA is running.`;
    });

  return (
    <Card title="Scene prompts & AI images" className="min-w-0 lg:col-span-2">
      <p className="mb-3 text-sm text-slate-600">
        {data.concepts.length} prompts waiting for a picture{data.failed.length ? ` · ${data.failed.length} failed` : ""} · images:{" "}
        {manual ? <strong>manual</strong> : <strong>{data.image_provider} / {data.image_model || "default model"}</strong>}
        {manual && " — copy a prompt, make the picture yourself, then upload it on its row (or drop files in Images)."}
      </p>
      <div className="flex flex-wrap items-end gap-2">
        <Button variant="ghost" disabled={busy || !data.can_make_concepts} onClick={writePrompts} title={data.can_make_concepts ? "" : `Book is ${data.status}`}>
          Write scene prompts
        </Button>
        {!manual && (
          <>
            <label className="text-xs font-semibold">
              How many
              <input type="number" min={0} max={waiting.length} value={count} placeholder={String(waiting.length)} onChange={(e) => setCount(e.target.value)} className="mt-1 block w-20 rounded-lg border border-slate-300 px-2 py-1 text-sm" />
            </label>
            <Button disabled={busy || !data.can_generate || n === 0} onClick={() => generate({ count: n === waiting.length ? 0 : n })}>
              Generate {n} image{n === 1 ? "" : "s"}
            </Button>
            <span className="text-sm text-slate-600">
              ≈ ${estimate.toFixed(2)}{rate ? ` · ₹${(estimate * rate).toFixed(0)}` : ""} (${data.price_per_image_usd} each)
            </span>
          </>
        )}
        <Button variant="ghost" disabled={!all.length} onClick={() => copy(all.map((c) => `${c.position}. ${c.scene_title}\n${c.prompt}`).join("\n\n"), "all prompts")}>
          Copy all prompts
        </Button>
        <Button variant="ghost" onClick={() => { load(); router.refresh(); }}>Refresh</Button>
      </div>
      {msg && <p role="status" className="mt-2 text-sm">{msg}</p>}
      <ul className="mt-3 max-h-[32rem] divide-y divide-slate-100 overflow-y-auto rounded-xl border border-slate-200">
        {all.map((c) => (
          <li key={c.id} className="p-2 text-sm">
            <div className="flex flex-wrap items-center gap-2">
              <span className="w-8 shrink-0 text-right text-slate-500">{c.position}</span>
              <span className="min-w-0 flex-1 truncate font-semibold">{c.scene_title || `#${c.id}`}</span>
              <Badge value={c.status} />
              {c.status === "failed" && !manual && (
                <Button variant="ghost" disabled={busy || !data.can_generate} onClick={() => generate({ image_ids: [c.id] })}>Retry</Button>
              )}
              {c.status !== "generating" && (
                <label className="cursor-pointer rounded-lg border border-slate-300 px-2 py-1 text-xs font-semibold hover:bg-slate-50">
                  Upload picture
                  <input
                    type="file"
                    accept="image/*"
                    className="sr-only"
                    disabled={busy}
                    aria-label={`Upload a picture for scene ${c.position}`}
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      e.target.value = "";
                      if (file) upload(c, file);
                    }}
                  />
                </label>
              )}
            </div>
            {c.error && <p className="mt-1 pl-10 text-xs text-rose-700">{c.error}</p>}
            <details className="mt-1 pl-10">
              <summary className="cursor-pointer text-xs text-slate-500">Prompt</summary>
              <p className="mt-1 whitespace-pre-wrap text-xs">{c.prompt}</p>
              <Button variant="ghost" className="mt-1" onClick={() => copy(c.prompt, `prompt ${c.position}`)}>Copy prompt</Button>
            </details>
          </li>
        ))}
        {!all.length && <li className="p-3 text-sm text-slate-500">No scene prompts yet. Click “Write scene prompts”.</li>}
      </ul>
    </Card>
  );
}
