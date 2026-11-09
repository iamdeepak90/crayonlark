"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Icon, type IconName } from "./icons";
import { Monogram } from "./ui";

type Item = { href: string; label: string; icon: IconName };

const GROUPS: { title: string; items: Item[] }[] = [
  {
    title: "Make",
    items: [
      { href: "/", label: "Pipeline", icon: "pipeline" },
      { href: "/niches", label: "Niche ideas", icon: "niches" },
      { href: "/books/new", label: "New book", icon: "plus" },
      { href: "/packs", label: "KDP packs", icon: "pack" },
    ],
  },
  {
    title: "Sell & market",
    items: [
      { href: "/etsy", label: "Etsy drafts", icon: "etsy" },
      { href: "/pinterest", label: "Pinterest", icon: "pin" },
      { href: "/blog", label: "Blog posts", icon: "blog" },
      { href: "/sales", label: "Sales", icon: "sales" },
    ],
  },
  {
    title: "Audience",
    items: [
      { href: "/subscribers", label: "Subscribers", icon: "users" },
      { href: "/messages", label: "Messages", icon: "mail" },
    ],
  },
  {
    title: "System",
    items: [
      { href: "/costs", label: "Costs", icon: "costs" },
      { href: "/jobs", label: "Jobs", icon: "jobs" },
      { href: "/audit", label: "Audit log", icon: "audit" },
      { href: "/settings", label: "Settings", icon: "settings" },
    ],
  },
];

const ALL = GROUPS.flatMap((g) => g.items);

function isActive(pathname: string, href: string) {
  if (href === "/") return pathname === "/" || (pathname.startsWith("/books/") && pathname !== "/books/new");
  return pathname === href || pathname.startsWith(`${href}/`);
}

