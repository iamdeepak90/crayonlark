"use client";

import { useId, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { Honeypot } from "./Honeypot";
import { useStartedAt } from "./useStartedAt";

type Status = { kind: "idle" | "sending" | "done" | "error"; message?: string };

/**
 * Email sign-up for the free printable (double opt-in: the API sends a confirmation email).
 * `variant="footer"` is the compact version on the dark footer.
 */
export function SubscribeForm({ variant = "default", button = "Send my pages" }: { variant?: "default" | "footer"; button?: string }) {
  const id = useId();
  const [email, setEmail] = useState("");
  const [website, setWebsite] = useState("");
  const [status, setStatus] = useState<Status>({ kind: "idle" });
  const startedAt = useStartedAt();
  const footer = variant === "footer";

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
      <p role="status" className={`rounded-2xl p-4 text-sm font-semibold ${footer ? "bg-white/10 text-white" : "bg-white ring-1 ring-line"}`}>
        {status.message}
      </p>
    );
  }

  return (
    <form onSubmit={onSubmit} method="post" className="relative">
      <label htmlFor={id} className="sr-only">
        {footer ? "Email address for free pages" : "Your email address"}
      </label>
      <div className={`flex gap-2 ${footer ? "" : "max-w-md flex-col gap-3 sm:flex-row"}`}>
        <input
          id={id}
          type="email"
          name="email"
          required
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder={footer ? "Email address" : "Your email address"}
          className={
            footer
              ? "min-w-0 flex-1 rounded-full border-0 bg-white/10 px-4 py-2.5 text-sm text-white placeholder:text-white/50 focus:outline-none focus:ring-2 focus:ring-sun-400"
              : "min-w-0 flex-1 rounded-full border-0 bg-white px-5 py-3 ring-1 ring-line placeholder:text-muted/70 focus:outline-none focus:ring-2 focus:ring-sky-400"
          }
        />
        <button
          type="submit"
          disabled={status.kind === "sending"}
          className={
            footer
              ? "rounded-full bg-sun-400 px-4 py-2.5 text-sm font-semibold text-ink transition hover:bg-sun-100 disabled:opacity-60"
              : "rounded-full bg-ink px-6 py-3 font-semibold text-white transition hover:bg-ink/85 disabled:opacity-60"
          }
        >
          {status.kind === "sending" ? "Sending…" : footer ? "Join" : button}
        </button>
      </div>
      <Honeypot value={website} onChange={setWebsite} />
      {!footer && <p className="mt-3 text-sm text-muted">We&apos;ll email you a link to confirm. No spam, unsubscribe anytime.</p>}
      {status.kind === "error" && (
        <p role="alert" className={`mt-2 text-sm font-semibold ${footer ? "text-coral-100" : "text-coral-600"}`}>
          {status.message}
        </p>
      )}
    </form>
  );
}
