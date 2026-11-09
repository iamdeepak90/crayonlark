"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";
import type { ListingItem } from "@/lib/types";
import { Badge, Button } from "./ui";

const lines = (v: string) => v.split("\n").map((s) => s.trim()).filter(Boolean);

/** Edit one listing. Limits are shown live; blocklist problems come back from the API. */
export default function ListingEditor({ item }: { item: ListingItem }) {
  const router = useRouter();
  const kdp = item.platform === "kdp";
  const locked = item.status === "approved";
  const [title, setTitle] = useState(item.title);
  const [subtitle, setSubtitle] = useState(item.subtitle);
  const [description, setDescription] = useState(item.description);
  const [keywords, setKeywords] = useState(item.keywords.join("\n"));
  const [categories, setCategories] = useState(item.categories.join("\n"));
  const [tags, setTags] = useState(item.tags.join(", "));
  const [price, setPrice] = useState((item.price_cents / 100).toFixed(2));
  const [problems, setProblems] = useState(item.problems);
  const [msg, setMsg] = useState("");

  const tagList = tags.split(",").map((t) => t.trim()).filter(Boolean);
  const titleMax = kdp ? 200 - subtitle.length : 140;

  async function save() {
    setMsg("");
    const body: Record<string, unknown> = { title, description, price_cents: Math.round(Number(price) * 100) };
    if (kdp) Object.assign(body, { subtitle, keywords: lines(keywords), categories: lines(categories) });
    else body.tags = tagList;
    try {
      const out = await api<ListingItem>(`/api/admin/listings/${item.id}`, { method: "PATCH", body });
      setProblems(out.problems);
      setMsg("Saved");
      router.refresh();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "failed");
    }
  }

  const field = "mt-1 block w-full rounded-lg border px-2 py-1 text-sm disabled:bg-slate-50";
  const count = (n: number, max: number) => <span className={n > max ? "font-bold text-rose-700" : "text-slate-500"}> ({n}/{max})</span>;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <Badge value={item.platform} />
        <span className="text-sm font-semibold">{item.product_kind.replaceAll("_", " ")}</span>
        <Badge value={item.status} />
        {item.page_selection.length > 0 && !kdp && <span className="text-xs text-slate-500">{item.page_selection.length} designs</span>}
      </div>
      {Object.keys(problems).length > 0 && (
        <div role="alert" className="rounded-lg bg-rose-50 p-2 text-sm text-rose-800">
          Must fix before approval:{" "}
          {Object.entries(problems)
            .map(([k, v]) => `${k}: ${v.join(", ")}`)
            .join(" · ")}
        </div>
      )}
      <label className="block text-sm">
        Title{count(title.length, titleMax)}
        <input disabled={locked} value={title} onChange={(e) => setTitle(e.target.value)} className={field} />
      </label>
      {kdp && (
        <label className="block text-sm">
          Subtitle
          <input disabled={locked} value={subtitle} onChange={(e) => setSubtitle(e.target.value)} className={field} />
        </label>
      )}
      <label className="block text-sm">
        Description {kdp ? "(HTML: p, b, i, ul, li, br)" : ""}
        {count(description.length, kdp ? 4000 : 6000)}
        <textarea disabled={locked} value={description} onChange={(e) => setDescription(e.target.value)} rows={kdp ? 8 : 10} className={`${field} font-mono`} />
      </label>
      {kdp ? (
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block text-sm">
            7 keywords, one per line{count(lines(keywords).length, 7)}
            <textarea disabled={locked} value={keywords} onChange={(e) => setKeywords(e.target.value)} rows={7} className={field} />
          </label>
          <label className="block text-sm">
            3 categories, one per line{count(lines(categories).length, 3)}
            <textarea disabled={locked} value={categories} onChange={(e) => setCategories(e.target.value)} rows={7} className={field} />
          </label>
        </div>
      ) : (
        <label className="block text-sm">
          13 tags, comma-separated, ≤ 20 characters each{count(tagList.length, 13)}
          <textarea disabled={locked} value={tags} onChange={(e) => setTags(e.target.value)} rows={3} className={field} />
          {tagList.some((t) => t.length > 20) && <span className="text-xs text-rose-700">Some tags are longer than 20 characters.</span>}
        </label>
      )}
      <div className="flex flex-wrap items-end gap-3">
        <label className="block text-sm">
          Price (USD){kdp && <span className="text-slate-500"> min 9.99</span>}
          <input disabled={locked} type="number" step="0.01" min={kdp ? 9.99 : 0.5} value={price} onChange={(e) => setPrice(e.target.value)} className={`${field} w-28`} />
        </label>
        {!locked && (
          <Button variant="outline" onClick={save}>
            Save
          </Button>
        )}
        {msg && <span role="status" className="text-sm text-slate-600">{msg}</span>}
      </div>
      <details className="text-xs text-slate-600">
        <summary>AI disclosure on this listing</summary>
        <pre className="mt-1 whitespace-pre-wrap">{item.ai_disclosure}</pre>
      </details>
    </div>
  );
}
