import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { isAdminHost } from "@/lib/hosts";

/**
 * - admin.<domain>/x  -> rewritten to /admin/x (the admin app)
 * - <public>/admin/*  -> 404 (admin is never served on the public host)
 */
export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const admin = isAdminHost(request.headers.get("host"));

  if (admin) {
    if (pathname.startsWith("/admin")) return NextResponse.next();
    const url = request.nextUrl.clone();
    url.pathname = `/admin${pathname === "/" ? "" : pathname}`;
    const res = NextResponse.rewrite(url);
    res.headers.set("X-Robots-Tag", "noindex, nofollow");
    return res;
  }

  if (pathname === "/admin" || pathname.startsWith("/admin/")) {
    const url = request.nextUrl.clone();
    url.pathname = "/not-found-admin";
    return NextResponse.rewrite(url, { status: 404 });
  }
  return NextResponse.next();
}

export const config = {
  // skip API, Next internals, static files and health
  matcher: ["/((?!api/|_next/|healthz|favicon.ico|robots.txt|sitemap.xml|brand/|fonts/).*)"],
};
