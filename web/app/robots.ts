import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/public";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: "*", allow: "/", disallow: ["/api/", "/free-printables/confirm", "/unsubscribe"] },
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
