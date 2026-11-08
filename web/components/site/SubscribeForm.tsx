"use client";

import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import { Honeypot } from "./Honeypot";
import { useStartedAt } from "./useStartedAt";

type Status = { kind: "idle" | "sending" | "done" | "error"; message?: string };

/** Email sign-up for the free printable (double opt-in: the API sends a confirmation email). */
export function SubscribeForm() {
  const [email, setEmail] = useState("");
  const [website, setWebsite] = useState("");
  const [status, setStatus] = useState<Status>({ kind: "idle" });
  const startedAt = useStartedAt();

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setStatus({ kind: "sending" });
    try {
      const res = await api<{ ok: boolean; message: string }>("/api/public/subscribe", {
        body: { email, website, started_at: startedAt.current },
      });
      setStatus({ kind: "done", message: res.message });
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Something went wrong. Please try again in a moment.";
      setStatus({ kind: "error", message });
    }
  }

  if (status.kind === "done") {
    return (
      <p role="status" className="rounded-2xl bg-sky-soft p-4 font-semibold">
        {status.message}
      </p>
    );
  }

  return (
    <form onSubmit={onSubmit} method="post" className="relative flex flex-col gap-3">
      <label htmlFor="subscribe-email" className="font-semibold">
        Your email address
      </label>
      <div className="flex flex-col gap-3 sm:flex-row">
        <input
          id="subscribe-email"
          type="email"
          name="email"
          required
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
          className="min-h-12 w-full min-w-0 flex-1 rounded-full border-2 border-ink/20 bg-white px-5 text-lg focus:border-sky"
        />
        <button
          type="submit"
          disabled={status.kind === "sending"}
          className="min-h-12 rounded-full bg-coral-dark px-6 font-display text-lg font-semibold text-white hover:bg-ink disabled:opacity-60"
        >
          {status.kind === "sending" ? "Sending…" : "Send me the printable"}
        </button>
      </div>
      <Honeypot value={website} onChange={setWebsite} />
      <p className="text-sm text-ink-soft">
        We&apos;ll email you a link to confirm. No spam, and you can unsubscribe any time.
      </p>
      {status.kind === "error" && (
        <p role="alert" className="font-semibold text-coral-dark">
          {status.message}
        </p>
      )}
    </form>
  );
}
