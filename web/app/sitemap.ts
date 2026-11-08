import type { MetadataRoute } from "next";
import { SITE_URL, getSitemapData } from "@/lib/public";

// Rebuilt with the rest of the public site (ISR, "public" tag).
export const revalidate = 300;

const STATIC_PAGES = ["", "/books", "/free-printables", "/blog", "/about", "/contact", "/privacy", "/terms", "/license"];

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const data = await getSitemapData(); // null when the API is down: static pages only
  return [
    ...STATIC_PAGES.map((path) => ({ url: `${SITE_URL}${path}` })),
    ...(data?.books ?? []).map((b) => ({ url: `${SITE_URL}/books/${b.slug}`, lastModified: b.updated_at })),
    ...(data?.posts ?? []).map((p) => ({ url: `${SITE_URL}/blog/${p.slug}`, lastModified: p.updated_at })),
  ];
}
