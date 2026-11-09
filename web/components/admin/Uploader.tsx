"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";

/** Manual drop: upload images generated in the ChatGPT/Gemini apps. */
export default function Uploader({ bookId }: { bookId: number }) {
  const router = useRouter();
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const [drag, setDrag] = useState(false);

  async function send(files: FileList | File[]) {
    const list = Array.from(files).filter((f) => f.type.startsWith("image/"));
    if (!list.length) return;
    setBusy(true);
    setMsg(`Uploading ${list.length} file(s)…`);
    let ok = 0;
    const errors: string[] = [];
    // batches of 10 keep each request small
    for (let i = 0; i < list.length; i += 10) {
      const form = new FormData();
      list.slice(i, i + 10).forEach((f) => form.append("files", f));
      try {
        const r = await api<{ created: number[]; errors: string[] }>(`/api/admin/books/${bookId}/images`, { form });
        ok += r.created.length;
        errors.push(...r.errors);
      } catch (e) {
        errors.push(e instanceof Error ? e.message : "upload failed");
      }
    }
    setMsg(`Uploaded ${ok}. QA is running in the background.${errors.length ? " Errors: " + errors.join("; ") : ""}`);
    setBusy(false);
    router.refresh();
  }

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setDrag(true);
      }}
      onDragLeave={() => setDrag(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDrag(false);
        send(e.dataTransfer.files);
      }}
      className={`rounded-xl border border-dashed p-6 text-center ${drag ? "border-sky bg-sky-soft" : "border-slate-300 bg-white"}`}
    >
      <p className="font-semibold">Drop PNG/JPG/WebP images here</p>
      <p className="text-sm text-slate-500">or</p>
      <label className="mt-2 inline-block cursor-pointer rounded-lg bg-ink px-3 py-1.5 text-sm font-semibold text-white">
        Choose files
        <input type="file" accept="image/*" multiple className="sr-only" disabled={busy} onChange={(e) => e.target.files && send(e.target.files)} />
      </label>
      {msg && <p className="mt-3 text-sm" role="status">{msg}</p>}
    </div>
  );
}
