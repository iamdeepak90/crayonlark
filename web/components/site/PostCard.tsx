import Image from "next/image";
import Link from "next/link";
import { formatDate, type PostSummary } from "@/lib/public";
import { CloudDoodle, DinoDoodle, FishDoodle, HouseDoodle, RocketDoodle } from "./Doodles";
import { TINT as tint } from "./tints";

const DOODLES = [HouseDoodle, RocketDoodle, FishDoodle, CloudDoodle];

/** Cover image, or a soft tinted tile with a doodle when the post has no image. */
function PostArt({ post, featured }: { post: PostSummary; featured?: boolean }) {
  if (post.cover_url) {
    return <Image src={post.cover_url} alt="" fill sizes={featured ? "(min-width: 1024px) 55vw, 90vw" : "160px"} className="object-cover transition duration-500 group-hover:scale-[1.04]" />;
  }
  const Doodle = DOODLES[post.slug.length % DOODLES.length];
  if (!featured) {
    return (
      <div className={`grid h-full w-full place-items-center ${tint.bg}`}>
        <div className="w-14">
          <Doodle />
        </div>
      </div>
    );
  }
  return (
    <div className={`relative grid h-full w-full place-items-center ${tint.bg}`}>
      <div className="absolute -right-10 -top-10 h-48 w-48 rounded-lg bg-white/50" />
      <div className="relative flex gap-4 transition duration-500 group-hover:scale-[1.04]">
        <div className="h-32 w-28 -rotate-6 rounded-lg bg-white p-4 shadow-lift sm:h-44 sm:w-36">
          <DinoDoodle className="h-full w-full" />
        </div>
        <div className="h-32 w-28 rotate-3 rounded-lg bg-white p-4 shadow-lift sm:h-44 sm:w-36">
          <Doodle />
        </div>
      </div>
    </div>
  );
}

function Meta({ post }: { post: PostSummary }) {
  return (
    <div className="flex items-center gap-2 text-xs font-medium text-muted">
      <time dateTime={post.published_at}>{formatDate(post.published_at)}</time>
      <span aria-hidden="true">·</span>
      <span>{post.reading_minutes} min read</span>
    </div>
  );
}

export function FeaturedPost({ post }: { post: PostSummary }) {
  return (
    <article className="group">
      <Link href={`/blog/${post.slug}`} className="block">
        <div className="relative aspect-[16/10] overflow-hidden rounded-lg">
          <PostArt post={post} featured />
        </div>
        <div className="mt-6">
          <Meta post={post} />
        </div>
        <h3 className="mt-2 font-display text-2xl font-semibold leading-snug transition group-hover:text-coral-600 sm:text-[1.75rem]">{post.title}</h3>
        {post.excerpt && <p className="mt-3 max-w-lg leading-relaxed text-muted">{post.excerpt}</p>}
        <span className="mt-4 inline-flex items-center gap-1 text-sm font-semibold">
          Read article <span className="transition group-hover:translate-x-1">→</span>
        </span>
      </Link>
    </article>
  );
}

export function PostRow({ post }: { post: PostSummary }) {
  return (
    <article className="group">
      <Link href={`/blog/${post.slug}`} className="flex gap-5 rounded-lg p-3 transition hover:bg-cream">
        <div className="relative aspect-square w-24 shrink-0 overflow-hidden rounded-lg sm:w-36">
          <PostArt post={post} />
        </div>
        <div className="min-w-0 py-1">
          <Meta post={post} />
          <h3 className="mt-2 font-display text-lg font-semibold leading-snug transition group-hover:text-coral-600">{post.title}</h3>
          {post.excerpt && <p className="mt-1 line-clamp-2 text-sm text-muted">{post.excerpt}</p>}
        </div>
      </Link>
    </article>
  );
}

export function PostCard({ post }: { post: PostSummary }) {
  return (
    <article className="group h-full">
      <Link href={`/blog/${post.slug}`} className="flex h-full flex-col rounded-lg bg-white p-3 ring-1 ring-line transition duration-300 hover:-translate-y-1 hover:shadow-lift">
        <div className="relative aspect-[16/10] overflow-hidden rounded-lg">
          <PostArt post={post} />
        </div>
        <div className="flex flex-1 flex-col px-2 pb-2 pt-4">
          <Meta post={post} />
          <h3 className="mt-2 font-display text-xl font-semibold leading-snug transition group-hover:text-coral-600">{post.title}</h3>
          {post.excerpt && <p className="mt-2 line-clamp-3 text-sm leading-relaxed text-muted">{post.excerpt}</p>}
        </div>
      </Link>
    </article>
  );
}

/** Up to 3 per row. */
export function PostGrid({ posts }: { posts: PostSummary[] }) {
  return (
    <ul className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
      {posts.map((post) => (
        <li key={post.slug} className="min-w-0">
          <PostCard post={post} />
        </li>
      ))}
    </ul>
  );
}
