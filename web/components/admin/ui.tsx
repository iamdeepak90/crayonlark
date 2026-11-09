import Link from "next/link";
import type { ComponentProps, ReactNode } from "react";

/** Minimal admin UI kit: flat surfaces, hairline borders, one accent. Colours follow light/dark via CSS variables. */

export function Monogram({ className = "h-7 w-7 text-xs" }: { className?: string }) {
  return (
    <span aria-hidden="true" className={`grid shrink-0 place-items-center rounded-md bg-ink font-bold text-white ${className}`}>
      C
    </span>
  );
}

export function Card({ title, children, actions, className = "" }: { title?: ReactNode; children: ReactNode; actions?: ReactNode; className?: string }) {
  return (
    <section className={`rounded-xl border border-slate-200 bg-white p-5 ${className}`}>
      {(title || actions) && (
        <div className="mb-4 flex items-center justify-between gap-3">
          {title && <h2 className="text-sm font-semibold tracking-tight">{title}</h2>}
          {actions}
        </div>
      )}
      {children}
    </section>
  );
}

const TONES = {
  neutral: "bg-slate-100 text-slate-600 ring-slate-200",
  warn: "bg-amber-50 text-amber-700 ring-amber-600/20 dark:bg-amber-400/10 dark:text-amber-300 dark:ring-amber-400/20",
  info: "bg-blue-50 text-blue-700 ring-blue-600/20 dark:bg-blue-400/10 dark:text-blue-300 dark:ring-blue-400/20",
  ok: "bg-emerald-50 text-emerald-700 ring-emerald-600/20 dark:bg-emerald-400/10 dark:text-emerald-300 dark:ring-emerald-400/20",
  bad: "bg-rose-50 text-rose-700 ring-rose-600/20 dark:bg-rose-400/10 dark:text-rose-300 dark:ring-rose-400/20",
} as const;

export type Tone = keyof typeof TONES;

const STATUS_TONE: Record<string, Tone> = {
  awaiting_image_approval: "warn",
  awaiting_cover_approval: "warn",
  awaiting_listing_approval: "warn",
  pending: "warn",
  proposed: "warn",
  draft: "warn",
  kdp_pack_ready: "info",
  running: "info",
  generating: "info",
  images_generating: "info",
  queued: "info",
  live: "ok",
  approved: "ok",
  succeeded: "ok",
  published: "ok",
  confirmed: "ok",
  rejected: "bad",
  failed: "bad",
};

export function Badge({ value, tone }: { value: string; tone?: Tone }) {
  return (
    <span className={`inline-flex items-center rounded-md px-1.5 py-0.5 text-xs font-medium ring-1 ring-inset ${TONES[tone ?? STATUS_TONE[value] ?? "neutral"]}`}>
      {value.replaceAll("_", " ")}
    </span>
  );
}

export function Button({ variant = "primary", className = "", ...props }: ComponentProps<"button"> & { variant?: "primary" | "ghost" | "danger" | "ok" }) {
  const styles = {
    primary: "bg-ink text-white hover:opacity-90",
    ghost: "border border-slate-200 bg-white text-ink hover:bg-slate-50",
    danger: "bg-rose-600 text-white hover:bg-rose-700",
    ok: "bg-emerald-600 text-white hover:bg-emerald-700",
  }[variant];
  return (
    <button
      {...props}
      className={`inline-flex h-8 items-center justify-center gap-1.5 rounded-md px-3 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50 ${styles} ${className}`}
    />
  );
}

export function ButtonLink({ href, children, variant = "primary" }: { href: string; children: ReactNode; variant?: "primary" | "ghost" }) {
  const styles = variant === "primary" ? "bg-ink text-white hover:opacity-90" : "border border-slate-200 bg-white text-ink hover:bg-slate-50";
  return (
    <Link href={href} className={`inline-flex h-8 items-center justify-center gap-1.5 rounded-md px-3 text-sm font-medium transition ${styles}`}>
      {children}
    </Link>
  );
}

export function PageTitle({ children, actions, description }: { children: ReactNode; actions?: ReactNode; description?: ReactNode }) {
  return (
    <div className="mb-8 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{children}</h1>
        {description && <p className="mt-1 text-sm text-slate-500">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

export function StatTile({ label, value, sub, href, tone }: { label: string; value: ReactNode; sub?: ReactNode; href?: string; tone?: "bad" | "warn" }) {
  const body = (
    <>
      <p className="text-xs font-medium text-slate-500">{label}</p>
      <p className={`mt-2 text-2xl font-semibold tracking-tight tabular-nums ${tone === "bad" ? "text-rose-600 dark:text-rose-400" : ""}`}>{value}</p>
      {sub && <div className="mt-1 text-xs text-slate-500">{sub}</div>}
    </>
  );
  const cls = "block rounded-xl border border-slate-200 bg-white p-4";
  return href ? (
    <Link href={href} className={`${cls} transition-colors hover:border-slate-300`}>
      {body}
    </Link>
  ) : (
    <div className={cls}>{body}</div>
  );
}

export function fmtDate(v: string | null | undefined): string {
  if (!v) return "—";
  return new Date(v).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" });
}

export function fileUrl(key: string): string {
  return `/api/admin/files?key=${encodeURIComponent(key)}`;
}
