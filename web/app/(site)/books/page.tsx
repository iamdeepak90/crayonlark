import Link from "next/link";
import { BookGrid } from "@/components/site/BookCard";
import { EmptyState } from "@/components/site/EmptyState";
import { PageHeader } from "@/components/site/PageHeader";
import { getBooks, getFilters, pageMetadata } from "@/lib/public";

export const metadata = pageMetadata({
  title: "Coloring & activity books",
  description: "All Crayonlark coloring and activity books for kids. Filter by age and theme, then buy the paperback or the printable.",
  path: "/books",
});

type SearchParams = Promise<{ [key: string]: string | string[] | undefined }>;

/** Read and validate ?age=&theme= (anything odd is ignored). */
async function readFilters(searchParams: SearchParams) {
  const sp = await searchParams;
  const ageRaw = typeof sp.age === "string" ? sp.age : "";
  const themeRaw = typeof sp.theme === "string" ? sp.theme : "";
  const age = /^\d{1,2}$/.test(ageRaw) ? Number(ageRaw) : undefined;
  const theme = /^[a-z0-9-]{1,120}$/.test(themeRaw) ? themeRaw : undefined;
  return { age, theme };
}

function hrefWith(current: { age?: number; theme?: string }, change: { age?: number | null; theme?: string | null }) {
  const age = change.age === null ? undefined : (change.age ?? current.age);
  const theme = change.theme === null ? undefined : (change.theme ?? current.theme);
  const qs = new URLSearchParams();
  if (age !== undefined) qs.set("age", String(age));
  if (theme) qs.set("theme", theme);
  return qs.size ? `/books?${qs}` : "/books";
}

function FilterChip({ href, active, children }: { href: string; active: boolean; children: React.ReactNode }) {
  return (
    <li>
      <Link
        href={href}
        aria-current={active ? "true" : undefined}
        className={`inline-block rounded-full border-2 px-4 py-1.5 font-semibold ${
          active ? "border-ink bg-ink text-white" : "border-ink/15 bg-white hover:border-ink"
        }`}
      >
        {children}
      </Link>
    </li>
  );
}

export default async function BooksPage({ searchParams }: { searchParams: SearchParams }) {
  const current = await readFilters(searchParams);
  const [books, filters] = await Promise.all([getBooks(current), getFilters()]);
  const filtered = current.age !== undefined || current.theme !== undefined;

  return (
    <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6 sm:py-14">
      <PageHeader
        title="Coloring & activity books"
        intro="Find our books as paperbacks on Amazon and as printable PDFs on Etsy. Pick an age or a theme to narrow things down."
      />

      {filters && (filters.ages.length > 0 || filters.themes.length > 0) && (
        <nav aria-label="Filter books" className="mt-8 space-y-4">
          {filters.ages.length > 0 && (
            <div>
              <h2 className="mb-2 text-lg font-semibold">Age</h2>
              <ul className="flex flex-wrap gap-2">
                <FilterChip href={hrefWith(current, { age: null })} active={current.age === undefined}>
                  All ages
                </FilterChip>
                {filters.ages.map((age) => (
                  <FilterChip key={age} href={hrefWith(current, { age })} active={current.age === age}>
                    {age}
                  </FilterChip>
                ))}
              </ul>
            </div>
          )}
          {filters.themes.length > 0 && (
            <div>
              <h2 className="mb-2 text-lg font-semibold">Theme</h2>
              <ul className="flex flex-wrap gap-2">
                <FilterChip href={hrefWith(current, { theme: null })} active={current.theme === undefined}>
                  All themes
                </FilterChip>
                {filters.themes.map((t) => (
                  <FilterChip key={t.slug} href={hrefWith(current, { theme: t.slug })} active={current.theme === t.slug}>
                    {t.name}
                  </FilterChip>
                ))}
              </ul>
            </div>
          )}
        </nav>
      )}

      <section aria-label="Books" className="mt-10">
        {books === null ? (
          <EmptyState title="Our bookshelf is being restocked">
            <p>We couldn&apos;t load the books just now. Please check back in a few minutes.</p>
          </EmptyState>
        ) : books.length === 0 ? (
          <EmptyState title={filtered ? "No books match those filters yet" : "Our first books are on their way!"}>
            {filtered ? (
              <Link href="/books" className="font-semibold text-coral-dark underline">
                Show all books
              </Link>
            ) : (
              <p>
                In the meantime, try our{" "}
                <Link href="/free-printables" className="font-semibold text-coral-dark underline">
                  free printable pack
                </Link>
                .
              </p>
            )}
          </EmptyState>
        ) : (
          <BookGrid books={books} />
        )}
      </section>
    </div>
  );
}
