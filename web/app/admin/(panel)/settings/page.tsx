import SecurityCard from "@/components/admin/SecurityCard";
import SettingEditor from "@/components/admin/SettingEditor";
import { PageTitle } from "@/components/admin/ui";
import { serverApi } from "@/lib/api";

const HELP: Record<string, string> = {
  agent_models: "Provider and model per agent. provider: anthropic | openai | gemini | offline (free, template-based).",
  image_provider: "manual (you upload images; zero cost) | openai | gemini.",
  house_prompt_template: "Prompt template for coloring pages. {scene} is replaced by each scene idea.",
  blocklist_extra: "Extra blocked words/phrases (brands, characters, artists) on top of the built-in list.",
  images_per_book: "How many images you must approve per book.",
  concepts_per_niche: "Scene ideas the concept agent writes for each book.",
  pinterest: "Pins per day and posting window (UTC hours).",
  qa_thresholds: "Python QA limits for images.",
  free_printable_key: "Object key (outputs bucket) of the free sample pack on the website.",
};

export default async function SettingsPage() {
  const [settings, me] = await Promise.all([serverApi<Record<string, unknown>>("/api/admin/settings"), serverApi<{ email: string; totp_enabled: boolean }>("/api/auth/me")]);
  return (
    <>
      <PageTitle>Settings</PageTitle>
      <p className="mb-4 max-w-3xl text-sm text-slate-600">
        Secrets (API keys, budget cap) live in Coolify environment variables. Everything here is stored in the database and every change is written to the audit log.
      </p>
      <div className="grid gap-4 lg:grid-cols-2">
        <SecurityCard email={me.email} totpEnabled={me.totp_enabled} />
        {Object.entries(settings).map(([key, value]) => (
          <SettingEditor key={key} name={key} value={value} help={HELP[key]} />
        ))}
      </div>
    </>
  );
}
