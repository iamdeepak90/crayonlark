"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";
import { Button } from "./ui";

/** Small client button that POSTs to the API and refreshes the page. */
export default function ActionButton({
  path,
  body,
  label,
  variant = "primary",
  confirm,
  method = "POST",
}: {
  path: string;
  body?: unknown;
  label: string;
  variant?: "primary" | "ghost" | "danger" | "ok";
  confirm?: string;
  method?: string;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  return (
    <span className="inline-flex flex-col">
      <Button
        variant={variant}
        disabled={busy}
        onClick={async () => {
          if (confirm && !window.confirm(confirm)) return;
          setBusy(true);
          setError("");
          try {
            await api(path, { method, body: body ?? {} });
            router.refresh();
          } catch (e) {
            setError(e instanceof Error ? e.message : "failed");
          } finally {
            setBusy(false);
          }
        }}
      >
        {busy ? "…" : label}
      </Button>
      {error && <span role="alert" className="mt-1 max-w-xs text-xs text-rose-700">{error}</span>}
    </span>
  );
}
