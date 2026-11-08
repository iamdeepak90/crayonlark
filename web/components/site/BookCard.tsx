import Link from "next/link";
import { ageLabel, type PublicBook } from "@/lib/public";
import { BookCover } from "./BookCover";

export function BookCard({ book }: { book: PublicBook }) {
  return (
    <Link href={`/books/${book.slug}`} className="group flex flex-col gap-3 rounded-[var(--radius-blob)] bg-white p-3 shadow-sm ring-1 ring-ink/5 transition hover:-translate-y-0.5 hover:shadow-md">
      <BookCover book={book} sizes="(min-width: 1024px) 280px, (min-width: 640px) 45vw, 90vw" />
      <div className="px-1 pb-1">
        <h3 className="text-lg font-semibold leading-snug group-hover:underline">{book.title}</h3>
        <p className="mt-1 text-sm text-ink-soft">
          {ageLabel(book)} · {book.page_count} pages
        </p>
      </div>
    </Link>
  );
}

/** Responsive grid of book cards. */
export function BookGrid({ books }: { books: PublicBook[] }) {
  return (
    <ul className="grid grid-cols-2 gap-4 sm:gap-6 lg:grid-cols-4">
      {books.map((book) => (
        <li key={book.slug} className="min-w-0">
          <BookCard book={book} />
        </li>
      ))}
    </ul>
  );
}
