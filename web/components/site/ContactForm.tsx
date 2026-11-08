"use client";

import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import { Honeypot } from "./Honeypot";
import { Turnstile } from "./Turnstile";
import { useStartedAt } from "./useStartedAt";

const TURNSTILE_SITE_KEY = process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY ?? "";

type Status = { kind: "idle" | "sending" | "done" | "error"; message?: string };

const inputClass = "w-full min-w-0 rounded-2xl border-2 border-ink/20 bg-white px-4 py-3 text-lg focus:border-sky";

export function ContactForm() {
  const [form, setForm] = useState({ name: "", email: "", message: "" });
  const [website, setWebsite] = useState("");
  const [token, setToken] = useState("");
  const [turnstileKey, setTurnstileKey] = useState(0);
  const [status, setStatus] = useState<Status>({ kind: "idle" });
  const startedAt = useStartedAt();

  const set = (field: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm({ ...form, [field]: e.target.value });

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setStatus({ kind: "sending" });
    try {
      await api("/api/public/contact", {
        body: {
          ...form,
          website,
          started_at: startedAt.current,
          ...(TURNSTILE_SITE_KEY ? { turnstile_token: token } : {}),
        },
      });
      setStatus({ kind: "done" });
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Something went wrong. Please try again in a moment.";
      setStatus({ kind: "error", message });
      if (TURNSTILE_SITE_KEY) {
        setToken(""); // a token can only be used once
        setTurnstileKey((k) => k + 1);
      }
    }
  }

  if (status.kind === "done") {
    return (
      <p role="status" className="rounded-2xl bg-sky-soft p-5 text-lg font-semibold">
        Thank you! Your message is on its way. We usually reply within a few days.
      </p>
    );
  }

  return (
    <form onSubmit={onSubmit} method="post" className="relative flex max-w-xl flex-col gap-5">
      <div className="flex flex-col gap-2">
        <label htmlFor="contact-name" className="font-semibold">
          Your name
        </label>
        <input id="contact-name" name="name" required autoComplete="name" maxLength={200} value={form.name} onChange={set("name")} className={inputClass} />
      </div>
      <div className="flex flex-col gap-2">
        <label htmlFor="contact-email" className="font-semibold">
          Email
        </label>
        <input id="contact-email" name="email" type="email" required autoComplete="email" value={form.email} onChange={set("email")} className={inputClass} />
      </div>
      <div className="flex flex-col gap-2">
        <label htmlFor="contact-message" className="font-semibold">
          Message
        </label>
        <textarea id="contact-message" name="message" required rows={6} maxLength={5000} value={form.message} onChange={set("message")} className={inputClass} />
      </div>
      <Honeypot value={website} onChange={setWebsite} />
      {TURNSTILE_SITE_KEY && <Turnstile key={turnstileKey} siteKey={TURNSTILE_SITE_KEY} onToken={setToken} />}
      <div>
        <button
          type="submit"
          disabled={status.kind === "sending"}
          className="min-h-12 rounded-full bg-coral-dark px-8 font-display text-lg font-semibold text-white hover:bg-ink disabled:opacity-60"
        >
          {status.kind === "sending" ? "Sending…" : "Send message"}
        </button>
      </div>
      {status.kind === "error" && (
        <p role="alert" className="font-semibold text-coral-dark">
          {status.message}
        </p>
      )}
    </form>
  );
}
