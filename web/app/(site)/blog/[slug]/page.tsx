import Image from "next/image";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { BookGrid } from "@/components/site/BookCard";
import { Breadcrumbs } from "@/components/site/Breadcrumbs";
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
    <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6 sm:py-12">
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
          <h1 className="text-3xl font-bold leading-tight tracking-tight break-words sm:text-5xl">{post.title}</h1>
          <p className="mt-3 text-ink-soft">
            <time dateTime={post.published_at}>{formatDate(post.published_at)}</time>
          </p>
        </header>
        {post.cover_url && (
          <div className="relative mt-6 aspect-[16/9] overflow-hidden rounded-[var(--radius-blob)] bg-sun-soft">
            <Image src={post.cover_url} alt="" fill priority sizes="(min-width: 768px) 720px, 95vw" className="object-cover" />
          </div>
        )}
        <Prose html={post.html} className="mt-4" />
      </article>

      {post.books.length > 0 && (
        <section aria-labelledby="books-in-post" className="mt-14">
          <h2 id="books-in-post" className="mb-5 text-2xl font-bold">
            Books from this post
          </h2>
          <BookGrid books={post.books.slice(0, 4)} />
        </section>
      )}
    </div>
  );
}
