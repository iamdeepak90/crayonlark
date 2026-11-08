# Public API (used by the public website)

Served by FastAPI under `/api/public/*`. The website calls it server-side through
`publicApi()` in `web/lib/api.ts` (ISR, tag `"public"`). The browser calls the POST endpoints
through the same-origin `/api/*` rewrite. The API never returns anything unpublished: books need
`is_public = true` and status `live`, and posts need status `published`.

All image URLs are same-origin paths (`/api/public/media/...`), so use them directly in `<img>`
or `next/image`. They are cached for one year.

## Types

```ts
type PublicBook = {
  slug: string;
  title: string;
  subtitle: string;
  series: string;            // "" if none
  volume: number;
  age_min: number;
  age_max: number;
  themes: string[];          // e.g. ["ocean animals"]
  page_count: number;
  trim: string;              // "8.5x11" | "8.5x8.5"
  description_html: string;  // safe HTML (p, b, i, ul, ol, li, br)
  cover_url: string | null;  // front cover JPG, 2:3-ish (8.5x11 → 0.773 aspect), ~1200px tall
  preview_urls: string[];    // 0-4 sample interior pages (JPG, portrait)
  amazon_url: string | null; // already includes the Associates tag when configured
  etsy_url: string | null;   // Etsy listing (printable version), if any
  live_at: string | null;    // ISO date
  updated_at: string;
  ai_note: string;           // e.g. "Artwork made with AI tools, edited and checked by Crayonlark." or ""
};

type PostSummary = { slug: string; title: string; excerpt: string; published_at: string; cover_url: string | null };
type Post = PostSummary & { html: string; seo_title: string; seo_description: string; updated_at: string; books: PublicBook[] };
```

## Endpoints

| Method | Path | Returns |
|---|---|---|
| GET | `/api/public/books?age=<n>&theme=<slug>` | `{ books: PublicBook[] }`, newest first. `age` keeps books where age_min ≤ n ≤ age_max |
| GET | `/api/public/books/{slug}` | `PublicBook & { related: PublicBook[] }` or 404 |
| GET | `/api/public/filters` | `{ themes: {slug, name, count}[], ages: number[] }` |
| GET | `/api/public/posts?limit=` | `{ posts: PostSummary[] }` |
| GET | `/api/public/posts/{slug}` | `Post` or 404 |
| GET | `/api/public/sitemap` | `{ books: {slug, updated_at}[], posts: {slug, updated_at}[] }` |
| GET | `/api/public/free-printable` | `{ available: boolean, title: string, pages: number, preview_url: string | null }` |
| POST | `/api/public/subscribe` | body `{ email, website: "", started_at: <ms epoch when form rendered> }` → `{ ok: true, message }` (always the same message: no email enumeration). Sends the confirmation email (double opt-in) |
| GET | `/api/public/confirm?token=` | `{ ok: true, download_url }` (download_url = `/api/public/download?token=…`) or 400 |
| GET | `/api/public/download?token=` | the free PDF (confirmed subscribers only) |
| GET | `/api/public/unsubscribe?token=` | `{ ok: true }` |
| POST | `/api/public/contact` | body `{ name, email, message, website: "", started_at, turnstile_token?: string }` → `{ ok: true }`, or 400/429 with `detail` |
| GET | `/api/public/media/{key}` | image bytes |

**Spam rules (server side):** `website` is a honeypot and must be empty. Forms submitted less
than 3 s after `started_at` are treated as bots. Limits are 5 contact messages and 5 subscribes per
IP per hour. When `TURNSTILE_SECRET` is set, `turnstile_token` is required.

## Revalidation

When a book or post changes, the API sends `POST {WEB_INTERNAL_URL}/revalidate` with the header
`x-revalidate-secret: $REVALIDATE_SECRET`. The web route then revalidates the `"public"` tag.
