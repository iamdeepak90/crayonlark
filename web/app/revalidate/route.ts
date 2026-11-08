import { timingSafeEqual } from "node:crypto";
import { revalidateTag } from "next/cache";

/**
 * On-demand ISR. The API calls POST /revalidate (not /api/*, which is rewritten to the API) with
 * header x-revalidate-secret when a book or post changes; we expire everything tagged "public".
 */
function secretMatches(given: string | null): boolean {
  const expected = process.env.REVALIDATE_SECRET;
  if (!expected || !given) return false;
  const a = Buffer.from(given);
  const b = Buffer.from(expected);
  return a.length === b.length && timingSafeEqual(a, b);
}

export async function POST(request: Request) {
  if (!secretMatches(request.headers.get("x-revalidate-secret"))) {
    return Response.json({ revalidated: false }, { status: 401 });
  }
  // Next 16 signature: revalidateTag(tag, profile). { expire: 0 } = the next visit gets fresh data.
  revalidateTag("public", { expire: 0 });
  return Response.json({ revalidated: true });
}
