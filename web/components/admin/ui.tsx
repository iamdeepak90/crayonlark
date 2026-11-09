import type { VariantProps } from "class-variance-authority";
import Link from "next/link";
import type { ReactNode } from "react";
import { Badge as UiBadge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { CardAction, CardContent, CardHeader, CardTitle, Card as UiCard } from "@/components/ui/card";
import { cn } from "@/lib/utils";

/**
 * Admin building blocks on top of the shadcn/ui components in components/ui.
 * Style rules: zinc palette, lucide icons, corner radius at most 8px.
 */

export { Button } from "@/components/ui/button";

export function Monogram({ className }: { className?: string }) {
  return (
    <span aria-hidden="true" className={cn("grid size-7 shrink-0 place-items-center rounded-md bg-primary text-xs font-bold text-primary-foreground", className)}>
      C
    </span>
  );
}

export function Card({ title, children, actions, className }: { title?: ReactNode; children: ReactNode; actions?: ReactNode; className?: string }) {
  return (
    <UiCard className={cn("gap-4", className)}>
      {(title || actions) && (
        <CardHeader>
          {title && <CardTitle className="text-base">{title}</CardTitle>}
          {actions && <CardAction className="flex flex-wrap items-center gap-2">{actions}</CardAction>}
        </CardHeader>
      )}
      <CardContent>{children}</CardContent>
    </UiCard>
  );
}

export type Tone = "neutral" | "warn" | "info" | "ok" | "bad";

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

/** Status pill: soft colour for states that matter, plain outline for everything else. */
export function Badge({ value, tone }: { value: string; tone?: Tone }) {
  const t = tone ?? STATUS_TONE[value] ?? "neutral";
  return <UiBadge variant={t === "neutral" ? "outline" : t}>{value.replaceAll("_", " ")}</UiBadge>;
}

export function ButtonLink({ href, children, variant = "default", size = "sm" }: { href: string; children: ReactNode } & VariantProps<typeof buttonVariants>) {
  return (
    <Link href={href} className={buttonVariants({ variant, size })}>
      {children}
    </Link>
  );
}

export function PageTitle({ children, actions, description }: { children: ReactNode; actions?: ReactNode; description?: ReactNode }) {
  return (
    <div className="mb-8 flex flex-wrap items-end justify-between gap-3">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">{children}</h1>
        {description && <p className="text-sm text-muted-foreground">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

export function StatTile({ label, value, sub, href, icon, tone }: { label: string; value: ReactNode; sub?: ReactNode; href?: string; icon?: ReactNode; tone?: "bad" }) {
  const body = (
    <>
      <div className="flex items-center justify-between gap-2 text-sm font-medium text-muted-foreground">
        {label}
        {icon && <span className="text-muted-foreground [&_svg]:size-4">{icon}</span>}
      </div>
      <div className={cn("mt-2 text-2xl font-semibold tracking-tight tabular-nums", tone === "bad" && "text-destructive dark:text-red-400")}>{value}</div>
      {sub && <div className="mt-1 text-xs text-muted-foreground">{sub}</div>}
    </>
  );
  const cls = "block rounded-lg border bg-card p-5 text-card-foreground shadow-xs";
  return href ? (
    <Link href={href} className={cn(cls, "transition-colors hover:bg-accent/40")}>
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
