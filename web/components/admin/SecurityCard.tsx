"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { Button, Card } from "./ui";

export default function SecurityCard({ email, totpEnabled }: { email: string; totpEnabled: boolean }) {
  const [enabled, setEnabled] = useState(totpEnabled);
  const [setup, setSetup] = useState<{ secret: string; qr: string } | null>(null);
  const [code, setCode] = useState("");
  const [msg, setMsg] = useState("");

  return (
    <Card title="Security (2FA)">
      <p className="text-sm">Signed in as {email}. Two-factor login is <strong>{enabled ? "on" : "off"}</strong>.</p>
      {!enabled && !setup && (
        <Button className="mt-3" onClick={async () => setSetup(await api("/api/auth/totp/setup", { method: "POST", body: {} }))}>
          Set up authenticator app
        </Button>
      )}
      {setup && !enabled && (
        <div className="mt-3 space-y-2">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={setup.qr} alt="QR code for your authenticator app" width={180} height={180} />
          <p className="font-mono text-xs break-all">{setup.secret}</p>
          <input aria-label="6-digit code" value={code} onChange={(e) => setCode(e.target.value)} placeholder="123456" inputMode="numeric" className="rounded-lg border px-3 py-1.5" />
          <Button
            onClick={async () => {
              try {
                await api("/api/auth/totp/enable", { body: { code } });
                setEnabled(true);
                setMsg("2FA is on.");
              } catch (e) {
                setMsg(e instanceof Error ? e.message : "failed");
              }
            }}
          >
            Confirm
          </Button>
        </div>
      )}
      {enabled && (
        <div className="mt-3 flex gap-2">
          <input aria-label="Current 2FA code" value={code} onChange={(e) => setCode(e.target.value)} placeholder="code to disable" className="rounded-lg border px-3 py-1.5" />
          <Button
            variant="outline"
            onClick={async () => {
              try {
                await api("/api/auth/totp/disable", { body: { code } });
                setEnabled(false);
                setSetup(null);
                setMsg("2FA is off.");
              } catch (e) {
                setMsg(e instanceof Error ? e.message : "failed");
              }
            }}
          >
            Disable
          </Button>
        </div>
      )}
      {msg && <p role="status" className="mt-2 text-sm">{msg}</p>}
    </Card>
  );
}
