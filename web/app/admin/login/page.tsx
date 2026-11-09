"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Monogram } from "@/components/admin/ui";
import { api, ApiError } from "@/lib/api";

const INPUT = "mt-1.5 block h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [totp, setTotp] = useState("");
  const [needTotp, setNeedTotp] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api("/api/auth/login", { body: { email, password, totp: totp || undefined } });
      router.replace("/");
      router.refresh();
    } catch (err) {
      if (err instanceof ApiError && err.message === "totp_required") {
        setNeedTotp(true);
        setError("Enter the 6-digit code from your authenticator app.");
      } else setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="grid min-h-dvh place-items-center bg-slate-50 px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center text-center">
          <Monogram className="h-10 w-10 text-base" />
          <h1 className="mt-4 text-xl font-semibold tracking-tight">Crayonlark Admin</h1>
          <p className="mt-1 text-sm text-slate-500">Sign in to continue</p>
        </div>
        <form onSubmit={submit} className="space-y-4 rounded-xl border border-slate-200 bg-white p-6">
          <label className="block text-sm font-medium">
            Email
            <input className={INPUT} type="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>
          <label className="block text-sm font-medium">
            Password
            <input className={INPUT} type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
          </label>
          {needTotp && (
            <label className="block text-sm font-medium">
              2FA code
              <input className={`${INPUT} tracking-widest`} inputMode="numeric" autoComplete="one-time-code" autoFocus value={totp} onChange={(e) => setTotp(e.target.value)} />
            </label>
          )}
          {error && (
            <p role="alert" className="text-sm text-rose-600">
              {error}
            </p>
          )}
          <button disabled={busy} className="h-10 w-full rounded-md bg-ink text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-50">
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </main>
  );
}
