import Link from "next/link";
import { BookGrid } from "@/components/site/BookCard";
import { BookCover } from "@/components/site/BookCover";
import { ButtonLink } from "@/components/site/ButtonLink";
import { DinoDoodle, FishDoodle, HouseDoodle, RocketDoodle } from "@/components/site/Doodles";
import { EmptyState } from "@/components/site/EmptyState";
import { FaqList, faqJsonLd } from "@/components/site/FaqList";
import { JsonLd } from "@/components/site/JsonLd";
import { SectionHeading } from "@/components/site/PageHeader";
import { FeaturedPost, PostRow } from "@/components/site/PostCard";
import { SubscribeForm } from "@/components/site/SubscribeForm";
import { AGE_GROUPS, FAQ } from "@/lib/content";
import { SITE_NAME, SITE_TAGLINE, SITE_URL, ageLabel, getBooks, getFilters, getFreePrintable, getPosts, organizationJsonLd, pageMetadata } from "@/lib/public";

export const metadata = pageMetadata({
  title: "Crayonlark – Coloring & Activity Books for Kids",
  absoluteTitle: true,
  description:
    "Crayonlark makes coloring and activity books for kids ages 2–10. Paperbacks on Amazon, instant printables on Etsy, and free coloring pages.",
  path: "/",
});

const VALUES = [
  { bar: "bg-sun-400", title: "Clear, bold lines", text: "Easy to color inside the lines, even for small hands." },
  { bar: "bg-sky-400", title: "Made for each age", text: "Simple shapes for toddlers, more detail as kids grow." },
  { bar: "bg-coral-400", title: "Screen-free time", text: "Quiet, creative play that builds focus and fine motor skills." },
  { bar: "bg-leaf-400", title: "Reviewed page by page", text: "A person checks every design before it goes into a book." },
];

const Check = () => (
  <span className="text-leaf-600" aria-hidden="true">
    ✓
  </span>
);

