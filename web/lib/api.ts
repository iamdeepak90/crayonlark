/**
 * API helpers. The FastAPI service lives on the internal network; the browser reaches it through
 * the /api/* rewrite (same origin, so the httpOnly session cookie just works).
 */
const API_INTERNAL_URL = process.env.API_INTERNAL_URL ?? "http://api:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function parse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* not json */
    }
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

/** Server-side fetch (Server Components). Forwards the admin session cookie. */
export async function serverApi<T>(path: string, init: RequestInit = {}): Promise<T> {
  const { cookies } = await import("next/headers");
  const jar = await cookies();
  const res = await fetch(`${API_INTERNAL_URL}${path}`, {
    ...init,
    headers: { ...(init.headers ?? {}), cookie: jar.toString(), "x-requested-with": "crayonlark" },
    cache: "no-store",
  });
  return parse<T>(res);
}

/** Public server-side fetch (no cookies), cacheable with ISR. */
export async function publicApi<T>(path: string, revalidate = 300): Promise<T | null> {
  try {
    const res = await fetch(`${API_INTERNAL_URL}${path}`, { next: { revalidate, tags: ["public"] } });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null; // API down at build time → render the empty state, ISR fills it in later
  }
}

/** Browser-side fetch for client components. */
export async function api<T>(path: string, init: { method?: string; body?: unknown; form?: FormData } = {}): Promise<T> {
  const headers: Record<string, string> = { "x-requested-with": "crayonlark" };
  let body: BodyInit | undefined;
  if (init.form) body = init.form;
  else if (init.body !== undefined) {
    headers["content-type"] = "application/json";
    body = JSON.stringify(init.body);
  }
  const res = await fetch(path, { method: init.method ?? (body ? "POST" : "GET"), headers, body, credentials: "same-origin" });
  return parse<T>(res);
}
