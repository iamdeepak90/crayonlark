"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";
import { Button, Card } from "./ui";

export default function NicheForm() {
  const router = useRouter();
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const input = "mt-1 w-full rounded-lg border border-slate-300 px-3 py-2";

  async function research(form: FormData) {
    setBusy(true);
    setMsg("");
    try {
      await api("/api/admin/research", { body: { theme: form.get("theme"), competitor_notes: form.get("competitor_notes") } });
      setMsg("Research agent started. Ideas appear here in a minute.");
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "failed");
    } finally {
      setBusy(false);
    }
  }

  async function add(form: FormData) {
    setBusy(true);
    setMsg("");
    try {
      await api("/api/admin/niches", { body: Object.fromEntries(form.entries()) });
      router.refresh();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <Card title="Ask the research agent">
        <form action={research} className="space-y-2">
          <label className="block text-sm font-semibold">
            Theme
            <input name="theme" required className={input} placeholder="ocean animals" />
          </label>
          <label className="block text-sm font-semibold">
            Competitor notes (optional, paste your own research)
            <textarea name="competitor_notes" rows={4} className={input} />
          </label>
          <Button disabled={busy}>Suggest 10 niches</Button>
        </form>
      </Card>
      <Card title="Add a niche by hand">
        <form action={add} className="space-y-2">
          {[["theme", "Theme"], ["name", "Niche name"], ["age_range", "Age range"], ["angle", "Angle"], ["risks", "Risks"], ["seasonality", "Seasonality"]].map(([k, l]) => (
            <label key={k} className="block text-sm font-semibold">
              {l}
              <input name={k} required={k === "theme" || k === "name"} defaultValue={k === "age_range" ? "4-8" : ""} className={input} />
            </label>
          ))}
          <Button disabled={busy}>Add niche</Button>
        </form>
      </Card>
      {msg && <p role="status" className="text-sm">{msg}</p>}
    </div>
  );
}