function Nav({ pathname, onNavigate }: { pathname: string; onNavigate?: () => void }) {
  return (
    <nav aria-label="Admin" className="space-y-5">
      {GROUPS.map((g) => (
        <div key={g.title}>
          <p className="px-2.5 text-xs font-medium text-slate-400">{g.title}</p>
          <ul className="mt-1 space-y-px">
            {g.items.map((it) => {
              const active = isActive(pathname, it.href);
              return (
                <li key={it.href}>
                  <Link
                    href={it.href}
                    onClick={onNavigate}
                    aria-current={active ? "page" : undefined}
                    className={`flex items-center gap-2.5 rounded-md px-2.5 py-1.5 text-sm transition-colors ${
                      active ? "bg-slate-100 font-medium text-ink" : "text-slate-600 hover:bg-slate-100/70 hover:text-ink"
                    }`}
                  >
                    <Icon name={it.icon} className={`h-4 w-4 ${active ? "text-ink" : "text-slate-400"}`} />
                    {it.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </nav>
  );
}

function ThemeToggle() {
  const [dark, setDark] = useState(false);
  // eslint-disable-next-line react-hooks/set-state-in-effect -- read the class set by the inline script
  useEffect(() => setDark(document.documentElement.classList.contains("dark")), []);
  function toggle() {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    try {
      localStorage.setItem("cl-admin-theme", next ? "dark" : "light");
    } catch {
      /* private mode: just this page view */
    }
  }
  return (
    <button
      type="button"
      onClick={toggle}
      className="grid h-8 w-8 place-items-center rounded-md text-slate-500 transition-colors hover:bg-slate-100 hover:text-ink"
      aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
      title={dark ? "Light mode" : "Dark mode"}
    >
      <Icon name={dark ? "sun" : "moon"} className="h-4 w-4" />
    </button>
  );
}

/** Sidebar + top bar for every logged-in admin page. */
export default function AdminShell({ email, needsYou, children }: { email: string; needsYou: number; children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const current = ALL.find((it) => isActive(pathname, it.href));

  async function logout() {
    await api("/api/auth/logout", { method: "POST" });
    router.replace("/login");
  }

  const brand = (
    <Link href="/" className="flex items-center gap-2.5 px-2.5" onClick={() => setOpen(false)}>
      <Monogram />
      <span className="text-sm font-semibold tracking-tight">Crayonlark</span>
      <span className="rounded border border-slate-200 px-1.5 py-px text-[10px] font-medium uppercase tracking-wide text-slate-500">Admin</span>
    </Link>
  );

  const footer = (
    <div className="space-y-1 border-t border-slate-200 pt-3">
      <a
        href={process.env.NEXT_PUBLIC_SITE_URL ?? "/"}
        target="_blank"
        rel="noopener"
        className="flex items-center gap-2.5 rounded-md px-2.5 py-1.5 text-sm text-slate-600 transition-colors hover:bg-slate-100 hover:text-ink"
      >
        <Icon name="external" className="h-4 w-4 text-slate-400" /> View website
      </a>
      <button
        type="button"
        onClick={logout}
        className="flex w-full items-center gap-2.5 rounded-md px-2.5 py-1.5 text-sm text-slate-600 transition-colors hover:bg-slate-100 hover:text-ink"
      >
        <Icon name="logout" className="h-4 w-4 text-slate-400" /> Log out
      </button>
      <p className="truncate px-2.5 pt-1 text-xs text-slate-400" title={email}>
        {email}
      </p>
    </div>
  );

  return (
    <div className="flex min-h-dvh bg-slate-50 text-ink">
      {/* desktop sidebar */}
      <aside className="sticky top-0 hidden h-dvh w-60 shrink-0 flex-col gap-5 border-r border-slate-200 bg-white px-3 py-4 lg:flex">
        {brand}
        <div className="-mx-1 flex-1 overflow-y-auto px-1">
          <Nav pathname={pathname} />
        </div>
        {footer}
      </aside>

      {/* mobile drawer */}
      {open && (
        <div className="fixed inset-0 z-50 lg:hidden" role="dialog" aria-modal="true" aria-label="Menu">
          <button type="button" className="absolute inset-0 bg-black/40" aria-label="Close menu" onClick={() => setOpen(false)} />
          <aside className="absolute inset-y-0 left-0 flex w-64 flex-col gap-5 overflow-y-auto border-r border-slate-200 bg-white px-3 py-4">
            <div className="flex items-center justify-between">
              {brand}
              <button type="button" onClick={() => setOpen(false)} className="grid h-8 w-8 place-items-center rounded-md text-slate-500 hover:bg-slate-100" aria-label="Close menu">
                <Icon name="close" className="h-4 w-4" />
              </button>
            </div>
            <div className="flex-1">
              <Nav pathname={pathname} onNavigate={() => setOpen(false)} />
            </div>
            {footer}
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-14 items-center gap-2 border-b border-slate-200 bg-white/80 px-4 backdrop-blur md:px-8">
          <button type="button" onClick={() => setOpen(true)} className="-ml-1 grid h-8 w-8 place-items-center rounded-md text-slate-500 hover:bg-slate-100 lg:hidden" aria-label="Open menu">
            <Icon name="menu" className="h-4 w-4" />
          </button>
          <p className="truncate text-sm text-slate-500">
            <span className="hidden sm:inline">Admin / </span>
            <span className="font-medium text-ink">{current?.label ?? "Admin"}</span>
          </p>
          <div className="ml-auto flex items-center gap-1">
            <Link
              href="/"
              className="inline-flex h-8 items-center gap-2 rounded-md px-2.5 text-sm text-slate-600 transition-colors hover:bg-slate-100 hover:text-ink"
              title="Approvals and reviews waiting for you"
            >
              <Icon name="bell" className="h-4 w-4" />
              <span className="hidden sm:inline">Needs you</span>
              <span
                className={`grid h-5 min-w-5 place-items-center rounded-full px-1.5 text-[11px] font-semibold tabular-nums ${
                  needsYou ? "bg-ink text-white" : "bg-slate-100 text-slate-500"
                }`}
              >
                {needsYou}
              </span>
            </Link>
            <ThemeToggle />
          </div>
        </header>
        <main className="min-w-0 flex-1 px-4 py-6 md:px-8 md:py-8">
          <div className="mx-auto max-w-6xl">{children}</div>
        </main>
      </div>
    </div>
  );
}
