"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";
import type { AgentModel, AIProviders, ImageProvider, LlmProvider } from "@/lib/types";
import { Button, Card } from "./ui";

const LLM_PROVIDERS: LlmProvider[] = ["offline", "anthropic", "openai", "gemini"];
const IMAGE_PROVIDERS: ImageProvider[] = ["manual", "openai", "gemini"];
const EFFORTS = ["", "low", "medium", "high", "xhigh", "max"];
const PREFIX: Record<string, string> = { anthropic: "claude-", openai: "gpt-", gemini: "gemini-" };

const field = "rounded-lg border border-slate-300 px-2 py-1.5 text-sm";

/** Known model ids for a provider (by name prefix), for the <datalist> suggestions. */
function modelsFor(provider: string, prices: Record<string, unknown>): string[] {
  const prefix = PREFIX[provider];
  return prefix ? Object.keys(prices).filter((m) => m.startsWith(prefix)) : [];
}

/** Edit which provider/model each agent uses and which image provider makes the pictures. */
export default function AISettings({ initial }: { initial: AIProviders }) {
  const router = useRouter();
  const [agents, setAgents] = useState<Record<string, AgentModel>>(() =>
    Object.fromEntries(initial.agents.map((a) => [a, { model: "", effort: "", ...(initial.agent_models[a] ?? { provider: "offline" }) }])),
  );
  const [imgProvider, setImgProvider] = useState<ImageProvider>(initial.image_provider?.provider ?? "manual");
  const [imgModel, setImgModel] = useState(initial.image_provider?.model ?? "");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const hasKey = (p: string) => p === "offline" || p === "manual" || initial.keys[p as keyof AIProviders["keys"]];

  function update(agent: string, patch: Partial<AgentModel>) {
    setAgents((all) => ({ ...all, [agent]: { ...all[agent], ...patch } }));
  }

  async function save() {
    setBusy(true);
    setMsg("");
    try {
      const agent_models = Object.fromEntries(
        Object.entries(agents).map(([a, m]) => [a, { provider: m.provider, model: m.provider === "offline" ? "" : (m.model ?? "").trim(), effort: m.effort ?? "" }]),
      );
      await api("/api/admin/ai/providers", { method: "PUT", body: { agent_models, image_provider: imgProvider, image_model: imgProvider === "manual" ? "" : imgModel.trim() } });
      setMsg("Saved");
      router.refresh();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "failed");
    } finally {
      setBusy(false);
    }
  }

  const imgPrice = initial.image_prices[imgModel.trim()];
  return (
    <Card title="AI providers & models" className="lg:col-span-2">
      <p className="mb-3 text-sm text-slate-600">
        <strong>offline</strong> is free template output (no AI call); <strong>manual</strong> means you upload pictures you made yourself. Prices checked {initial.prices_checked}.
      </p>
      {(["anthropic", "openai", "gemini"] as const).some((p) => !initial.keys[p]) && (
        <p className="mb-3 text-xs text-slate-500">
          Keys not set: {(["anthropic", "openai", "gemini"] as const).filter((p) => !initial.keys[p]).join(", ")}. Add them as environment variables to enable those providers.
        </p>
      )}
      <div className="space-y-3">
        {initial.agents.map((a) => {
          const m = agents[a];
          const list = `models-${a}`;
          const price = initial.llm_prices[(m.model ?? "").trim()];
          return (
            <fieldset key={a} className="rounded-xl border border-slate-200 p-3">
              <legend className="px-1 text-sm font-bold">{a.replaceAll("_", " ")}</legend>
              <div className="flex flex-wrap items-end gap-2">
                <label className="text-xs font-semibold">
                  Provider
                  <select className={`${field} mt-1 block`} value={m.provider} onChange={(e) => update(a, { provider: e.target.value as LlmProvider, model: "" })}>
                    {LLM_PROVIDERS.map((p) => (
                      <option key={p} value={p} disabled={!hasKey(p)}>
                        {p}{hasKey(p) ? "" : " (key not set)"}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="min-w-48 flex-1 text-xs font-semibold">
                  Model
                  <input className={`${field} mt-1 block w-full`} list={list} value={m.model ?? ""} disabled={m.provider === "offline"} placeholder={m.provider === "offline" ? "—" : "model id"} onChange={(e) => update(a, { model: e.target.value })} />
                  <datalist id={list}>
                    {modelsFor(m.provider, initial.llm_prices).map((id) => <option key={id} value={id} />)}
                  </datalist>
                </label>
                <label className="text-xs font-semibold">
                  Effort
                  <select className={`${field} mt-1 block`} value={m.effort ?? ""} disabled={m.provider === "offline"} onChange={(e) => update(a, { effort: e.target.value })}>
                    {EFFORTS.map((e) => <option key={e} value={e}>{e || "default"}</option>)}
                  </select>
                </label>
              </div>
              <p className="mt-1 text-xs text-slate-500">
                {m.provider === "offline" ? "free" : price ? `$${price.input} in / $${price.output} out per 1M tokens` : m.model ? "unknown model: priced at the expensive fallback rate" : "pick a model"}
              </p>
            </fieldset>
          );
        })}
        <fieldset className="rounded-xl border border-slate-200 p-3">
          <legend className="px-1 text-sm font-bold">images</legend>
          <div className="flex flex-wrap items-end gap-2">
            <label className="text-xs font-semibold">
              Provider
              <select className={`${field} mt-1 block`} value={imgProvider} onChange={(e) => { setImgProvider(e.target.value as ImageProvider); setImgModel(""); }}>
                {IMAGE_PROVIDERS.map((p) => (
                  <option key={p} value={p} disabled={!hasKey(p)}>
                    {p}{hasKey(p) ? "" : " (key not set)"}
                  </option>
                ))}
              </select>
            </label>
            <label className="min-w-48 flex-1 text-xs font-semibold">
              Model
              <input className={`${field} mt-1 block w-full`} list="models-images" value={imgModel} disabled={imgProvider === "manual"} placeholder={imgProvider === "manual" ? "—" : "model id"} onChange={(e) => setImgModel(e.target.value)} />
              <datalist id="models-images">
                {modelsFor(imgProvider, initial.image_prices).map((id) => <option key={id} value={id} />)}
              </datalist>
            </label>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            {imgProvider === "manual" ? "free: you upload the pictures" : imgPrice !== undefined ? `~$${imgPrice} per image` : imgModel ? "unknown model: priced at the expensive fallback rate" : "pick a model"}
          </p>
        </fieldset>
      </div>
      <div className="mt-3 flex items-center gap-2">
        <Button onClick={save} disabled={busy}>{busy ? "Saving…" : "Save AI settings"}</Button>
        {msg && <span role="status" className="text-sm">{msg}</span>}
      </div>
    </Card>
  );
}
