import Link from "next/link";
import { PageHeader } from "@/components/site/PageHeader";
import { THEMES, TINT_BG } from "@/lib/content";
import { getFilters, pageMetadata, slugify } from "@/lib/public";

export const metadata = pageMetadata({
  title: "Coloring book themes",
  description: "Farm animals, ocean, dinosaurs, space, vehicles and more: the themes of Crayonlark coloring and activity books for kids.",
  path: "/themes",
});

export default async function ThemesPage() {
  const filters = await getFilters();
  const counts = new Map((filters?.themes ?? []).map((t) => [t.slug, t.count]));
  // themes that have books but aren't in our planned list still show up
  const extra = (filters?.themes ?? []).filter((t) => !THEMES.some((p) => p.slug === t.slug) && t.slug !== "demo");

  return (
    <div className="mx-auto max-w-6xl px-5 py-14 sm:py-20">
      <PageHeader
        eyebrow="Themes"
        title="Find your child's favourite"
        intro="Every book is built around one theme kids love. Themes marked “coming soon” are on our drawing board right now."
      />
      <ul className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {THEMES.map((t) => {
          const count = counts.get(t.slug) ?? counts.get(slugify(t.name)) ?? 0;
          const inner = (
            <>
              <div className="flex items-start justify-between gap-4">
                <span className="grid h-12 w-12 place-items-center rounded-2xl bg-white text-2xl shadow-soft" aria-hidden="true">
                  {t.emoji}
                </span>
                <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${count ? "bg-ink text-white" : "bg-white/80 text-muted ring-1 ring-line"}`}>
                  {count ? `${count} book${count > 1 ? "s" : ""}` : "Coming soon"}
                </span>
              </div>
              <h2 className="mt-5 font-display text-xl font-semibold">{t.name}</h2>
              <p className="mt-1 text-sm leading-relaxed text-muted">{t.blurb}</p>
              {count > 0 && (
                <span className="mt-5 inline-flex items-center gap-1 text-sm font-semibold">
                  See books <span className="transition group-hover:translate-x-1">→</span>
                </span>
              )}
            </>
          );
          return (
            <li key={t.slug}>
              {count ? (
                <Link href={`/books?theme=${t.slug}`} className={`group block h-full rounded-3xl p-7 transition hover:shadow-soft ${TINT_BG[t.tint]}`}>
                  {inner}
                </Link>
              ) : (
                <div className={`h-full rounded-3xl p-7 ${TINT_BG[t.tint]}`}>{inner}</div>
              )}
            </li>
          );
        })}
        {extra.map((t) => (
          <li key={t.slug}>
            <Link href={`/books?theme=${t.slug}`} className="group block h-full rounded-3xl bg-white p-7 ring-1 ring-line transition hover:shadow-soft">
              <h2 className="font-display text-xl font-semibold capitalize">{t.name}</h2>
              <p className="mt-1 text-sm text-muted">
                {t.count} book{t.count > 1 ? "s" : ""}
              </p>
            </Link>
          </li>
        ))}
      </ul>
      <p className="mt-12 text-center text-sm text-muted">
        Got a theme idea? <Link href="/contact" className="font-semibold text-ink underline underline-offset-4">Tell us</Link>: many of our books start with a
        suggestion from a parent or teacher.
      </p>
    </div>
  );
}
