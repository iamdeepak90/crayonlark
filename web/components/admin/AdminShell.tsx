"use client";

import {
  Bell,
  ChartColumn,
  Clock,
  ExternalLink,
  FileText,
  House,
  Lightbulb,
  LogOut,
  type LucideIcon,
  Mail,
  Menu,
  Moon,
  Package,
  Pin,
  Plus,
  ScrollText,
  Settings,
  Store,
  Sun,
  Trophy,
  Users,
  Wallet,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Button, buttonVariants } from "@/components/ui/button";
import { Toaster } from "@/components/ui/sonner";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Monogram } from "./ui";

type Item = { href: string; label: string; icon: LucideIcon };

const GROUPS: { title: string; items: Item[] }[] = [
  {
    title: "Your part",
    items: [
      { href: "/", label: "Today", icon: House },
      { href: "/etsy", label: "1. Approve for Etsy", icon: Store },
      { href: "/kdp", label: "2. Pick for KDP", icon: Trophy },
      { href: "/packs", label: "KDP uploads", icon: Package },
      { href: "/settings", label: "Settings", icon: Settings },
    ],
  },
  {
    title: "More (runs by itself)",
    items: [
      { href: "/sales", label: "Sales", icon: ChartColumn },
      { href: "/niches", label: "Niche ideas", icon: Lightbulb },
      { href: "/books/new", label: "New book", icon: Plus },
      { href: "/pinterest", label: "Pinterest", icon: Pin },
      { href: "/blog", label: "Blog posts", icon: FileText },
      { href: "/subscribers", label: "Subscribers", icon: Users },
      { href: "/messages", label: "Messages", icon: Mail },
      { href: "/costs", label: "Costs", icon: Wallet },
      { href: "/jobs", label: "Jobs", icon: Clock },
      { href: "/audit", label: "Audit log", icon: ScrollText },
    ],
  },
];

const ALL = GROUPS.flatMap((g) => g.items);

function isActive(pathname: string, href: string) {
  if (href === "/") return pathname === "/" || (pathname.startsWith("/books/") && pathname !== "/books/new");
  return pathname === href || pathname.startsWith(`${href}/`);
}

const itemClass =
  "flex h-8 w-full items-center gap-2 rounded-md px-2 text-sm text-sidebar-foreground outline-none transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground focus-visible:ring-2 focus-visible:ring-ring [&_svg]:size-4 [&_svg]:shrink-0";

