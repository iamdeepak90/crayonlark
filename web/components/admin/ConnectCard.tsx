import ActionButton from "./ActionButton";
import { Badge, Card, fmtDate } from "./ui";
import type { Connection } from "@/lib/types";

/** Connect / disconnect an OAuth provider. "Connect" is a plain link: the API redirects to the provider. */
export default function ConnectCard({ name, label, configured, connection, children }: { name: string; label: string; configured: boolean; connection: Connection; children?: React.ReactNode }) {
  return (
    <Card title={`${label} connection`} actions={<Badge value={connection.connected ? "connected" : "not connected"} />} className="mb-4">
      {!configured && <p className="text-sm text-rose-700">App keys are missing. Enter them in Settings → Integrations (see docs/API_KEYS.md).</p>}
      {configured && !connection.connected && (
        <a href={`/api/oauth/${name}/start`} className="inline-block rounded-lg bg-ink px-3 py-1.5 text-sm font-semibold text-white">
          Connect {label}
        </a>
      )}
      {connection.connected && (
        <div className="flex flex-wrap items-center gap-3 text-sm">
          <span>Token renews automatically (current one valid until {fmtDate(connection.expires_at)}).</span>
          <ActionButton path={`/api/oauth/${name}/disconnect`} label="Disconnect" variant="ghost" confirm={`Disconnect ${label}?`} />
        </div>
      )}
      {children}
    </Card>
  );
}