export default async function HomePage() {
  const [books, posts, filters, free] = await Promise.all([getBooks(), getPosts(4), getFilters(), getFreePrintable()]);
  const shelf = books?.slice(0, 6) ?? null;
  const hero = books?.[0];
  const [featured, ...sidePosts] = posts ?? [];

  return (
    <>
      <JsonLd
        data={[
          organizationJsonLd,
          { "@type": "WebSite", name: SITE_NAME, url: SITE_URL, description: SITE_TAGLINE, inLanguage: "en" },
          faqJsonLd(FAQ.slice(0, 4)),
        ]}
      />

      {/* Hero */}
      <section className="mx-auto grid max-w-6xl items-center gap-14 px-5 pb-20 pt-14 md:grid-cols-2 md:pb-28 md:pt-20">
        <div>
          <p className="inline-flex items-center gap-2 rounded-full bg-sun-50 px-3 py-1 text-sm font-semibold text-sun-600 ring-1 ring-sun-100">
            <span className="h-1.5 w-1.5 rounded-full bg-sun-400" /> Coloring &amp; activity books · Ages 2–10
          </p>
          <h1 className="mt-5 font-display text-4xl font-semibold leading-[1.1] tracking-tight sm:text-5xl lg:text-[3.5rem]">
            Little books for <span className="text-coral-500">big imaginations</span>
          </h1>
          <p className="mt-5 max-w-md text-lg leading-relaxed text-muted">
            Thoughtfully designed coloring pages, mazes and tracing activities with clear, bold lines. Order a paperback on Amazon or print at home in
            minutes.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <ButtonLink href="/books">Browse books</ButtonLink>
            <ButtonLink href="/free-printables" variant="outline">
              Get free pages
            </ButtonLink>
          </div>
          <dl className="mt-10 grid max-w-md grid-cols-3 gap-6 border-t border-line pt-6">
            <div>
              <dt className="text-sm text-muted">Printed</dt>
              <dd className="mt-1 text-xl font-bold">One side</dd>
            </div>
            <div>
              <dt className="text-sm text-muted">Print sizes</dt>
              <dd className="mt-1 text-xl font-bold">Letter &amp; A4</dd>
            </div>
            <div>
              <dt className="text-sm text-muted">Ages</dt>
              <dd className="mt-1 text-xl font-bold">2–10</dd>
            </div>
          </dl>
        </div>

        <div className="relative mx-auto w-full max-w-md">
          <div className="absolute inset-0 -z-10 translate-x-3 translate-y-3 rounded-[2rem] bg-sky-100 sm:translate-x-6 sm:translate-y-6" />
          <div className="rounded-[2rem] bg-white p-6 shadow-lift">
            <div className="grid grid-cols-2 gap-4">
              {hero ? (
                <Link href={`/books/${hero.slug}`} className="col-span-2 flex items-center gap-5 rounded-2xl bg-sun-50 p-5 transition hover:ring-1 hover:ring-sun-100">
                  <div className="w-24 shrink-0">
                    <BookCover book={hero} sizes="96px" priority />
                  </div>
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wider text-sun-600">Newest book</p>
                    <p className="mt-1 font-bold leading-snug">{hero.title}</p>
                    <p className="mt-1 text-sm text-muted">
                      {hero.page_count} pages · {ageLabel(hero)}
                    </p>
                  </div>
                </Link>
              ) : (
                <div className="col-span-2 flex items-center gap-5 rounded-2xl bg-sun-50 p-5">
                  <div className="grid h-28 w-24 shrink-0 place-items-center rounded-xl bg-sun-400 shadow-soft">
                    <DinoDoodle />
                  </div>
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wider text-sun-600">Coming soon</p>
                    <p className="mt-1 font-bold leading-snug">Our first coloring books</p>
                    <p className="mt-1 text-sm text-muted">Animals, ocean, space and more</p>
                  </div>
                </div>
              )}
              <div className="aspect-square rounded-2xl border border-line p-4">
                <HouseDoodle />
              </div>
              <div className="aspect-square rounded-2xl border border-line p-4">
                <RocketDoodle />
              </div>
            </div>
            <div className="mt-4 flex items-center justify-between rounded-2xl bg-cream px-4 py-3 text-sm">
              <span className="hidden font-medium text-muted sm:inline">Available as</span>
              <span className="flex w-full justify-center gap-2 sm:w-auto">
                <span className="whitespace-nowrap rounded-full bg-white px-3 py-1 font-semibold ring-1 ring-line">Paperback</span>
                <span className="whitespace-nowrap rounded-full bg-white px-3 py-1 font-semibold ring-1 ring-line">Printable PDF</span>
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* Shop by age */}
      <section className="bg-white" aria-labelledby="by-age">
        <div className="mx-auto max-w-6xl px-5 py-20">
          <div className="max-w-xl">
            <h2 id="by-age" className="font-display text-3xl font-semibold tracking-tight">
              Shop by age
            </h2>
            <p className="mt-2 text-muted">The right level of detail and challenge at every stage.</p>
          </div>
          <div className="mt-10 grid gap-5 sm:grid-cols-3">
            {AGE_GROUPS.map((g) => (
              <Link key={g.title} href={`/books?age=${g.age}`} className={`group rounded-3xl p-7 transition hover:shadow-soft ${g.bg}`}>
                <p className={`text-sm font-semibold ${g.eyebrow}`}>{g.label}</p>
                <h3 className="mt-2 font-display text-xl font-semibold">{g.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted">{g.text}</p>
                <span className="mt-6 inline-flex items-center gap-1 text-sm font-semibold">
                  Explore <span className="transition group-hover:translate-x-1">→</span>
                </span>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* Books */}
      <section id="books" className="mx-auto max-w-6xl px-5 py-24" aria-labelledby="popular">
        <SectionHeading
          id="popular"
          eyebrow="Our books"
          title="New on the shelf"
          intro="Paperbacks shipped by Amazon. Printable PDFs delivered instantly on Etsy."
          action={
            filters && filters.themes.length > 0 ? (
              <ul className="flex flex-wrap gap-2 text-sm font-semibold" aria-label="Browse by theme">
                <li>
                  <Link href="/books" className="inline-block rounded-full bg-ink px-4 py-2 text-white">
                    All
                  </Link>
                </li>
                {filters.themes.slice(0, 4).map((t) => (
                  <li key={t.slug}>
                    <Link href={`/books?theme=${t.slug}`} className="inline-block rounded-full px-4 py-2 capitalize text-muted ring-1 ring-line hover:text-ink">
                      {t.name}
                    </Link>
                  </li>
                ))}
              </ul>
            ) : undefined
          }
        />
        <div className="mt-10">
          {shelf && shelf.length > 0 ? (
            <BookGrid books={shelf} />
          ) : (
            <EmptyState title="Our first books are on their way!">
              <p>
                See the <Link href="/themes" className="font-semibold text-coral-600 underline underline-offset-4">themes we&apos;re working on</Link>, and grab
                the free pages below in the meantime.
              </p>
            </EmptyState>
          )}
        </div>
        <div className="mt-12 flex flex-col items-center justify-between gap-4 rounded-2xl bg-white px-6 py-5 ring-1 ring-line sm:flex-row">
          <p className="text-sm text-muted">
            <span className="font-semibold text-ink">New books added regularly.</span> Browse the full collection by age or theme.
          </p>
          <ButtonLink href="/books" size="sm" className="whitespace-nowrap">
            View all books →
          </ButtonLink>
        </div>
      </section>

      {/* Two formats */}
      <section className="bg-white" aria-labelledby="formats">
        <div className="mx-auto max-w-6xl px-5 py-24">
          <div className="mx-auto max-w-xl text-center">
            <h2 id="formats" className="font-display text-3xl font-semibold tracking-tight">
              Two ways to color
            </h2>
            <p className="mt-2 text-muted">The same designs, in the format that suits your family.</p>
          </div>
          <div className="mt-12 grid gap-6 md:grid-cols-2">
            <div className="rounded-3xl border border-line p-8">
              <div className="grid h-12 w-12 place-items-center rounded-2xl bg-sun-50 text-sun-600">
                <svg className="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M4 5a2 2 0 0 1 2-2h12v16H6a2 2 0 0 0-2 2V5z" />
                  <path d="M4 19a2 2 0 0 1 2-2h12" />
                </svg>
              </div>
              <h3 className="mt-5 font-display text-xl font-semibold">Paperback books</h3>
              <p className="mt-2 leading-relaxed text-muted">Printed on demand and delivered by Amazon. Great for gifts, travel and quiet afternoons.</p>
              <ul className="mt-6 space-y-3 text-sm">
                <li className="flex gap-3"><Check /> One design per page, blank on the back</li>
                <li className="flex gap-3"><Check /> Large 8.5 × 11 in format</li>
                <li className="flex gap-3"><Check /> Fast delivery with Amazon</li>
              </ul>
              <ButtonLink href="/books" variant="dark" size="sm" className="mt-8">
                Shop paperbacks
              </ButtonLink>
            </div>
            <div className="rounded-3xl border border-line p-8">
              <div className="grid h-12 w-12 place-items-center rounded-2xl bg-coral-50 text-coral-600">
                <svg className="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M6 9V3h12v6" />
                  <rect x="3" y="9" width="18" height="8" rx="2" />
                  <path d="M7 14h10v7H7z" />
                </svg>
              </div>
              <h3 className="mt-5 font-display text-xl font-semibold">Instant printables</h3>
              <p className="mt-2 leading-relaxed text-muted">Download a PDF and print as many copies as you need, at home or in the classroom.</p>
              <ul className="mt-6 space-y-3 text-sm">
                <li className="flex gap-3"><Check /> US Letter and A4 sizes included</li>
                <li className="flex gap-3"><Check /> Print favourites again and again</li>
                <li className="flex gap-3"><Check /> Ideal for teachers and parties</li>
              </ul>
              <ButtonLink href="/books" variant="outline" size="sm" className="mt-8">
                Shop printables
              </ButtonLink>
            </div>
          </div>
        </div>
      </section>

      {/* Why parents choose */}
      <section className="mx-auto max-w-6xl px-5 py-24" aria-labelledby="why">
        <div className="grid gap-12 md:grid-cols-[1fr_2fr]">
          <div>
            <h2 id="why" className="font-display text-3xl font-semibold tracking-tight">
              Designed with parents in mind
            </h2>
            <p className="mt-3 leading-relaxed text-muted">Every page is checked for clarity and age-appropriate detail before it goes into a book.</p>
            <Link href="/how-we-make-our-books" className="mt-5 inline-flex items-center gap-1 text-sm font-semibold">
              How we make our books <span aria-hidden="true">→</span>
            </Link>
          </div>
          <div className="grid gap-8 sm:grid-cols-2">
            {VALUES.map((v) => (
              <div key={v.title}>
                <div className={`h-1 w-10 rounded-full ${v.bar}`} />
                <h3 className="mt-4 font-bold">{v.title}</h3>
                <p className="mt-1 text-sm leading-relaxed text-muted">{v.text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Free printables */}
      <section id="free" className="mx-auto max-w-6xl px-5 pb-24" aria-labelledby="free-title">
        <div className="grid items-center gap-10 overflow-hidden rounded-[2rem] bg-sky-50 p-8 md:grid-cols-[1.3fr_1fr] md:p-14">
          <div>
            <p className="text-sm font-semibold text-sky-600">Free download</p>
            <h2 id="free-title" className="mt-2 font-display text-3xl font-semibold tracking-tight sm:text-4xl">
              {free?.available && free.pages ? `Get ${free.pages} free coloring pages` : "Get free coloring pages"}
            </h2>
            <p className="mt-3 max-w-md leading-relaxed text-muted">Join our email list for a free printable pack and new pages now and then. No spam, unsubscribe anytime.</p>
            <div className="mt-7">
              <SubscribeForm />
            </div>
          </div>
          <div className="relative mx-auto h-56 w-48" aria-hidden="true">
            <div className="absolute inset-0 translate-x-4 rotate-6 rounded-2xl bg-white shadow-soft" />
            <div className="absolute inset-0 rounded-2xl bg-white p-5 shadow-lift">
              <FishDoodle />
            </div>
          </div>
        </div>
      </section>

      {/* Blog */}
      <section id="blog" className="bg-white" aria-labelledby="blog-title">
        <div className="mx-auto max-w-6xl px-5 py-24">
          <SectionHeading
            id="blog-title"
            eyebrow="Ideas & tips"
            eyebrowClass="text-sky-600"
            title="From the blog"
            intro="Activity ideas, learning tips and printable help for busy parents and teachers."
            action={<ButtonLink href="/blog" variant="outline" size="sm">All articles →</ButtonLink>}
          />
          {featured ? (
            <div className="mt-12 grid gap-8 lg:grid-cols-[1.35fr_1fr]">
              <FeaturedPost post={featured} />
              <div className="flex flex-col gap-6">
                {sidePosts.map((p) => (
                  <PostRow key={p.slug} post={p} />
                ))}
              </div>
            </div>
          ) : (
            <div className="mt-12">
              <EmptyState title="Blog posts coming soon">
                <p>Coloring ideas, activity tips and classroom helpers.</p>
              </EmptyState>
            </div>
          )}
        </div>
      </section>

      {/* FAQ */}
      <section className="mx-auto max-w-3xl px-5 py-24" aria-labelledby="faq-title">
        <h2 id="faq-title" className="text-center font-display text-3xl font-semibold tracking-tight">
          Frequently asked questions
        </h2>
        <div className="mt-10">
          <FaqList items={FAQ.slice(0, 4)} />
        </div>
        <p className="mt-8 text-center text-sm text-muted">
          More answers on our <Link href="/faq" className="font-semibold text-ink underline underline-offset-4">FAQ page</Link>.
        </p>
      </section>
    </>
  );
}
