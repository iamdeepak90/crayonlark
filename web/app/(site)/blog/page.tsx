import { EmptyState } from "@/components/site/EmptyState";
import { PageHeader } from "@/components/site/PageHeader";
import { PostGrid } from "@/components/site/PostCard";
import { getPosts, pageMetadata } from "@/lib/public";

export const metadata = pageMetadata({
  title: "Blog",
  description: "Coloring ideas, activity tips and simple classroom helpers from Crayonlark.",
  path: "/blog",
});

export default async function BlogPage() {
  const posts = await getPosts();
  return (
    <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6 sm:py-14">
      <PageHeader title="Blog" intro="Coloring ideas, activity tips and simple classroom helpers." />
      <div className="mt-10">
        {posts && posts.length > 0 ? (
          <PostGrid posts={posts} />
        ) : (
          <EmptyState title="No posts yet">
            <p>Our first posts are being written. Check back soon!</p>
          </EmptyState>
        )}
      </div>
    </div>
  );
}
