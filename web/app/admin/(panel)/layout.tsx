import { redirect } from "next/navigation";
import AdminShell from "@/components/admin/AdminShell";
import { ApiError, serverApi } from "@/lib/api";
import type { Dashboard } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function PanelLayout({ children }: { children: React.ReactNode }) {
  let me: { email: string };
  try {
    me = await serverApi<{ email: string }>("/api/auth/me");
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) redirect("/login");
    throw e;
  }
  const dash = await serverApi<Dashboard>("/api/admin/dashboard").catch(() => null);
  return (
    <AdminShell email={me.email} needsYou={dash?.needs_you ?? 0}>
      {children}
    </AdminShell>
  );
}
