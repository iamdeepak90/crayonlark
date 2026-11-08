"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { ImageItem } from "@/lib/types";
import { Badge, Button } from "./ui";

type Filter = "all" | "pending" | "approved" | "rejected";

/**
 * Keyboard: ←/→/↑/↓ move · A or Y keep · R or N reject · Z zoom 100% · Esc close zoom
 */
export default function ImageGrid({ bookId, status, initial, limits }: { bookId: number; status: string; initial: ImageItem[]; limits: { min: number; max: number } }) {
  const router = useRouter();
  const [images, setImages] = useState(initial);
  const [filter, setFilter] = useState<Filter>("all");
  const [focus, setFocus] = useState(0);
  const [zoom, setZoom] = useState(false);
  const [variant, setVariant] = useState<"original" | "cleaned">("original");
  const [msg, setMsg] = useState("");
  const gridRef = useRef<HTMLUListElement>(null);

  const shown = useMemo(() => (filter === "all" ? images : images.filter((i) => i.approval === filter)), [images, filter]);
  const approved = images.filter((i) => i.approval === "approved").length;
  const current = shown[Math.min(focus, shown.length - 1)];

  const decide = useCallback(async (img: ImageItem | undefined, approve: boolean) => {
    if (!img) return;
    setImages((all) => all.map((i) => (i.id === img.id ? { ...i, approval: approve ? "approved" : "rejected" } : i)));
    try {
      await api(`/api/admin/images/${img.id}/decision`, { body: { approve } });
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "failed");
      setImages((all) => all.map((i) => (i.id === img.id ? { ...i, approval: img.approval } : i)));
    }
  }, []);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      const cols = Math.max(1, Math.round((gridRef.current?.clientWidth ?? 1000) / 210));
      const move = (d: number) => {
        e.preventDefault();
        setFocus((f) => Math.max(0, Math.min(shown.length - 1, f + d)));
      };
      switch (e.key) {
        case "ArrowRight": return move(1);
        case "ArrowLeft": return move(-1);
        case "ArrowDown": return move(cols);
        case "ArrowUp": return move(-cols);
        case "a": case "y": decide(current, true); return move(1);
        case "r": case "n": decide(current, false); return move(1);
        case "z": setZoom((z) => !z); return;
        case "Escape": setZoom(false); return;
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [shown.length, current, decide]);

  useEffect(() => {
    document.getElementById(`img-${current?.id}`)?.scrollIntoView({ block: "nearest" });
  }, [current?.id]);

  async function approveSet() {
    setMsg("");
    try {
      const r = await api<{ approved: number }>(`/api/admin/books/${bookId}/approve-images`, { method: "POST", body: {} });
      setMsg(`Approved ${r.approved} images. Cleanup started.`);
      router.push(`/books/${bookId}`);
      router.refresh();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "failed");
    }
  }

  return (
    <div>
      <div className="sticky top-0 z-10 mb-4 flex flex-wrap items-center gap-3 rounded-xl bg-white p-3 shadow-sm">
        <div role="tablist" aria-label="Filter" className="flex gap-1">
          {(["all", "pending", "approved", "rejected"] as Filter[]).map((f) => (
            <button key={f} role="tab" aria-selected={filter === f} onClick={() => { setFilter(f); setFocus(0); }} className={`rounded-lg px-2 py-1 text-sm font-semibold ${filter === f ? "bg-ink text-white" : "bg-slate-100"}`}>
              {f} ({f === "all" ? images.length : images.filter((i) => i.approval === f).length})
            </button>
          ))}
        </div>
        <span className={`text-sm font-semibold ${approved < limits.min || approved > limits.max ? "text-amber-700" : "text-emerald-700"}`}>
          {approved} approved (need {limits.min}–{limits.max})
        </span>
        <span className="hidden text-xs text-slate-500 lg:inline">Keys: arrows move · A keep · R reject · Z zoom 100%</span>
        <div className="ml-auto">
          <Button variant="ok" disabled={status !== "awaiting_image_approval"} onClick={approveSet} title={status !== "awaiting_image_approval" ? "Book is not waiting for image approval" : ""}>
            Approve image set
          </Button>
        </div>
        {msg && <p role="status" className="w-full text-sm">{msg}</p>}
      </div>
      <ul ref={gridRef} className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {shown.map((img, idx) => {
          const q = img.qa;
          return (
            <li key={img.id} id={`img-${img.id}`} onClick={() => setFocus(idx)} className={`rounded-xl bg-white p-2 shadow-sm ring-2 ${idx === focus ? "ring-sky" : img.approval === "approved" ? "ring-emerald-500" : img.approval === "rejected" ? "ring-rose-400" : "ring-transparent"}`}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={`/api/admin/images/${img.id}/file?variant=thumb`} alt={img.scene_title || `image ${img.id}`} loading="lazy" className={`aspect-[3/4] w-full rounded bg-white object-contain ${img.approval === "rejected" ? "opacity-40" : ""}`} />
              <div className="mt-1 flex items-center justify-between gap-1 text-xs">
                <span className="truncate font-semibold">{img.scene_title || `#${img.id}`}</span>
                <span title="QA score" className={img.qa_recommendation === "reject" ? "font-bold text-rose-700" : "text-slate-600"}>
                  {img.qa_score ?? "…"}
                </span>
              </div>
              {(q.failures?.length || img.vision?.issues?.length) ? (
                <p className="mt-1 line-clamp-2 text-xs text-rose-700">{[...(q.failures ?? []), ...(img.vision?.issues ?? [])].join("; ")}</p>
              ) : null}
              <div className="mt-2 flex gap-1">
                <Button variant={img.approval === "approved" ? "ok" : "ghost"} className="flex-1" aria-label={`Keep image ${img.id}`} onClick={() => decide(img, true)}>
                  ✅
                </Button>
                <Button variant={img.approval === "rejected" ? "danger" : "ghost"} className="flex-1" aria-label={`Reject image ${img.id}`} onClick={() => decide(img, false)}>
                  ❌
                </Button>
              </div>
            </li>
          );
        })}
      </ul>
      {!shown.length && <p className="text-slate-500">No images here yet. Upload some on the book page.</p>}
      {zoom && current && (
        <div role="dialog" aria-modal="true" aria-label="Zoom 100%" className="fixed inset-0 z-50 overflow-auto bg-black/80 p-4" onClick={() => setZoom(false)}>
          <div className="mb-2 flex items-center gap-3 text-white" onClick={(e) => e.stopPropagation()}>
            <strong>{current.scene_title}</strong>
            <Badge value={current.approval} />
            <button className="underline" onClick={() => setVariant((v) => (v === "original" ? "cleaned" : "original"))} disabled={!current.has_cleaned}>
              showing {variant}
            </button>
            <span className="text-sm opacity-80">QA {JSON.stringify({ grey: current.qa.grey_ratio, fill: current.qa.black_fill, line: current.qa.line_px_at_print })}</span>
          </div>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={`/api/admin/images/${current.id}/file?variant=${current.has_cleaned ? variant : "original"}`} alt={current.scene_title} className="max-w-none bg-white" />
        </div>
      )}
    </div>
  );
}
