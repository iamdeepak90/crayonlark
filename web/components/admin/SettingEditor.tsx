"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { Button, Card } from "./ui";

export default function SettingEditor({ name, value, help }: { name: string; value: unknown; help?: string }) {
  const isText = typeof value === "string";
  const [text, setText] = useState(isText ? (value as string) : JSON.stringify(value, null, 2));
  const [msg, setMsg] = useState("");

  async function save() {
    setMsg("");
    let parsed: unknown = text;
    if (!isText) {
      try {
        parsed = JSON.parse(text);
      } catch {
        setMsg("Not valid JSON");
        return;
      }
    }
    try {
      await api(`/api/admin/settings/${name}`, { method: "PUT", body: { value: parsed } });
      setMsg("Saved");
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "failed");
    }
  }

  return (
    <Card title={<code className="text-base">{name}</code>}>
      {help && <p className="mb-2 text-sm text-slate-600">{help}</p>}
      <label className="sr-only" htmlFor={`s-${name}`}>{name}</label>
      <textarea id={`s-${name}`} value={text} onChange={(e) => setText(e.target.value)} rows={Math.min(14, text.split("\n").length + 1)} className="w-full rounded-lg border border-slate-300 p-2 font-mono text-xs" />
      <div className="mt-2 flex items-center gap-2">
        <Button onClick={save}>Save</Button>
        {msg && <span role="status" className="text-sm">{msg}</span>}
      </div>
    </Card>
  );
}
