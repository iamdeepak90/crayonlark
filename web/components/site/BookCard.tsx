import Link from "next/link";
import { ageLabel, type PublicBook } from "@/lib/public";
import { BookCover } from "./BookCover";
import { tintFor } from "./tints";

const isNew = (b: PublicBook) => Boolean(b.live_at && Date.now() - new Date(b.live_at).getTime() < 30 * 864e5);

export function BookCard({ book }: { book: PublicBook }) {
  const tint = tintFor(book.slug);
  const theme = book.themes.find((t) => t !== "demo");
  return (
    <article className="group relative flex h-full flex-col rounded-3xl bg-white p-3 ring-1 ring-line transition duration-300 hover:-translate-y-1 hover:shadow-lift">
      <div className={`relative grid aspect-[4/5] place-items-center overflow-hidden rounded-2xl ${tint.bg}`}>
        {isNew(book) && <span className="absolute left-3 top-3 z-10 rounded-full bg-white/95 px-2.5 py-1 text-xs font-semibold shadow-sm">New</span>}
        <div className="w-[64%] transition duration-300 group-hover:-rotate-2 group-hover:scale-[1.03]">
          <BookCover book={book} sizes="(min-width: 1024px) 240px, (min-width: 640px) 30vw, 60vw" />
        </div>
        <span
          aria-hidden="true"
          className="absolute inset-x-3 bottom-3 translate-y-3 rounded-full bg-white/95 py-2 text-center text-sm font-semibold opacity-0 shadow-soft backdrop-blur transition duration-300 group-hover:translate-y-0 group-hover:opacity-100 group-focus-within:translate-y-0 group-focus-within:opacity-100"
        >
          Preview pages
        </span>
      </div>
      <div className="flex flex-1 flex-col px-2 pb-2 pt-4">
        <div className="flex flex-wrap items-center gap-2 text-xs font-medium text-muted">
          {theme && <span className="rounded-full bg-cream px-2 py-0.5 capitalize ring-1 ring-line">{theme}</span>}
          <span>{ageLabel(book)}</span>
        </div>
        <h3 className="mt-2 font-display text-lg font-semibold leading-snug">
          <Link href={`/books/${book.slug}`} className="after:absolute after:inset-0 after:rounded-3xl">
            {book.title}
          </Link>
        </h3>
        <p className="mt-1 text-sm text-muted">
          {book.page_count} pages · {book.trim === "8.5x8.5" ? "8.5 × 8.5 in" : "8.5 × 11 in"}
        </p>
        <div className="mt-auto" />
        {(book.amazon_url || book.etsy_url) && (
          <div className="relative z-10 mt-4 grid grid-cols-2 gap-2 border-t border-line pt-4 text-sm">
            {book.amazon_url ? (
              <a href={book.amazon_url} target="_blank" rel="sponsored noopener" className="rounded-full bg-ink py-2.5 text-center font-semibold text-white transition hover:bg-ink/85">
                Amazon<span className="sr-only"> paperback (opens in a new tab)</span>
              </a>
            ) : (
              <span />
            )}
            {book.etsy_url && (
              <a href={book.etsy_url} target="_blank" rel="noopener" className="rounded-full py-2.5 text-center font-semibold ring-1 ring-line transition hover:ring-ink/25">
                Etsy<span className="sr-only"> printable (opens in a new tab)</span>
              </a>
            )}
          </div>
        )}
      </div>
    </article>
  );
}

/** Book cards, at most 3 per row. */
export function BookGrid({ books }: { books: PublicBook[] }) {
  return (
    <ul className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
      {books.map((book) => (
        <li key={book.slug} className="min-w-0">
          <BookCard book={book} />
        </li>
      ))}
    </ul>
  );
}
