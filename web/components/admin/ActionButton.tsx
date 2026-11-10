"use client";

import { useRouter } from "next/navigation";
import { LoaderCircle } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
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
  return (
    <Button
      variant={variant}
      disabled={busy}
      onClick={async () => {
        if (confirm && !window.confirm(confirm)) return;
        setBusy(true);
        try {
          await api(path, { method, body: body ?? {} });
          toast.success(success ?? `${label}: done`);
          router.refresh();
        } catch (e) {
          toast.error(`${label} failed`, { description: e instanceof Error ? e.message : undefined });
        } finally {
          setBusy(false);
        }
      }}
    >
      {busy ? <LoaderCircle className="animate-spin" aria-hidden="true" /> : icon}
      {label}
    </Button>
  );
}
