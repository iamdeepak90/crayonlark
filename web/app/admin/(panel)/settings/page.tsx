import BackupsCard from "@/components/admin/BackupsCard";
import BudgetCard from "@/components/admin/BudgetCard";
import IntegrationsCard from "@/components/admin/IntegrationsCard";
import SecurityCard from "@/components/admin/SecurityCard";
import { PageTitle } from "@/components/admin/ui";
import { serverApi } from "@/lib/api";
import type { BackupsResponse, BudgetSettings, Integrations } from "@/lib/types";

/**
 * Only what I must set myself. Models, picture provider, Etsy schedule, Autopilot tuning and QA
 * limits are fixed in code (docs/DECISIONS.md 77).
 */
export default async function SettingsPage() {
  const [me, backups, budget, integrations] = await Promise.all([
    serverApi<{ email: string; totp_enabled: boolean }>("/api/auth/me"),
    serverApi<BackupsResponse>("/api/admin/backups"),
    serverApi<BudgetSettings>("/api/admin/budget"),
    serverApi<Integrations>("/api/admin/integrations"),
  ]);
  return (
    <>
      <PageTitle description="Add the keys once. The models, the picture maker, the daily Etsy schedule and the Autopilot are set up for you.">Settings</PageTitle>
      <div className="grid gap-4 lg:grid-cols-2">
        <IntegrationsCard initial={integrations} />
        <BudgetCard initial={budget} />
        <SecurityCard email={me.email} totpEnabled={me.totp_enabled} />
        <BackupsCard backups={backups} />
      </div>
    </>
  );
}
