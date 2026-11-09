"use client";

import { useState } from "react";
import { api } from "@/lib/api";

/**
 * Unsubscribe needs one click on the page (not on page load), so email link scanners that
 * open every link can't unsubscribe people by accident.
 */
export function UnsubscribeButton({ token }: { token: string }) {
  const [state, setState] = useState<"idle" | "sending" | "done" | "error">("idle");

  async function unsubscribe() {
    setState("sending");
    try {
      await api(`/api/public/unsubscribe?token=${encodeURIComponent(token)}`);
      setState("done");
    } catch {
      setState("error");
    }
  }

  if (state === "done") {
    return (
      <p role="status" className="rounded-lg bg-sun-50 p-4 text-lg font-semibold">
        You&apos;re unsubscribed. We won&apos;t email you again. Thanks for coloring with us!
      </p>
    );
  }
  return (
    <div className="flex flex-col items-start gap-3">
      <button
        type="button"
        onClick={unsubscribe}
        disabled={state === "sending"}
        className="rounded-lg bg-coral-600 px-6 py-3 font-semibold text-white transition hover:bg-coral-700 disabled:opacity-60"
      >
        {state === "sending" ? "Unsubscribing…" : "Unsubscribe me"}
      </button>
      {state === "error" && (
        <p role="alert" className="font-semibold text-coral-600">
          That link didn&apos;t work. It may be old or already used. You can also write to us on the contact page and we&apos;ll remove you.
        </p>
      )}
    </div>
  );
}
