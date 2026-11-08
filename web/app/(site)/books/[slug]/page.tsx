import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { BookGrid } from "@/components/site/BookCard";
import { BookCover } from "@/components/site/BookCover";
import { Breadcrumbs } from "@/components/site/Breadcrumbs";
import { ButtonLink } from "@/components/site/ButtonLink";
import { JsonLd } from "@/components/site/JsonLd";
import { Prose } from "@/components/site/Prose";
import {
  SITE_NAME,
  absoluteUrl,
  ageLabel,
  breadcrumbJsonLd,
  getBook,
  getBooks,
  organizationJsonLd,
  pageMetadata,
  plainText,
  slugify,
  trimLabel,
  type BookDetail,
} from "@/lib/public";

type Params = Promise<{ slug: string }>;

/** Prebuild the known books; others render on first visit (ISR). Empty list when the API is down. */
export async function generateStaticParams() {
  const books = await getBooks();
  return (books ?? []).map((b) => ({ slug: b.slug }));
}

export async function generateMetadata({ params }: { params: Params }): Promise<Metadata> {
  const { slug } = await params;
  const book = await getBook(slug);
  if (!book) return { title: "Book not found", robots: { index: false } };
  return pageMetadata({
    title: book.title,
    description: book.subtitle || plainText(book.description_html) || `A ${SITE_NAME} coloring book for kids.`,
    path: `/books/${book.slug}`,
    image: book.cover_url,
  });
}

function bookJsonLd(book: BookDetail) {
  const url = absoluteUrl(`/books/${book.slug}`);
  const image = book.cover_url ? absoluteUrl(book.cover_url) : undefined;
  const description = plainText(book.description_html, 500);
  return [
    {
      "@type": "Book",
      "@id": `${url}#book`,
      name: book.title,
      alternativeHeadline: book.subtitle || undefined,
      description,
      image,
      url,
      inLanguage: "en",
      bookFormat: "https://schema.org/Paperback",
      numberOfPages: book.page_count,
      typicalAgeRange: `${book.age_min}-${book.age_max}`,
      genre: "Coloring book",
      keywords: book.themes.join(", ") || undefined,
      author: organizationJsonLd,
      publisher: organizationJsonLd,
      ...(book.series ? { isPartOf: { "@type": "BookSeries", name: book.series }, position: book.volume } : {}),
    },
    {
      "@type": "Product",
      name: book.title,
      description,
      image,
      url,
      brand: { "@type": "Brand", name: SITE_NAME },
      // Only a link to where it is sold: no made-up prices, ratings or reviews.
      ...(book.amazon_url ? { offers: { "@type": "Offer", url: book.amazon_url, availability: "https://schema.org/InStock" } } : {}),
    },
    breadcrumbJsonLd([
      { name: "Home", href: "/" },
      { name: "Books", href: "/books" },
      { name: book.title, href: `/books/${book.slug}` },
    ]),
  ];
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl bg-white px-4 py-3 ring-1 ring-ink/5">
      <dt className="text-sm text-ink-soft">{label}</dt>
      <dd className="font-display text-lg font-semibold">{value}</dd>
    </div>
  );
}

export default async function BookPage({ params }: { params: Params }) {
  const { slug } = await params;
  const book = await getBook(slug);
  if (!book) notFound();

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-12">
      <JsonLd data={bookJsonLd(book)} />
      <Breadcrumbs
        items={[
          { name: "Home", href: "/" },
          { name: "Books", href: "/books" },
          { name: book.title, href: `/books/${book.slug}` },
        ]}
      />

      <article className="mt-6">
        <div className="grid gap-8 md:grid-cols-[minmax(0,2fr)_minmax(0,3fr)] md:gap-12">
          <div className="mx-auto w-full max-w-sm md:max-w-none">
            <BookCover book={book} sizes="(min-width: 768px) 40vw, 90vw" priority />
          </div>

          <div className="min-w-0">
            {book.series && (
              <p className="font-semibold text-coral-dark">
                {book.series}
                {book.volume > 0 ? ` · Book ${book.volume}` : ""}
              </p>
            )}
            <h1 className="text-3xl font-bold leading-tight tracking-tight break-words sm:text-5xl">{book.title}</h1>
            {book.subtitle && <p className="mt-3 text-lg text-ink-soft sm:text-xl">{book.subtitle}</p>}

            <dl className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-3">
              <Fact label="Ages" value={ageLabel(book).replace(/^Ages? /, "")} />
              <Fact label="Pages" value={String(book.page_count)} />
              <Fact label="Size" value={trimLabel(book.trim)} />
            </dl>

            {(book.amazon_url || book.etsy_url) && (
              <div className="mt-6 flex flex-col gap-3 sm:flex-row">
                {book.amazon_url && (
                  <ButtonLink href={book.amazon_url} external rel="sponsored noopener" variant="dark">
                    Buy the paperback on Amazon
                  </ButtonLink>
                )}
                {book.etsy_url && (
                  <ButtonLink href={book.etsy_url} external variant="sun">
                    Get the printable on Etsy
                  </ButtonLink>
                )}
              </div>
            )}

            {book.themes.length > 0 && (
              <ul className="mt-6 flex flex-wrap gap-2" aria-label="Themes">
                {book.themes.map((theme) => (
                  <li key={theme}>
                    <Link
                      href={`/books?theme=${slugify(theme)}`}
                      className="inline-block rounded-full bg-sky-soft px-3 py-1 text-sm font-semibold hover:underline"
                    >
                      {theme}
                    </Link>
                  </li>
                ))}
              </ul>
            )}

            {book.description_html && <Prose html={book.description_html} className="mt-4" />}

            {book.ai_note && <p className="mt-6 rounded-2xl bg-sun-soft px-4 py-3 text-ink-soft">{book.ai_note}</p>}
          </div>
        </div>

        {book.preview_urls.length > 0 && (
          <section aria-labelledby="peek" className="mt-14">
            <h2 id="peek" className="text-2xl font-bold sm:text-3xl">
              Peek inside
            </h2>
            <ul className="mt-5 grid grid-cols-2 gap-4 md:grid-cols-4">
              {book.preview_urls.map((src, i) => (
                <li key={src} className="relative aspect-[17/22] overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-ink/5">
                  <Image
                    src={src}
                    alt={`Sample page ${i + 1} from ${book.title}`}
                    fill
                    sizes="(min-width: 768px) 25vw, 45vw"
                    className="object-contain"
                  />
                </li>
              ))}
            </ul>
          </section>
        )}
      </article>

      {book.related.length > 0 && (
        <section aria-labelledby="related" className="mt-16">
          <h2 id="related" className="mb-5 text-2xl font-bold sm:text-3xl">
            You might also like
          </h2>
          <BookGrid books={book.related.slice(0, 4)} />
        </section>
      )}
    </div>
  );
}
