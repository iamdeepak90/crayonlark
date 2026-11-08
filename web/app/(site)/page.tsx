import Image from "next/image";
import Link from "next/link";
import { BookGrid } from "@/components/site/BookCard";
import { ButtonLink } from "@/components/site/ButtonLink";
import { EmptyState } from "@/components/site/EmptyState";
import { JsonLd } from "@/components/site/JsonLd";
import { PostGrid } from "@/components/site/PostCard";
import { SITE_NAME, SITE_TAGLINE, SITE_URL, getBooks, getPosts, organizationJsonLd, pageMetadata } from "@/lib/public";

export const metadata = pageMetadata({
  title: `${SITE_NAME} — ${SITE_TAGLINE}`,
  absoluteTitle: true,
  description:
    "Friendly coloring and activity books for kids, as paperbacks on Amazon and printable PDFs on Etsy. Plus free printables for home and the classroom.",
  path: "/",
});

const VALUES = [
  {
    title: "Made for small hands",
    text: "Big, bold outlines and simple scenes that are easy to color, with age ranges on every book.",
    color: "bg-sky-soft",
  },
  {
    title: "Checked by a person",
    text: "We design pages with help from AI tools, then a person checks and edits every single one.",
    color: "bg-sun-soft",
  },
  {
    title: "Paperback or printable",
    text: "Grab a paperback on Amazon, or a printable PDF on Etsy to print at home or school.",
    color: "bg-white",
  },
];

export default async function HomePage() {
  const [books, posts] = await Promise.all([getBooks(), getPosts(3)]);
  const latest = books?.slice(0, 8) ?? null;

  return (
    <>
      <JsonLd
        data={[
          organizationJsonLd,
          { "@type": "WebSite", name: SITE_NAME, url: SITE_URL, description: SITE_TAGLINE, inLanguage: "en" },
        ]}
      />

      {/* Hero */}
      <section className="bg-sun-soft">
        <div className="mx-auto flex max-w-6xl flex-col-reverse items-center gap-8 px-4 py-12 sm:px-6 md:flex-row md:py-20">
          <div className="flex-1 text-center md:text-left">
            <h1 className="text-4xl font-bold leading-tight tracking-tight sm:text-6xl">Little books for big imaginations</h1>
            <p className="mt-4 text-lg text-ink-soft sm:text-xl">
              Coloring and activity books for kids. Simple, friendly pages for quiet afternoons, long car
              rides and busy classrooms.
            </p>
            <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row md:justify-start">
              <ButtonLink href="/books">Browse the books</ButtonLink>
              <ButtonLink href="/free-printables" variant="outline">
                Get a free printable
              </ButtonLink>
            </div>
          </div>
          <Image
            src="/brand/lark.svg"
            alt="The Crayonlark mascot: a friendly blue lark holding a crayon"
            width={280}
            height={280}
            priority
            className="h-auto w-44 sm:w-64"
          />
        </div>
      </section>

      {/* Value props */}
      <section aria-labelledby="why" className="mx-auto max-w-6xl px-4 py-14 sm:px-6">
        <h2 id="why" className="sr-only">
          Why parents and teachers like our books
        </h2>
        <ul className="grid gap-5 md:grid-cols-3">
          {VALUES.map((v) => (
            <li key={v.title} className={`rounded-[var(--radius-blob)] p-6 ring-1 ring-ink/5 ${v.color}`}>
              <h3 className="text-xl font-semibold">{v.title}</h3>
              <p className="mt-2 text-ink-soft">{v.text}</p>
            </li>
          ))}
        </ul>
      </section>

      {/* Latest books */}
      <section aria-labelledby="latest-books" className="mx-auto max-w-6xl px-4 sm:px-6">
        <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
          <h2 id="latest-books" className="text-3xl font-bold">
            New on the shelf
          </h2>
          <Link href="/books" className="font-semibold text-coral-dark underline underline-offset-4">
            See all books
          </Link>
        </div>
        {latest && latest.length > 0 ? (
          <BookGrid books={latest} />
        ) : (
          <EmptyState title="Our first books are on their way!">
            <p>Meanwhile, grab a free printable coloring pack below.</p>
          </EmptyState>
        )}
      </section>

      {/* Free printable CTA */}
      <section className="mx-auto max-w-6xl px-4 py-14 sm:px-6">
        <div className="flex flex-col items-start gap-4 rounded-[var(--radius-blob)] bg-sky-soft p-8 sm:p-10 md:flex-row md:items-center md:justify-between">
          <div className="max-w-xl">
            <h2 className="text-3xl font-bold">Free coloring pages</h2>
            <p className="mt-2 text-lg text-ink-soft">
              Pop in your email and we&apos;ll send you a free printable pack. Print as many copies as your family or
              class needs.
            </p>
          </div>
          <ButtonLink href="/free-printables" variant="sun">
            Get the free pack
          </ButtonLink>
        </div>
      </section>

      {/* Latest posts */}
      <section aria-labelledby="latest-posts" className="mx-auto max-w-6xl px-4 sm:px-6">
        <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
          <h2 id="latest-posts" className="text-3xl font-bold">
            From the blog
          </h2>
          <Link href="/blog" className="font-semibold text-coral-dark underline underline-offset-4">
            All posts
          </Link>
        </div>
        {posts && posts.length > 0 ? (
          <PostGrid posts={posts} />
        ) : (
          <EmptyState title="Blog posts coming soon">
            <p>Coloring ideas, activity tips and classroom helpers.</p>
          </EmptyState>
        )}
      </section>
    </>
  );
}
