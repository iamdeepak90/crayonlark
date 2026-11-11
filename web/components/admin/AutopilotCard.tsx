"use client";

import { AlertTriangle, Bot, LoaderCircle } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import type { AutopilotStatus } from "@/lib/types";

/** On/off for the Autopilot (everything between my two approvals). Its tuning is fixed in code. */
export default function AutopilotCard({ status }: { status: AutopilotStatus }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  async function toggle() {
    const next = !status.enabled;
    if (!next && !window.confirm("Switch the Autopilot off? New books stop being made until you switch it on again.")) return;
    setBusy(true);
    try {
      await api("/api/admin/autopilot", { method: "PUT", body: { enabled: next } });
      toast.success(next ? "Autopilot is on" : "Autopilot is off");
      router.refresh();
    } catch (e) {
      toast.error("Could not switch", { description: e instanceof Error ? e.message : undefined });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-2 rounded-lg border bg-card p-4 text-sm shadow-xs">
      <div className="flex flex-wrap items-center gap-3">
        <Bot className="size-4 shrink-0" aria-hidden="true" />
        <p className="min-w-0 flex-1">
          <span className="font-medium">Autopilot {status.enabled ? "on" : "off"}.</span>{" "}
          <span className="text-muted-foreground">
            {status.enabled
              ? `It makes books by itself (${status.stock} in progress, keeps about ${status.keep_books}). You only approve them.`
              : "No new books are being made."}
          </span>
        </p>
        <Button size="sm" variant={status.enabled ? "ghost" : "success"} disabled={busy} onClick={toggle}>
          {busy && <LoaderCircle className="animate-spin" aria-hidden="true" />}
          {status.enabled ? "Switch off" : "Switch on"}
        </Button>
      </div>
      {status.enabled && status.problems.length > 0 && (
        <ul role="alert" className="flex flex-col gap-1 text-amber-900 dark:text-amber-200">
          {status.problems.map((p) => (
            <li key={p} className="flex gap-2">
              <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden="true" /> {p}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
