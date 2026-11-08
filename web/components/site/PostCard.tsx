import Image from "next/image";
import Link from "next/link";
import { formatDate, type PostSummary } from "@/lib/public";

export function PostCard({ post }: { post: PostSummary }) {
  return (
    <article className="flex h-full flex-col overflow-hidden rounded-[var(--radius-blob)] bg-white shadow-sm ring-1 ring-ink/5">
      {post.cover_url && (
        <div className="relative aspect-[16/9] bg-sun-soft">
          <Image src={post.cover_url} alt="" fill sizes="(min-width: 768px) 33vw, 90vw" className="object-cover" />
        </div>
      )}
      <div className="flex flex-1 flex-col gap-2 p-5">
        <h3 className="text-xl font-semibold leading-snug">
          <Link href={`/blog/${post.slug}`} className="hover:underline">
            {post.title}
          </Link>
        </h3>
        <p className="text-sm text-ink-soft">
          <time dateTime={post.published_at}>{formatDate(post.published_at)}</time>
        </p>
        {post.excerpt && <p className="text-ink-soft">{post.excerpt}</p>}
      </div>
    </article>
  );
}

export function PostGrid({ posts }: { posts: PostSummary[] }) {
  return (
    <ul className="grid gap-6 md:grid-cols-3">
      {posts.map((post) => (
        <li key={post.slug} className="min-w-0">
          <PostCard post={post} />
        </li>
      ))}
    </ul>
  );
}
