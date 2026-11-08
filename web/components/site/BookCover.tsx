import Image from "next/image";
import type { PublicBook } from "@/lib/public";

/** Cover image in the right shape for the trim size, with a soft placeholder if there is no cover yet. */
export function BookCover({ book, sizes, priority }: { book: PublicBook; sizes: string; priority?: boolean }) {
  const shape = book.trim === "8.5x8.5" ? "aspect-square" : "aspect-[17/22]";
  return (
    <div className={`relative ${shape} w-full overflow-hidden rounded-2xl bg-sky-soft shadow-sm`}>
      {book.cover_url ? (
        <Image
          src={book.cover_url}
          alt={`Cover of ${book.title}`}
          fill
          sizes={sizes}
          priority={priority}
          className="object-cover"
        />
      ) : (
        <div className="flex h-full items-center justify-center p-4 text-center font-display text-lg font-semibold text-ink-soft">
          {book.title}
        </div>
      )}
    </div>
  );
}
