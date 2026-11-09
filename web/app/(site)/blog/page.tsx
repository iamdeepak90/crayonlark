import { EmptyState } from "@/components/site/EmptyState";
import { PageHeader } from "@/components/site/PageHeader";
import { FeaturedPost, PostGrid, PostRow } from "@/components/site/PostCard";
import { getPosts, pageMetadata } from "@/lib/public";

export const metadata = pageMetadata({
  title: "Blog",
  description: "Coloring ideas, activity tips and simple classroom helpers from Crayonlark.",
  path: "/blog",
});

export default async function BlogPage() {
  const posts = await getPosts();
  const [featured, ...rest] = posts ?? [];
  const side = rest.slice(0, 3);
  const more = rest.slice(3);

  return (
    <div className="mx-auto max-w-6xl px-5 py-14 sm:py-20">
      <PageHeader eyebrow="Ideas & tips" title="The Crayonlark blog" intro="Activity ideas, learning tips and printable help for busy parents and teachers." />
      <div className="mt-12">
        {featured ? (
          <>
            <div className="grid gap-8 lg:grid-cols-[1.35fr_1fr]">
              <FeaturedPost post={featured} />
              <div className="flex flex-col gap-6">
                {side.map((p) => (
                  <PostRow key={p.slug} post={p} />
                ))}
              </div>
            </div>
            {more.length > 0 && (
              <section aria-labelledby="more-posts" className="mt-20">
                <h2 id="more-posts" className="mb-8 font-display text-2xl font-semibold">
                  More articles
                </h2>
                <PostGrid posts={more} />
              </section>
            )}
          </>
        ) : (
          <EmptyState title="No posts yet">
            <p>Our first posts are being written. Check back soon!</p>
          </EmptyState>
        )}
      </div>
    </div>
  );
}
