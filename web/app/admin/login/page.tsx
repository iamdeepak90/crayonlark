"use client";

import Image from "next/image";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, ApiError } from "@/lib/api";

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
    <main className="grid min-h-dvh place-items-center bg-cream px-4">
      <form onSubmit={submit} className="w-full max-w-sm space-y-4 rounded-2xl bg-white p-8 shadow">
        <div className="flex items-center gap-3">
          <Image src="/brand/lark.svg" alt="" width={44} height={44} />
          <h1 className="text-2xl font-bold">Crayonlark Admin</h1>
        </div>
        <label className="block text-sm font-semibold">
          Email
          <input className="mt-1 w-full rounded-lg border px-3 py-2" type="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label className="block text-sm font-semibold">
          Password
          <input className="mt-1 w-full rounded-lg border px-3 py-2" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
        </label>
        {needTotp && (
          <label className="block text-sm font-semibold">
            2FA code
            <input className="mt-1 w-full rounded-lg border px-3 py-2 tracking-widest" inputMode="numeric" autoComplete="one-time-code" autoFocus value={totp} onChange={(e) => setTotp(e.target.value)} />
          </label>
        )}
        {error && <p role="alert" className="text-sm text-rose-700">{error}</p>}
        <button disabled={busy} className="w-full rounded-lg bg-ink py-2 font-semibold text-white disabled:opacity-50">
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </main>
  );
}
