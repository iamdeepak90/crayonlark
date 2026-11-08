import Image from "next/image";
import { redirect } from "next/navigation";
import { NavLink } from "@/components/admin/ui";
import { ApiError, serverApi } from "@/lib/api";
import LogoutButton from "@/components/admin/LogoutButton";

export const dynamic = "force-dynamic";

const NAV: [string, string][] = [
  ["/", "Pipeline"],
  ["/niches", "Niche ideas"],
  ["/books/new", "New book"],
  ["/packs", "KDP packs"],
  ["/etsy", "Etsy drafts"],
  ["/pinterest", "Pinterest"],
  ["/blog", "Blog posts"],
  ["/subscribers", "Subscribers"],
  ["/messages", "Messages"],
  ["/sales", "Sales"],
  ["/costs", "Costs"],
  ["/jobs", "Jobs"],
  ["/audit", "Audit log"],
  ["/settings", "Settings"],
];

export default async function PanelLayout({ children }: { children: React.ReactNode }) {
  let me: { email: string };
  try {
    me = await serverApi<{ email: string }>("/api/auth/me");
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) redirect("/login");
    throw e;
  }
  return (
    <div className="flex min-h-dvh flex-col md:flex-row">
      <aside className="border-b border-slate-200 bg-cream md:w-56 md:border-r md:border-b-0">
        <div className="flex items-center gap-2 px-4 py-4">
          <Image src="/brand/lark.svg" alt="" width={32} height={32} />
          <span className="font-display text-lg font-bold">Crayonlark</span>
        </div>
        <nav aria-label="Admin" className="flex gap-1 overflow-x-auto px-2 pb-3 md:block md:space-y-0.5">
          {NAV.map(([href, label]) => (
            <NavLink key={href} href={href}>
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="hidden px-4 py-4 text-xs text-slate-500 md:block">
          {me.email}
          <LogoutButton />
        </div>
      </aside>
      <main className="min-w-0 flex-1 bg-slate-50 p-4 md:p-8">{children}</main>
    </div>
  );
}
