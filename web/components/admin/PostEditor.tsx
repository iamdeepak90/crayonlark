"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";
import { Badge, Button } from "./ui";

export type AdminPost = {
  id: number;
  slug: string;
  title: string;
  excerpt: string;
  body_md: string;
  seo_title: string;
  seo_description: string;
  status: string;
  ai_generated: boolean;
  approved_by: string | null;
  published_at: string | null;
};

/** Edit a blog post (Markdown) and publish it. Publishing is a human approval. */
export default function PostEditor({ post }: { post?: AdminPost }) {
  const router = useRouter();
  const [f, setF] = useState({
    title: post?.title ?? "",
    excerpt: post?.excerpt ?? "",
    body_md: post?.body_md ?? "",
    seo_title: post?.seo_title ?? "",
    seo_description: post?.seo_description ?? "",
  });
  const [msg, setMsg] = useState("");
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setF({ ...f, [k]: e.target.value });

  async function run(fn: () => Promise<unknown>, done: string) {
    setMsg("");
    try {
      await fn();
      setMsg(done);
      router.refresh();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "failed");
    }
  }
  const save = () => (post ? api(`/api/admin/posts/${post.id}`, { method: "PATCH", body: f }) : api("/api/admin/posts", { body: f }));
  const field = "mt-1 block w-full rounded-lg border px-2 py-1 text-sm";

  return (
    <div className="space-y-2">
      {post && (
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <Badge value={post.status} />
          {post.ai_generated && <span className="text-xs text-slate-500">drafted by the content agent</span>}
          {post.published_at && <a className="text-sky-800 underline" href={`${process.env.NEXT_PUBLIC_SITE_URL ?? ""}/blog/${post.slug}`}>view on site</a>}
        </div>
      )}
      <label className="block text-sm">
        Title
        <input value={f.title} onChange={set("title")} className={field} />
      </label>
      <label className="block text-sm">
        Excerpt ({f.excerpt.length}/300)
        <input value={f.excerpt} onChange={set("excerpt")} maxLength={300} className={field} />
      </label>
      <label className="block text-sm">
        Body (Markdown)
        <textarea value={f.body_md} onChange={set("body_md")} rows={12} className={`${field} font-mono`} />
      </label>
      <div className="grid gap-2 sm:grid-cols-2">
        <label className="block text-sm">
          SEO title ({f.seo_title.length}/70)
          <input value={f.seo_title} onChange={set("seo_title")} maxLength={70} className={field} />
        </label>
        <label className="block text-sm">
          SEO description ({f.seo_description.length}/160)
          <input value={f.seo_description} onChange={set("seo_description")} maxLength={160} className={field} />
        </label>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button variant="ghost" onClick={() => run(save, "Saved")}>
          {post ? "Save" : "Create draft"}
        </Button>
        {post && post.status !== "published" && (
          <Button variant="ok" onClick={() => run(async () => { await save(); await api(`/api/admin/posts/${post.id}/decision`, { body: { approve: true } }); }, "Published")}>
            ✅ Save & publish
          </Button>
        )}
        {post && post.status !== "rejected" && (
          <Button variant="danger" onClick={() => run(() => api(`/api/admin/posts/${post.id}/decision`, { body: { approve: false } }), post.status === "published" ? "Unpublished" : "Rejected")}>
            {post.status === "published" ? "Unpublish" : "Reject"}
          </Button>
        )}
        {msg && <span role="status" className="text-sm text-slate-600">{msg}</span>}
      </div>
    </div>
  );
}
