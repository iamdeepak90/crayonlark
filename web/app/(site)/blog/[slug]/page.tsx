import Image from "next/image";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { BookGrid } from "@/components/site/BookCard";
import { Breadcrumbs } from "@/components/site/Breadcrumbs";
import { ButtonLink } from "@/components/site/ButtonLink";
import { JsonLd } from "@/components/site/JsonLd";
import { Prose } from "@/components/site/Prose";
import {
  absoluteUrl,
  breadcrumbJsonLd,
  formatDate,
  getPost,
  getPosts,
  organizationJsonLd,
  pageMetadata,
  type Post,
} from "@/lib/public";

type Params = Promise<{ slug: string }>;

export async function generateStaticParams() {
  const posts = await getPosts();
  return (posts ?? []).map((p) => ({ slug: p.slug }));
}

export async function generateMetadata({ params }: { params: Params }): Promise<Metadata> {
  const { slug } = await params;
  const post = await getPost(slug);
  if (!post) return { title: "Post not found", robots: { index: false } };
  return pageMetadata({
    title: post.seo_title || post.title,
    description: post.seo_description || post.excerpt,
    path: `/blog/${post.slug}`,
    image: post.cover_url,
    type: "article",
  });
}

function postJsonLd(post: Post) {
  const url = absoluteUrl(`/blog/${post.slug}`);
  return [
    {
      "@type": "BlogPosting",
      headline: post.title,
      description: post.seo_description || post.excerpt,
      image: post.cover_url ? absoluteUrl(post.cover_url) : undefined,
      datePublished: post.published_at,
      dateModified: post.updated_at,
      url,
      mainEntityOfPage: url,
      inLanguage: "en",
      author: organizationJsonLd,
      publisher: organizationJsonLd,
    },
    breadcrumbJsonLd([
      { name: "Home", href: "/" },
      { name: "Blog", href: "/blog" },
      { name: post.title, href: `/blog/${post.slug}` },
    ]),
  ];
}

export default async function PostPage({ params }: { params: Params }) {
  const { slug } = await params;
  const post = await getPost(slug);
  if (!post) notFound();

  return (
    <div className="mx-auto max-w-3xl px-5 py-10 sm:py-14">
      <JsonLd data={postJsonLd(post)} />
      <Breadcrumbs
        items={[
          { name: "Home", href: "/" },
          { name: "Blog", href: "/blog" },
          { name: post.title, href: `/blog/${post.slug}` },
        ]}
      />
      <article className="mt-6">
        <header>
          <h1 className="font-display text-3xl font-semibold leading-[1.15] tracking-tight break-words sm:text-[2.75rem]">{post.title}</h1>
          {post.excerpt && <p className="mt-4 text-lg leading-relaxed text-muted">{post.excerpt}</p>}
          <p className="mt-5 flex items-center gap-2 text-sm font-medium text-muted">
            <time dateTime={post.published_at}>{formatDate(post.published_at)}</time>
            <span aria-hidden="true">·</span>
            <span>{post.reading_minutes} min read</span>
          </p>
        </header>
        {post.cover_url && (
          <div className="relative mt-8 aspect-[16/9] overflow-hidden rounded-3xl bg-sun-50">
            <Image src={post.cover_url} alt="" fill priority sizes="(min-width: 768px) 720px, 95vw" className="object-cover" />
          </div>
        )}
        <Prose html={post.html} className="mt-6" />
        <aside className="mt-12 grid items-center gap-6 rounded-3xl bg-sky-50 p-6 sm:grid-cols-[1fr_auto] sm:p-8">
          <div>
            <p className="font-display text-xl font-semibold">Want free coloring pages?</p>
            <p className="mt-1 text-sm text-muted">Join our email list and we&apos;ll send you a free printable pack.</p>
          </div>
          <ButtonLink href="/free-printables" variant="dark" size="sm">
            Get free pages
          </ButtonLink>
        </aside>
      </article>

      {post.books.length > 0 && (
        <section aria-labelledby="books-in-post" className="mt-14">
          <h2 id="books-in-post" className="mb-6 font-display text-2xl font-semibold">
            Books from this post
          </h2>
          <BookGrid books={post.books.slice(0, 3)} />
        </section>
      )}
    </div>
  );
}
