"use client";

import { useRouter } from "next/navigation";
import { LoaderCircle } from "lucide-react";
import { useState } from "react";
import { api } from "@/lib/api";
import { Button, type ButtonProps } from "@/components/ui/button";

/** Small client button that POSTs to the API and refreshes the page. */
export default function ActionButton({
  path,
  body,
  label,
  variant = "default",
  confirm,
  method = "POST",
  success,
  icon,
}: {
  path: string;
  body?: unknown;
  label: string;
  variant?: ButtonProps["variant"];
  confirm?: string;
  method?: string;
  /** Shown after the call succeeds, e.g. "Queued: done in a minute." */
  success?: string;
  /** A lucide icon shown before the label. */
  icon?: React.ReactNode;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState("");
  return (
    <span className="inline-flex flex-col">
      <Button
        variant={variant}
        disabled={busy}
        onClick={async () => {
          if (confirm && !window.confirm(confirm)) return;
          setBusy(true);
          setError("");
          setDone("");
          try {
            await api(path, { method, body: body ?? {} });
            if (success) setDone(success);
            router.refresh();
          } catch (e) {
            setError(e instanceof Error ? e.message : "failed");
          } finally {
            setBusy(false);
          }
        }}
      >
        {busy ? <LoaderCircle className="animate-spin" aria-hidden="true" /> : icon}
        {label}
      </Button>
      {done && <span role="status" className="mt-1 max-w-xs text-xs text-emerald-700 dark:text-emerald-400">{done}</span>}
      {error && <span role="alert" className="mt-1 max-w-xs text-xs text-destructive">{error}</span>}
    </span>
  );
}
