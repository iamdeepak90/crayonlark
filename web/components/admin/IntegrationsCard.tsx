"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { IntegrationField, IntegrationGroup, Integrations } from "@/lib/types";
import { Button, Card } from "./ui";

const input = "w-full min-w-0 rounded-lg border border-slate-300 px-2 py-1.5 text-sm";

/**
 * Optional features, each with an on/off switch. Only the 7 infra secrets live in Coolify;
 * everything here is stored in the database (keys encrypted) and never shown again after saving.
 */
export default function IntegrationsCard({ initial }: { initial: Integrations }) {
  const [groups, setGroups] = useState(initial.groups);
  return (
    <Card title="Integrations" className="lg:col-span-2">
      <p className="mb-4 text-sm text-slate-600">
        Switch on only what you use. Keys are stored encrypted and are never shown again: leave a key field empty to keep the saved one. Changes reach the
        workers and the Telegram bot within a minute and the website within 5 minutes; no redeploy needed.
      </p>
      <div className="grid gap-3 md:grid-cols-2">
        {groups.map((g) => (
          <GroupForm key={g.id} group={g} onSaved={setGroups} />
        ))}
      </div>
    </Card>
  );
}

function GroupForm({ group, onSaved }: { group: IntegrationGroup; onSaved: (g: IntegrationGroup[]) => void }) {
  const [enabled, setEnabled] = useState(group.enabled);
  const [values, setValues] = useState<Record<string, string>>(() =>
    Object.fromEntries(group.fields.map((f) => [f.name, f.secret ? "" : (f.value ?? "")])),
  );
  const [clear, setClear] = useState<Set<string>>(new Set());
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  async function save() {
    setBusy(true);
    setMsg("");
    const body: Record<string, string | null> = {};
    for (const f of group.fields) {
      if (!f.secret) body[f.name] = values[f.name];
      else if (clear.has(f.name)) body[f.name] = "";
      else body[f.name] = values[f.name] ? values[f.name] : null; // null = keep the saved key
    }
    try {
      const res = await api<Integrations>(`/api/admin/integrations/${group.id}`, { method: "PUT", body: { enabled, values: body } });
      onSaved(res.groups);
      setValues((v) => Object.fromEntries(Object.entries(v).map(([k, x]) => [k, group.fields.find((f) => f.name === k)?.secret ? "" : x])));
      setClear(new Set());
      setMsg("Saved");
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rounded-xl border border-slate-200 p-4" aria-labelledby={`int-${group.id}`}>
      <div className="flex items-center justify-between gap-3">
        <h3 id={`int-${group.id}`} className="font-semibold">
          {group.title}
        </h3>
        <label className="inline-flex cursor-pointer items-center gap-2 text-sm font-semibold">
          <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} className="h-4 w-4" />
          {enabled ? "On" : "Off"}
        </label>
      </div>
      <p className="mt-1 text-xs text-slate-600">{group.help}</p>
      <div className={`mt-3 space-y-2 ${enabled ? "" : "opacity-60"}`}>
        {group.fields.map((f) => (
          <FieldInput
            key={f.name}
            field={f}
            value={values[f.name]}
            cleared={clear.has(f.name)}
            onChange={(v) => setValues({ ...values, [f.name]: v })}
            onClear={() => setClear(new Set(clear).add(f.name))}
          />
        ))}
      </div>
      <div className="mt-3 flex items-center gap-3">
        <Button onClick={save} disabled={busy}>
          {busy ? "…" : "Save"}
        </Button>
        {msg && (
          <span role="status" className="text-sm">
            {msg}
          </span>
        )}
      </div>
    </section>
  );
}

function FieldInput({
  field: f,
  value,
  cleared,
  onChange,
  onClear,
}: {
  field: IntegrationField;
  value: string;
  cleared: boolean;
  onChange: (v: string) => void;
  onClear: () => void;
}) {
  const id = `f-${f.name}`;
  let status = "";
  if (f.from_env) status = "set by an env var (wins over this field)";
  else if (f.secret && f.unreadable) status = "saved with an older SECRET_KEY: enter it again";
  else if (f.secret && cleared) status = "will be removed on save";
  else if (f.secret && f.set) status = "✓ saved";
  return (
    <div>
      <label htmlFor={id} className="flex flex-wrap items-baseline justify-between gap-x-2 text-sm font-semibold">
        {f.label}
        {status && <span className="text-xs font-normal text-slate-500">{status}</span>}
      </label>
      <div className="flex gap-2">
        {f.kind === "select" ? (
          <select id={id} value={value} onChange={(e) => onChange(e.target.value)} className={input}>
            <option value="">—</option>
            {f.options.map((o) => (
              <option key={o} value={o}>
                {o}
              </option>
            ))}
          </select>
        ) : (
          <input
            id={id}
            type={f.secret ? "password" : "text"}
            inputMode={f.kind === "int" ? "numeric" : undefined}
            autoComplete={f.secret ? "new-password" : "off"}
            spellCheck={false}
            value={value}
            placeholder={f.secret && f.set ? "•••••••• (leave empty to keep)" : f.placeholder}
            onChange={(e) => onChange(e.target.value)}
            className={input}
          />
        )}
        {f.secret && f.set && !cleared && (
          <Button type="button" variant="ghost" onClick={onClear} aria-label={`Remove saved ${f.label}`}>
            Remove
          </Button>
        )}
      </div>
    </div>
  );
}
