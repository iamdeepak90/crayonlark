"use client";

import { LoaderCircle, Undo2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

/** Send a book back to the listing agent, with an optional note on what to change. */
export function SendBackButton({ bookId }: { bookId: number }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  return (
    <Button
      variant="outline"
      disabled={busy}
      onClick={async () => {
        const note = window.prompt("What should change? (optional; the listing text is written again)");
        if (note === null) return;
        setBusy(true);
        try {
          await api(`/api/admin/books/${bookId}/etsy/send-back`, { body: { note } });
          toast.success("Sent back: the listing text is being written again");
          router.refresh();
        } catch (err) {
          toast.error("Send back failed", { description: err instanceof Error ? err.message : undefined });
        } finally {
          setBusy(false);
        }
      }}
    >
      {busy ? <LoaderCircle className="animate-spin" aria-hidden="true" /> : <Undo2 aria-hidden="true" />}
      Send back
    </Button>
  );
}
