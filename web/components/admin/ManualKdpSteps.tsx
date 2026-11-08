"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";
import { Button } from "./ui";

/** The KDP steps I do by hand: upload the pack, order a proof, go live (with ASIN). */
export default function ManualKdpSteps({ bookId, status }: { bookId: number; status: string }) {
  const router = useRouter();
  const [asin, setAsin] = useState("");
  const [url, setUrl] = useState("");
  const [err, setErr] = useState("");

  async function go(action: string) {
    setErr("");
    try {
      const q = action === "live" ? `?asin=${encodeURIComponent(asin)}&amazon_url=${encodeURIComponent(url)}` : "";
      await api(`/api/admin/books/${bookId}/status/${action}${q}`, { method: "POST", body: {} });
      router.refresh();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "failed");
    }
  }

  if (status === "kdp_pack_ready") return <Button onClick={() => go("kdp-uploaded")}>I uploaded it to KDP</Button>;
  if (status === "kdp_uploaded" || status === "proof_ordered")
    return (
      <div className="flex flex-wrap items-end gap-2">
        {status === "kdp_uploaded" && (
          <Button variant="ghost" onClick={() => go("proof-ordered")}>
            Proof ordered
          </Button>
        )}
        <input aria-label="ASIN" placeholder="ASIN" value={asin} onChange={(e) => setAsin(e.target.value)} className="w-32 rounded-lg border px-2 py-1 text-sm" />
        <input aria-label="Amazon URL" placeholder="Amazon URL" value={url} onChange={(e) => setUrl(e.target.value)} className="w-64 rounded-lg border px-2 py-1 text-sm" />
        <Button variant="ok" onClick={() => go("live")}>
          Mark live
        </Button>
        {err && <span className="text-sm text-rose-700">{err}</span>}
      </div>
    );
  return null;
}
