"use client";

import { Check, LoaderCircle, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

/** Approve or reject a proposed niche. Approving creates its book and starts the scene prompts. */
export default function NicheDecision({ id, name }: { id: number; name: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState<"approve" | "reject" | null>(null);

  async function decide(approve: boolean) {
    setBusy(approve ? "approve" : "reject");
    try {
      const r = await api<{ book?: { id: number; title: string } }>(`/api/admin/niches/${id}/decision`, { body: { approve } });
      if (approve && r.book) {
        const book = r.book;
        toast.success(`Book created: ${book.title}`, {
          description: "The concept agent is writing the scene prompts now.",
          action: { label: "Open book", onClick: () => router.push(`/books/${book.id}`) },
        });
      } else {
        toast(approve ? `Approved: ${name}` : `Rejected: ${name}`);
      }
      router.refresh();
    } catch (e) {
      toast.error(approve ? "Approve failed" : "Reject failed", { description: e instanceof Error ? e.message : undefined });
    } finally {
      setBusy(null);
    }
  }

  return (
    <>
      <Button variant="success" size="sm" disabled={busy !== null} onClick={() => decide(true)}>
        {busy === "approve" ? <LoaderCircle className="animate-spin" aria-hidden="true" /> : <Check aria-hidden="true" />}
        Approve & create book
      </Button>
      <Button variant="outline" size="sm" disabled={busy !== null} onClick={() => decide(false)}>
        {busy === "reject" ? <LoaderCircle className="animate-spin" aria-hidden="true" /> : <X aria-hidden="true" />}
        Reject
      </Button>
    </>
  );
}
