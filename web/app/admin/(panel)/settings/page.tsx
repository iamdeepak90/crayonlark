import AISettings from "@/components/admin/AISettings";
import BackupsCard from "@/components/admin/BackupsCard";
import BudgetCard from "@/components/admin/BudgetCard";
import IntegrationsCard from "@/components/admin/IntegrationsCard";
import PaidApisCard from "@/components/admin/PaidApisCard";
import SecurityCard from "@/components/admin/SecurityCard";
import SettingEditor from "@/components/admin/SettingEditor";
import { PageTitle } from "@/components/admin/ui";
import { serverApi } from "@/lib/api";
import type { AIProviders, BackupsResponse, BudgetSettings, Integrations, PaidApis } from "@/lib/types";

// Edited in their own cards instead (they validate before saving).
const AI_KEYS = new Set(["agent_models", "image_provider", "budget", "integrations"]);

const HELP: Record<string, string> = {
  house_prompt_template: "Prompt template for coloring pages. {scene} is replaced by each scene idea.",
  blocklist_extra: "Extra blocked words/phrases (brands, characters, artists) on top of the built-in list.",
  images_per_book: "How many images you must approve per book.",
  concepts_per_niche: "Scene ideas the concept agent writes for each book.",
  pinterest: "Pins per day and posting window (UTC hours).",
  qa_thresholds: "Python QA limits for images.",
  free_printable_key: "Object key (outputs bucket) of the free sample pack on the website.",
};

export default async function SettingsPage() {
  const [settings, me, ai, backups, budget, paid, integrations] = await Promise.all([
    serverApi<Record<string, unknown>>("/api/admin/settings"),
    serverApi<{ email: string; totp_enabled: boolean }>("/api/auth/me"),
    serverApi<AIProviders>("/api/admin/ai/providers"),
    serverApi<BackupsResponse>("/api/admin/backups"),
    serverApi<BudgetSettings>("/api/admin/budget"),
    serverApi<PaidApis>("/api/admin/paid-apis"),
    serverApi<Integrations>("/api/admin/integrations"),
  ]);
  return (
    <>
      <PageTitle>Settings</PageTitle>
      <p className="mb-4 max-w-3xl text-sm text-slate-600">
        Coolify only holds the 7 infra secrets. Everything optional is switched on here under Integrations (keys are stored encrypted). Every change is written to the audit log.
      </p>
      <div className="grid gap-4 lg:grid-cols-2">
        <IntegrationsCard initial={integrations} />
        <PaidApisCard data={paid} />
        <BudgetCard initial={budget} />
        <AISettings initial={ai} />
        <BackupsCard backups={backups} />
        <SecurityCard email={me.email} totpEnabled={me.totp_enabled} />
        {Object.entries(settings)
          .filter(([key]) => !AI_KEYS.has(key))
          .map(([key, value]) => (
            <SettingEditor key={key} name={key} value={value} help={HELP[key]} />
          ))}
      </div>
    </>
  );
}
