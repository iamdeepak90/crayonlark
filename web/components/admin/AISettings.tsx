"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { AgentModel, AIProviders, ImageProvider, LlmProvider, OpenRouterModels } from "@/lib/types";
import { Button, Card } from "./ui";

/** Grouped so the choice is clear: free, a company's own (official) API, or OpenRouter. */
const LLM_GROUPS: [string, LlmProvider[]][] = [["Free", ["offline"]], ["Official API", ["anthropic", "openai", "gemini"]], ["OpenRouter", ["openrouter"]]];
const IMAGE_GROUPS: [string, ImageProvider[]][] = [["Free", ["manual"]], ["Official API", ["openai", "gemini"]], ["OpenRouter", ["openrouter"]]];
const LABEL: Record<string, string> = {
  offline: "Offline (free templates)",
  manual: "Manual upload (free)",
  anthropic: "Anthropic (Claude)",
  openai: "OpenAI",
  gemini: "Google Gemini",
  openrouter: "OpenRouter (any model)",
};
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
  const [orModels, setOrModels] = useState<OpenRouterModels | null>(null);

  useEffect(() => {
    if (!initial.keys.openrouter) return;
    // Live list from OpenRouter (cached on the server); the inputs still accept any id if it fails.
    api<OpenRouterModels>("/api/admin/ai/openrouter-models").then(setOrModels, () => setOrModels({ text: [], image: [] }));
  }, [initial.keys.openrouter]);

  /** Price line for an agent's chosen model. */
  function priceText(m: AgentModel, agent: string): string {
    const id = (m.model ?? "").trim();
    if (m.provider === "offline") return "free";
    if (!id) return m.provider === "openrouter" ? "pick a model (e.g. anthropic/claude-haiku-5.5)" : "pick a model";
    if (m.provider === "openrouter") {
      const or = orModels?.text.find((x) => x.id === id);
      if (!or) return orModels ? "not in OpenRouter's list of models that can return JSON" : "";
      const price = or.input_per_m !== null && or.output_per_m !== null ? `$${or.input_per_m} in / $${or.output_per_m} out per 1M tokens (via OpenRouter)` : "price unknown";
      return agent === "vision_qa" && !or.vision ? `${price}. This model can't see images: pick one with image input for vision QA.` : price;
    }
    const price = initial.llm_prices[id];
    return price ? `$${price.input} in / $${price.output} out per 1M tokens` : "unknown model: priced at the expensive fallback rate";
  }

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
      <p className="mb-3 text-xs text-slate-500">
        <strong>Official API</strong> calls the company directly with its own key. <strong>OpenRouter</strong> uses one key for models from many companies (ids like <code>anthropic/claude-haiku-5.5</code>, <code>openai/…</code>, <code>google/…</code>); its price list is loaded live.
      </p>
      {(["anthropic", "openai", "gemini", "openrouter"] as const).some((p) => !initial.keys[p]) && (
        <p className="mb-3 text-xs text-slate-500">
          Keys not set: {(["anthropic", "openai", "gemini", "openrouter"] as const).filter((p) => !initial.keys[p]).join(", ")}. Add them in Settings → Integrations → AI providers to enable those choices.
        </p>
      )}
      <div className="space-y-3">
        {initial.agents.map((a) => {
          const m = agents[a];
          const list = `models-${a}`;
          return (
            <fieldset key={a} className="rounded-xl border border-slate-200 p-3">
              <legend className="px-1 text-sm font-bold">{a.replaceAll("_", " ")}</legend>
              <div className="flex flex-wrap items-end gap-2">
                <label className="text-xs font-semibold">
                  Provider
                  <select className={`${field} mt-1 block`} value={m.provider} onChange={(e) => update(a, { provider: e.target.value as LlmProvider, model: "" })}>
                    {LLM_GROUPS.map(([group, list]) => (
                      <optgroup key={group} label={group}>
                        {list.map((p) => (
                          <option key={p} value={p} disabled={!hasKey(p)}>
                            {LABEL[p]}{hasKey(p) ? "" : " (key not set)"}
                          </option>
                        ))}
                      </optgroup>
                    ))}
                  </select>
                </label>
                <label className="min-w-48 flex-1 text-xs font-semibold">
                  Model
                  <input className={`${field} mt-1 block w-full`} list={list} value={m.model ?? ""} disabled={m.provider === "offline"} placeholder={m.provider === "offline" ? "—" : "model id"} onChange={(e) => update(a, { model: e.target.value })} />
                  <datalist id={list}>
                    {m.provider === "openrouter"
                      ? orModels?.text.map((x) => <option key={x.id} value={x.id}>{x.name}</option>)
                      : modelsFor(m.provider, initial.llm_prices).map((id) => <option key={id} value={id} />)}
                  </datalist>
                </label>
                <label className="text-xs font-semibold">
                  Effort
                  <select className={`${field} mt-1 block`} value={m.effort ?? ""} disabled={m.provider === "offline"} onChange={(e) => update(a, { effort: e.target.value })}>
                    {EFFORTS.map((e) => <option key={e} value={e}>{e || "default"}</option>)}
                  </select>
                </label>
              </div>
              <p className="mt-1 text-xs text-slate-500">{priceText(m, a)}</p>
            </fieldset>
          );
        })}
        <fieldset className="rounded-xl border border-slate-200 p-3">
          <legend className="px-1 text-sm font-bold">images</legend>
          <div className="flex flex-wrap items-end gap-2">
            <label className="text-xs font-semibold">
              Provider
              <select className={`${field} mt-1 block`} value={imgProvider} onChange={(e) => { setImgProvider(e.target.value as ImageProvider); setImgModel(""); }}>
                {IMAGE_GROUPS.map(([group, list]) => (
                  <optgroup key={group} label={group}>
                    {list.map((p) => (
                      <option key={p} value={p} disabled={!hasKey(p)}>
                        {LABEL[p]}{hasKey(p) ? "" : " (key not set)"}
                      </option>
                    ))}
                  </optgroup>
                ))}
              </select>
            </label>
            <label className="min-w-48 flex-1 text-xs font-semibold">
              Model
              <input className={`${field} mt-1 block w-full`} list="models-images" value={imgModel} disabled={imgProvider === "manual"} placeholder={imgProvider === "manual" ? "—" : "model id"} onChange={(e) => setImgModel(e.target.value)} />
              <datalist id="models-images">
                {imgProvider === "openrouter"
                  ? orModels?.image.map((x) => <option key={x.id} value={x.id}>{x.name}</option>)
                  : modelsFor(imgProvider, initial.image_prices).map((id) => <option key={id} value={id} />)}
              </datalist>
            </label>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            {imgProvider === "manual" ? "free: you upload the pictures" : imgProvider === "openrouter" ? (imgModel ? "real cost is recorded after each image; the budget reserves $0.25 per image until then (override in model_prices)" : "pick an image model (e.g. google/gemini-2.5-flash-image)") : imgPrice !== undefined ? `~$${imgPrice} per image` : imgModel ? "unknown model: priced at the expensive fallback rate" : "pick a model"}
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
