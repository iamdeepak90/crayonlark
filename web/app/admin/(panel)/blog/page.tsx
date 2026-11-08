import PostEditor, { type AdminPost } from "@/components/admin/PostEditor";
import { Card, PageTitle } from "@/components/admin/ui";
import { serverApi } from "@/lib/api";

export default async function BlogPage() {
  const posts = await serverApi<AdminPost[]>("/api/admin/posts");
  const waiting = posts.filter((p) => p.status === "awaiting_approval");
  return (
    <>
      <PageTitle>Blog posts</PageTitle>
      <p className="mb-4 text-sm text-slate-600">
        When a book goes live, the content agent drafts a post. Nothing appears on the website until you publish it here. {waiting.length > 0 && <b>{waiting.length} waiting for you.</b>}
      </p>
      <div className="space-y-4">
        {posts.map((p) => (
          <Card key={p.id} title={p.title}>
            <PostEditor post={p} />
          </Card>
        ))}
        <Card title="New post">
          <PostEditor />
        </Card>
      </div>
    </>
  );
}