function Nav({ pathname, onNavigate }: { pathname: string; onNavigate?: () => void }) {
  return (
    <nav aria-label="Admin" className="flex flex-col gap-4">
      {GROUPS.map((g) => (
        <div key={g.title}>
          <p className="flex h-8 items-center px-2 text-xs font-medium text-sidebar-foreground/70">{g.title}</p>
          <ul className="flex flex-col gap-1">
            {g.items.map(({ href, label, icon: Icon }) => {
              const active = isActive(pathname, href);
              return (
                <li key={href}>
                  <Link
                    href={href}
                    onClick={onNavigate}
                    aria-current={active ? "page" : undefined}
                    className={cn(itemClass, active && "bg-sidebar-accent font-medium text-sidebar-accent-foreground")}
                  >
                    <Icon aria-hidden="true" />
                    {label}
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

function ThemeToggle({ dark, setDark }: { dark: boolean; setDark: (v: boolean) => void }) {
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
    <Button variant="ghost" size="icon" onClick={toggle} aria-label={dark ? "Switch to light mode" : "Switch to dark mode"} title={dark ? "Light mode" : "Dark mode"}>
      {dark ? <Sun aria-hidden="true" /> : <Moon aria-hidden="true" />}
    </Button>
  );
}

/** Sidebar + top bar for every logged-in admin page (shadcn/ui sidebar look). */
export default function AdminShell({ email, needsYou, children }: { email: string; needsYou: number; children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [dark, setDark] = useState(false);
  // eslint-disable-next-line react-hooks/set-state-in-effect -- read the class set by the inline script
  useEffect(() => setDark(document.documentElement.classList.contains("dark")), []);
  const current = ALL.find((it) => isActive(pathname, it.href));

  async function logout() {
    await api("/api/auth/logout", { method: "POST" });
    router.replace("/login");
  }

  const brand = (
    <Link href="/" className="flex h-10 items-center gap-2 rounded-md px-2" onClick={() => setOpen(false)}>
      <Monogram className="size-8 text-sm" />
      <span className="grid leading-tight">
        <span className="text-sm font-semibold">Crayonlark</span>
        <span className="text-xs text-muted-foreground">Admin</span>
      </span>
    </Link>
  );

  const footer = (
    <div className="flex flex-col gap-1 border-t border-sidebar-border pt-2">
      <a href={process.env.NEXT_PUBLIC_SITE_URL ?? "/"} target="_blank" rel="noopener" className={itemClass}>
        <ExternalLink aria-hidden="true" /> View website
      </a>
      <button type="button" onClick={logout} className={itemClass}>
        <LogOut aria-hidden="true" /> Log out
      </button>
      <p className="truncate px-2 pt-1 text-xs text-muted-foreground" title={email}>
        {email}
      </p>
    </div>
  );

  return (
    <div className="flex min-h-dvh bg-background text-foreground">
      {/* desktop sidebar */}
      <aside className="sticky top-0 hidden h-dvh w-64 shrink-0 flex-col gap-2 border-r border-sidebar-border bg-sidebar p-2 lg:flex">
        {brand}
        <div className="flex-1 overflow-y-auto">
          <Nav pathname={pathname} />
        </div>
        {footer}
      </aside>

      {/* mobile drawer */}
      {open && (
        <div className="fixed inset-0 z-50 lg:hidden" role="dialog" aria-modal="true" aria-label="Menu">
          <button type="button" className="absolute inset-0 bg-black/50" aria-label="Close menu" onClick={() => setOpen(false)} />
          <aside className="absolute inset-y-0 left-0 flex w-72 flex-col gap-2 overflow-y-auto border-r border-sidebar-border bg-sidebar p-2 shadow-lg">
            <div className="flex items-center justify-between">
              {brand}
              <Button variant="ghost" size="icon" onClick={() => setOpen(false)} aria-label="Close menu">
                <X aria-hidden="true" />
              </Button>
            </div>
            <div className="flex-1">
              <Nav pathname={pathname} onNavigate={() => setOpen(false)} />
            </div>
            {footer}
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-14 items-center gap-2 border-b bg-background/80 px-4 backdrop-blur md:px-6">
          <Button variant="ghost" size="icon" className="-ml-2 lg:hidden" onClick={() => setOpen(true)} aria-label="Open menu">
            <Menu aria-hidden="true" />
          </Button>
          <p className="truncate text-sm text-muted-foreground">
            <span className="hidden sm:inline">Admin / </span>
            <span className="font-medium text-foreground">{current?.label ?? "Admin"}</span>
          </p>
          <div className="ml-auto flex items-center gap-1">
            <Link href="/" className={buttonVariants({ variant: "ghost", size: "sm" })} title="Approvals and reviews waiting for you">
              <Bell aria-hidden="true" />
              <span className="hidden sm:inline">Needs you</span>
              <span
                className={cn(
                  "grid h-5 min-w-5 place-items-center rounded-md px-1 text-[11px] font-semibold tabular-nums",
                  needsYou ? "bg-primary text-primary-foreground" : "bg-secondary text-muted-foreground",
                )}
              >
                {needsYou}
              </span>
            </Link>
            <ThemeToggle dark={dark} setDark={setDark} />
          </div>
        </header>
        <main className="min-w-0 flex-1 px-4 py-6 md:px-8 md:py-8">
          <div className="mx-auto max-w-6xl">{children}</div>
        </main>
        <Toaster theme={dark ? "dark" : "light"} />
      </div>
    </div>
  );
}
