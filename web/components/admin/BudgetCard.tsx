"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";
import type { BudgetSettings } from "@/lib/types";
import { Button, Card } from "./ui";

const field = "w-32 rounded-lg border border-slate-300 px-2 py-1.5 text-sm";
const inr = (n: number) => `₹${Math.round(n).toLocaleString("en-IN")}`;

/** Monthly cap for every paid API call (AI text, AI images, web search). */
export default function BudgetCard({ initial }: { initial: BudgetSettings }) {
  const router = useRouter();
  const [cap, setCap] = useState(String(initial.cap_inr));
  const [rate, setRate] = useState(String(initial.usd_inr_rate));
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const pct = Math.round(initial.ratio * 100);

  async function save() {
    setBusy(true);
    setMsg("");
    try {
      await api("/api/admin/budget", { method: "PUT", body: { monthly_inr: Number(cap), usd_inr_rate: Number(rate) } });
      setMsg("Saved");
      router.refresh();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card title="Monthly API budget">
      <p className="mb-3 text-sm text-slate-600">
        The most Crayonlark may spend on paid API calls (AI text, AI images, web search) per calendar month. You get a Telegram warning at 80 %; at 100 % paid calls stop until next month or until you raise it. Set it to 0 to block all paid calls. Free modes (offline, manual) never count.
      </p>
      <p className="mb-3 text-sm">
        {initial.month}: <strong>{inr(initial.spent_inr)}</strong> of {inr(initial.cap_inr)} used ({pct} %)
      </p>
      <div className="flex flex-wrap items-end gap-4">
        <label className="text-sm">
          <span className="block font-semibold">Budget per month (₹)</span>
          <input type="number" min={0} step={100} value={cap} onChange={(e) => setCap(e.target.value)} className={field} />
        </label>
        <label className="text-sm">
          <span className="block font-semibold">₹ per US$</span>
          <input type="number" min={1} step={0.5} value={rate} onChange={(e) => setRate(e.target.value)} className={field} />
        </label>
        <Button onClick={save} disabled={busy || cap === "" || rate === ""}>
          {busy ? "…" : "Save"}
        </Button>
      </div>
      <p className="mt-2 text-xs text-slate-500">Providers bill in US$; this rate turns their prices into rupees for the cap.</p>
      {msg && <p role="status" className="mt-2 text-sm">{msg}</p>}
    </Card>
  );
}
