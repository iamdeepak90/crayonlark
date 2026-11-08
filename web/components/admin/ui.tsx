import Link from "next/link";
import type { ComponentProps, ReactNode } from "react";

export function Card({ title, children, actions, className = "" }: { title?: ReactNode; children: ReactNode; actions?: ReactNode; className?: string }) {
  return (
    <section className={`rounded-2xl border border-slate-200 bg-white p-5 shadow-sm ${className}`}>
      {(title || actions) && (
        <div className="mb-3 flex items-center justify-between gap-3">
          {title && <h2 className="text-lg font-semibold">{title}</h2>}
          {actions}
        </div>
      )}
      {children}
    </section>
  );
}

const STATUS_COLORS: Record<string, string> = {
  awaiting_image_approval: "bg-amber-100 text-amber-900",
  awaiting_cover_approval: "bg-amber-100 text-amber-900",
  awaiting_listing_approval: "bg-amber-100 text-amber-900",
  kdp_pack_ready: "bg-sky-100 text-sky-900",
  live: "bg-emerald-100 text-emerald-900",
  approved: "bg-emerald-100 text-emerald-900",
  rejected: "bg-rose-100 text-rose-900",
  failed: "bg-rose-100 text-rose-900",
  succeeded: "bg-emerald-100 text-emerald-900",
  running: "bg-sky-100 text-sky-900",
  generating: "bg-sky-100 text-sky-900",
};

export function Badge({ value }: { value: string }) {
  return (
    <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-semibold ${STATUS_COLORS[value] ?? "bg-slate-100 text-slate-700"}`}>
      {value.replaceAll("_", " ")}
    </span>
  );
}

export function Button({ variant = "primary", className = "", ...props }: ComponentProps<"button"> & { variant?: "primary" | "ghost" | "danger" | "ok" }) {
  const styles = {
    primary: "bg-ink text-white hover:bg-ink-soft",
    ghost: "border border-slate-300 bg-white hover:bg-slate-50",
    danger: "bg-rose-600 text-white hover:bg-rose-700",
    ok: "bg-emerald-600 text-white hover:bg-emerald-700",
  }[variant];
  return (
    <button
      {...props}
      className={`inline-flex items-center justify-center gap-1 rounded-lg px-3 py-1.5 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-50 ${styles} ${className}`}
    />
  );
}

export function PageTitle({ children, actions }: { children: ReactNode; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
      <h1 className="text-2xl font-bold">{children}</h1>
      {actions}
    </div>
  );
}

export function NavLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link href={href} className="block rounded-lg px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100">
      {children}
    </Link>
  );
}

export function fmtDate(v: string | null | undefined): string {
  if (!v) return "—";
  return new Date(v).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" });
}

export function fileUrl(key: string): string {
  return `/api/admin/files?key=${encodeURIComponent(key)}`;
}
