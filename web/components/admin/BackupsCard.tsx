import { CircleCheck, CircleX } from "lucide-react";
import ActionButton from "./ActionButton";
import { Card, fmtDate } from "./ui";
import type { BackupsResponse } from "@/lib/types";

const MAX_AGE_DAYS = 2;

/** True when there is no successful backup from the last two days. */
function needsAttention(b: BackupsResponse): boolean {
  if (!b.last || !b.last.ok) return true;
  const ageDays = (Date.now() - new Date(`${b.last.day}T00:00:00Z`).getTime()) / 86_400_000;
  return ageDays > MAX_AGE_DAYS;
}

export default function BackupsCard({ backups: b }: { backups: BackupsResponse }) {
  const warn = needsAttention(b);
  const last = b.last;
  return (
    <Card title="Backups" className={warn ? "border-amber-400 bg-amber-50" : ""} actions={<ActionButton path="/api/admin/backups/run" label="Run backup now" variant="outline" success="Backup started: refresh in a few minutes." />}>
      {warn && (
        <p role="alert" className="mb-2 text-sm font-semibold text-amber-900">
          {!last ? "No backup has run yet." : !last.ok ? `The last backup (${last.day}) failed.` : `The last backup is from ${last.day}, more than ${MAX_AGE_DAYS} days ago.`}
        </p>
      )}
      {last && (
        <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-sm">
          <dt className="text-slate-500">Last run</dt>
          <dd className="flex items-center gap-1.5">
            {last.day}{" "}
            {last.ok ? <CircleCheck className="size-4 text-emerald-600" aria-label="ok" /> : <span className="inline-flex items-center gap-1 text-destructive"><CircleX className="size-4" aria-hidden="true" /> failed</span>}
          </dd>
          <dt className="text-slate-500">Finished</dt>
          <dd>{fmtDate(last.finished_at)}</dd>
          {last.error && (
            <>
              <dt className="text-slate-500">Error</dt>
              <dd className="break-words text-rose-700">{last.error}</dd>
            </>
          )}
          {last.dump_mb !== undefined && (
            <>
              <dt className="text-slate-500">Database dump</dt>
              <dd>{last.dump_mb} MB</dd>
            </>
          )}
          <dt className="text-slate-500">Off-site copy</dt>
          <dd>{last.offsite?.enabled ? `on${last.offsite.files !== undefined ? ` (${last.offsite.files} files)` : ""}` : "off"}</dd>
          {Object.entries(last.buckets ?? {}).map(([name, v]) => (
            <div key={name} className="contents">
              <dt className="text-slate-500">Bucket {name}</dt>
              <dd>{v.objects} objects ({v.copied} copied, {v.removed} removed)</dd>
            </div>
          ))}
        </dl>
      )}
      <p className="mt-3 text-sm">
        <strong>{b.dumps.length}</strong> dumps kept ({b.retention_days} days){b.offsite ? ", also copied off-site" : ", no off-site copy configured"}.
      </p>
      {b.dumps.length > 0 && (
        <details className="mt-1 text-sm">
          <summary className="cursor-pointer text-slate-600">Available dumps</summary>
          <ul className="mt-1 max-h-48 overflow-y-auto font-mono text-xs">
            {[...b.dumps].reverse().map((d) => <li key={d}>{d}</li>)}
          </ul>
        </details>
      )}
      <p className="mt-3 text-xs text-slate-500">
        Restore: run <code>scripts/restore.sh &lt;day&gt;</code> on the server (see docs/DEPLOY_COOLIFY.md).
      </p>
    </Card>
  );
}
