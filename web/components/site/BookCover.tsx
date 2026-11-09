import Image from "next/image";
import type { PublicBook } from "@/lib/public";
import { LarkMark } from "./Logo";
import { TINT as tint } from "./tints";

/** The real cover image, or a simple stand-in "book" in the brand colours until a cover exists. */
export function BookCover({ book, sizes, priority }: { book: PublicBook; sizes: string; priority?: boolean }) {
  const shape = book.trim === "8.5x8.5" ? "aspect-square" : "aspect-[17/22]";
  if (book.cover_url) {
    return (
      <div className={`relative ${shape} w-full overflow-hidden rounded-r-lg rounded-l-sm bg-white shadow-lift`}>
        <Image src={book.cover_url} alt={`Cover of ${book.title}`} fill sizes={sizes} priority={priority} className="object-cover" />
        <div className="absolute inset-y-0 left-0 w-2.5 bg-black/10" aria-hidden="true" />
      </div>
    );
  }
  return (
    <div className={`relative ${shape} w-full rounded-r-lg rounded-l-sm ${tint.solid} shadow-lift`} role="img" aria-label={`Cover of ${book.title}`}>
      <div className="absolute inset-y-0 left-0 w-2.5 rounded-l-sm bg-black/10" aria-hidden="true" />
      <div className={`flex h-full flex-col items-center justify-between px-4 py-5 text-center ${tint.ink}`}>
        <p className="font-display text-base font-semibold leading-tight">{book.title}</p>
        <LarkMark className="h-12 w-12" />
        <p className="text-[10px] font-semibold uppercase tracking-widest opacity-80">Crayonlark</p>
      </div>
    </div>
  );
}
