"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";

/** Upload the KDP royalties report (CSV). Re-uploading the same file only skips rows already imported. */
export default function KdpCsvUpload() {
  const router = useRouter();
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function send(file: File) {
    setBusy(true);
    setMsg("");
    setError("");
    try {
      const form = new FormData();
      form.append("file", file);
      const r = await api<{ rows: number; added: number; skipped: number }>("/api/admin/sales/kdp-import", { form });
      setMsg(`${file.name}: ${r.rows} rows read, ${r.added} added, ${r.skipped} skipped (already imported).`);
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "upload failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <p className="text-sm text-slate-600">
        KDP → Reports → Royalties (or Prior months) → download, save as CSV, upload here. Re-uploading the same file is safe.
      </p>
      <label className="mt-2 inline-block cursor-pointer rounded-lg bg-ink px-3 py-1.5 text-sm font-semibold text-white">
        {busy ? "Importing…" : "Upload KDP CSV"}
        <input
          type="file"
          accept=".csv,text/csv"
          className="sr-only"
          disabled={busy}
          onChange={(e) => {
            const file = e.target.files?.[0];
            e.target.value = "";
            if (file) send(file);
          }}
        />
      </label>
      {msg && <p role="status" className="mt-2 text-sm text-emerald-800">{msg}</p>}
      {error && <p role="alert" className="mt-2 text-sm text-rose-700">{error}</p>}
    </div>
  );
}
