# Decisions

Short log of choices that are not obvious from the code. Newest at the bottom of each section.

## Architecture
1. **One Python package and one image** (`python/`, uv, Python 3.13). The services `api`, `worker`, `worker-heavy`,
   `scheduler`, `bot` and the one-shot `migrate` all run the same image with different commands.
   One thing to build, one place for code.
2. **One Next.js 16 app for both hosts.** `web/proxy.ts` rewrites `admin.*` requests to the `/admin`
   route tree and returns 404 for `/admin` on the public host. (Next 16 renamed `middleware` to `proxy`.)
3. **Only `web` is public.** Next rewrites `/api/*` to `http://api:8000` on the internal Docker network,
   so the API, Postgres, Redis and Garage never get a domain. OAuth callbacks use
   `https://admin.crayonlark.com/api/oauth/...`.
4. **Telegram bot uses long-polling**, so it needs no webhook URL or extra domain. Only `TELEGRAM_ADMIN_CHAT_ID` is obeyed.
5. **Celery + Redis.** `worker` runs queues `default,llm,images,publish` (concurrency 4); `worker-heavy`
   runs `cpu-heavy` with concurrency 1 and `cpus: 2`, so potrace/PDF builds never starve the website.
6. **SQLAlchemy 2 + Alembic.** Enums are stored as plain strings (no Postgres enum migrations).
7. **Auth lives in FastAPI** (argon2, Redis sessions, httpOnly cookie, optional TOTP, login rate limit).
   Single admin user, created with `crayonlark create-admin`. No sign-up.
8. **Approval gates are enforced in code.** `core/approvals.py` is the only place gate transitions
   happen and needs a `HumanActor`, which can only come from an admin session, the whitelisted
   Telegram chat or the CLI (`cli:<name>`). A test fails if agent/worker/provider code mentions
   `HumanActor`. The Etsy publish gate is a per-listing human approval checked right before activation.

## Storage
9. **Garage instead of MinIO.** MinIO stopped publishing community Docker images in late 2025.
   Garage is a small, maintained, S3-compatible store built for single-node self-hosting. Code
   uses plain boto3 S3 calls (`core/storage.py`), so any S3 can replace it. The Garage image is
   `FROM scratch`, so the config is baked into `infra/garage/Dockerfile` (no bind mounts needed
   on Coolify). First-run setup (layout, key import, buckets) goes through the Garage admin API
   in `core/garage_init.py` and is idempotent.
10. **Public images are served by the API** (`/api/public/media/...`) with long cache headers, not by
    Garage's website endpoint. That way there's no extra domain or Host-header tricks.

## Print engine
11. **Real-ESRGAN is off by default.** Cleanup vectorises with potrace and re-renders at 300 DPI, so
    the source resolution stops mattering and CPU upscaling would add hours for nothing. There is
    a hook: set `UPSCALE_ENABLED=true` and `UPSCALE_COMMAND="realesrgan-ncnn-vulkan -i {in} -o {out}"`
    (or any CLI) in a custom image if ever needed.
12. **Interior PDFs use ReportLab**: exact geometry, embedded TTF subsets, vector activities.
    **Covers use HTML/CSS → Playwright Chromium**, as the brief asks.
13. **Fonts:** Fredoka (display) + Nunito (body), OFL. Static instances live in `python/assets/fonts`
    (ReportLab can't use variable fonts); the website self-hosts the same families via `next/font`.
    The canvas default font is set to Nunito so no non-embedded Helvetica reference ever appears.
14. **Margins:** 0.5 in house minimum on all sides; the gutter grows with KDP's page-count table
    (0.375 → 0.875 in). Designs are rendered to 7.5 × 10 in at 300 DPI and only ever scaled down.
15. **Interior page order:** title, copyright, belongs-to, blank, colour test, blank, each design
    on a right-hand page with a blank back, activities (start right), answer keys two per page
    (start right), thank-you + more books, padded to even. Fewer than 24 pages is an error, not padding.
16. **Despeckle threshold scales with image size** (≈0.008 % of pixels): it removes AI noise but
    keeps small details such as eyes.
17. **Tracing words** are a fixed, hand-checked list (A is for Apple … Z is for Zebra), so letters
    and words are always correct.

## Business rules
18. **The `offline` LLM provider and `manual` image provider** cost nothing. Tests and `make demo`
    use only these, and the demo fails if any `api_costs` row is created.
19. **The "Designed by" wording and the AI line are driven by the book's AI-disclosure fields.** A book
    whose art wasn't AI-made doesn't claim it was (the demo sample art is hand-coded shapes).
20. **Covers are paperback-only for now.** Hardcover slots are counted by the weekly limiter, but the
    hardcover case-wrap template is not built yet.

## Covers, listings and packs (Phase 3)
21. **The cover hero is a colourised approved interior picture** (`print/colorize.py` flood-fills
    closed shapes with the brand palette). It costs nothing and matches the inside of the book. The
    cover's AI flag is set to true when that art is AI-made or `ai_cover_image` is ticked.
22. **Chromium rounds PDF paper size to whole CSS pixels** (up to ~0.01 in). After printing, the
    MediaBox is set to the exact KDP full-wrap size; the layout is anchored top-left, so only a
    sliver of outer bleed is affected. The validator then checks the exact size.
23. **Rejecting a cover builds a new version** (theme and hero rotate), and old versions are kept.
    Options (theme, front picture, blurb) can be chosen in admin before rebuilding.
24. **Listing text: the LLM writes it, code enforces the rules.** KDP price ≥ $9.99, 7 keywords
    with no "free/bestseller/Amazon…" claims, 3 categories, safe HTML only (p, b, i, ul, li, br…),
    title+subtitle ≤ 200 characters; Etsy 13 lowercase tags ≤ 20 characters. Disclosure wording is
    appended by code from the book's AI fields, never written by the LLM.
25. **Listing approval is refused while any blocklist hit or rule problem exists.** The check
    lives inside `approvals.approve_all_listings`, so admin and Telegram can't bypass it.
26. **Etsy products per book:** full PDF + bundle + activity pack when the book has activities, and
    mini packs of 10 designs for books with ≥ 10 / ≥ 20 designs (3–5 products). Etsy PDFs are built
    only for approved Etsy listings. A single product can be skipped without rejecting the rest.
27. **The KDP slot week is assigned when the pack is built** (approving listings). Archiving a book
    whose pack was never uploaded releases its slot. The demo does this so it never uses real slots.

## Etsy + Pinterest (Phase 4)
28. **API details were checked against the official OpenAPI specs** (Etsy `oas/3.0.0.json`,
    Pinterest `pinterest/api-description` v5.28) on 2026-11-08, not from memory. Key facts are in
    the module docstrings of `integrations/etsy.py` and `integrations/pinterest.py`.
29. **Etsy listings are `type=download`, `who_made=i_did`, `is_supply=false`.** Etsy has no API
    field for AI. Disclosure therefore lives in the description ("Designed by Crayonlark. The
    artwork was made with AI tools and then edited…"), and `draft_problems` refuses to create a draft
    without it, or with "handmade"/"hand-drawn" anywhere. Tags are sent comma-separated in the
    form body. **Check the first real draft on Etsy** to confirm all 13 tags arrived.
30. **Etsy drafts are idempotent**: each upload step (draft, image n, file letter/a4) is recorded
    in `etsy_listings.uploaded`, so a retry continues instead of duplicating. Publishing calls
    `require_etsy_publish_approval` for every listing *before* any API call.
31. **Rate limits:** Etsy calls are throttled to 5/s through Redis, retried on 429/5xx with
    `retry-after`, and `x-remaining-today` is shown in admin. Pinterest retries on 429.
32. **Pinterest uses the `ai_disclosures: AI_MODIFIED` field** (from the v5 spec) on pins whose
    art is AI-made. Pinterest's OAuth is the confidential-client code flow (HTTP Basic + `state`),
    with `continuous_refresh=true`. Etsy uses PKCE (S256), which Etsy requires.
33. **Mockups are rendered from the real Letter PDF** with Ghostscript + Pillow (no stock photos,
    props or brands): hero, "what's inside" grid, close-up, info card, page previews (8 Etsy
    images, 4:3, 2400×1800) and 2 Pinterest pins (2:3, 1000×1500).
34. **Pins:** planned only after the Etsy listing is active (the pin links to it), at most
    `pinterest.pins_per_day` (default 4) per UTC day inside a 13:00–23:00 UTC window with
    ±20 min jitter. Beat posts at most one due pin every 15 minutes. Boards are named after the
    series/theme and created on Pinterest on first use.

## Public website (Phase 5)
35. **The site shows only what a human released:** books that are `live` and `is_public`,
    and posts a human published (`approvals.decide_post`). Going live sets `is_public` on
    automatically; "Hide from website" on the book page turns it off.
36. **Website images live in the `public-assets` bucket** and are served by
    `/api/public/media/...` with one-year cache headers: the front cover plus 4 sample pages
    rendered on white Letter-shaped pages. Keys are checked against a strict pattern.
37. **All HTML shown publicly is sanitised server-side** with a small allow-list sanitiser
    (`core/html_safe.py`). Markdown is rendered with python-markdown, then sanitised. External
    links get `rel="noopener nofollow"`.
38. **Free printable:** double opt-in. Confirmation and download links are emailed, and the PDF is
    only served to confirmed subscribers. The subscribe endpoint always returns the same message,
    so no one can tell whether an address is on the list. The CSV export holds confirmed addresses only.
39. **Spam protection without third parties by default:** honeypot field, a 3-second time trap,
    and 5 requests per IP per hour. Cloudflare Turnstile is used only when `TURNSTILE_SECRET` is set.
40. **On-demand revalidation:** the API sends `POST http://web:3000/revalidate` with
    `x-revalidate-secret` when a book or post changes. Pages also refresh every 5 minutes (ISR),
    and the web build works with no API running.
41. **Website content agent drafts, a human publishes.** When a book goes live, the agent writes
    a public description (used only if empty and blocklist-clean) and one blog post that waits for
    approval. Publishing is checked against the blocklist again.
42. **Amazon Associates:** the tag is added server-side to amazon.* links only. The site shows the
    required disclosure line only when a tag is configured.
43. **Claude uses the official `anthropic` SDK; OpenAI, Gemini, Brave and Tavily use plain
    `httpx`.** That's one SDK instead of four, and the request/response shapes are easy to read
    and mock. Shapes were checked against each provider's official docs on 2026-11-08. The
    Gemini text provider still sends `responseMimeType` + `responseJsonSchema` (as in Google's
    guide), although Google now lists `responseFormat` as their successor. If Gemini starts
    rejecting them, change `GeminiProvider.request()`.
44. **Claude requests:** structured output (`output_config.format`, schema from
    `anthropic.transform_schema`), adaptive thinking with `effort` from Settings (default
    `medium`), streaming, and `max_tokens` ≥ 16k so thinking can't cut off the JSON. On Opus 5.5,
    Opus 5, Fable 5.1 and Sonnet 5.5 a safety refusal is retried server-side on a fallback model
    (`fallbacks: "default"`), and the cost is priced by the model that actually answered.
45. **Every agent answer is validated with Pydantic**, whatever the provider. One repair retry
    is made on invalid JSON. Refusals are charged but not retried (`LLMRefused`). OpenAI and
    Gemini get a "portable" strict schema: every field required, `additionalProperties: false`,
    length limits removed. Pydantic still enforces the limits afterwards.
46. **Prices live in `providers/pricing.py`** (checked 2026-11-08), and admin → Settings →
    `model_prices` can override them without a deploy. An unknown model is priced
    high on purpose ($10 / $50 per 1M tokens, $0.25 per image), so the guard errs on the safe
    side. Image costs come from the usage the provider returns. The per-image table is only the
    budget reservation.
47. **All agents default to `offline` and images to `manual`.** Nothing paid runs until I choose a
    provider and model in admin → Settings → AI providers. Saving refuses a provider whose
    API key is missing.
48. **Concepts are Image rows with status `pending`** (a prompt, no file). Paid generation is a
    button (`Generate N images`), never automatic. It checks the remaining monthly budget
    before queueing anything, and each image is its own idempotent job (`art:{image_id}`) on the
    `images` queue. In manual mode I copy the prompts and upload a picture per concept. A
    concept can't be approved until it has a picture.
49. **Concepts are written automatically** when I create a book from an approved niche (cheap,
    and free in offline mode). Re-running replaces only unused prompts. Scenes that hit the
    blocklist are dropped.
50. **Vision QA runs on the `llm` queue** after the Python checks, so the cpu-heavy worker
    never waits on a model. The book waits for every vision verdict before asking for approval.
    A failed vision check (budget reached, refusal, outage) marks the image "not checked" and
    never blocks the book; I still review every image. Images go to the model as 1024 px greyscale JPEGs.
51. **Research web search** is optional (Brave or Tavily, official APIs). Amazon and Etsy are
    excluded both in the query (Tavily `exclude_domains`) and in the results (filtered by host),
    so we never read their pages. Each search request goes through the budget guard (`kind="search"`).
52. **QA minimum image side lowered from 1500 to 840 px.** API images are 1024x1536 (OpenAI) or
    896x1200 (Gemini 3:4 at 1K), and cleanup re-draws every line with potrace at 300 DPI, so
    source pixels matter less than clean lines. An already-seeded database keeps its old value:
    change it in admin → Settings → `qa_thresholds`.
53. **KDP sales come from the royalty report CSV that I download and upload** (admin → Sales,
    or `crayonlark kdp-import FILE`). There's no scraping and no KDP login. xlsx is refused, to
    avoid adding a spreadsheet library: export as CSV. The header is matched loosely, EU decimal
    commas are handled, and every row gets a stable id, so re-uploads add nothing twice. Rows
    are matched to books by ASIN.
54. **Etsy sales sync every 6 hours** through the official receipts endpoint, going back 2 days
    before the newest sale we already have. There is one row per transaction
    (`receipt:transaction`), matched to a book through our Etsy listing id. The sync skips
    quietly until Etsy is connected.
55. **Backups go to the `backups` volume on `worker-heavy` every night at 03:00 IST:** a
    `pg_dump -Fc` per day plus a mirror of every Garage bucket (only changed files are copied).
    Files deleted from Garage move to `objects-deleted/DATE/`. Dumps and deleted files are
    kept 14 days (`BACKUP_RETENTION_DAYS`). `restore --day` replaces the database and puts back
    missing or changed files.
56. **The off-site copy uses any S3-compatible bucket** (B2, R2, Wasabi: `BACKUP_S3_*`) through
    boto3, which we already use, instead of rclone. That means no extra binary and no config file.
    It's optional but recommended.
57. **`pg_dump` comes from the PGDG repository (`postgresql-client-16`)**, so it matches the
    Postgres 16 server: Debian's client is version 17, and its dumps don't restore into 16. The
    password is passed as `PGPASSWORD`, never in the command line or in error messages.
58. **Weekly report on Monday 09:00 IST** to Telegram and SMTP (`OWNER_EMAIL`). The KDP figures
    are only as fresh as the last CSV I uploaded, and the report says so.
59. **Postgres is tuned for its 2 GB limit** (shared_buffers 512 MB, effective_cache_size
    1.5 GB, work_mem 16 MB, 100 connections, shm 256 MB). Memory limits add up to 13.5 GB of 24 GB.
    CPU limits are ceilings, and `worker-heavy` (concurrency 1, 2 CPUs) can't starve the website.
60. **Umami runs as its own Coolify one-click service**, not inside our compose file. It updates
    and backs up on its own, and the site only needs `NEXT_PUBLIC_UMAMI_*`.
61. **The load check is a small Python script (`scripts/loadcheck.py`, httpx)**, not k6 or hey,
    so there is nothing extra to install.
62. **The monthly API budget and the ₹/US$ rate are set in admin → Settings** (setting
    `budget`, its own validated card and endpoint, audited), not in env vars. It isn't a secret,
    and I change it more often than I deploy. Until it's saved, the built-in start values apply
    (₹2,000 at 88 ₹/US$). Saving re-arms this month's 80 % and 100 % alerts, so a raised cap warns
    again. A cap of 0 blocks every paid call.
63. **OpenRouter is a fifth provider, next to the official APIs, chosen per agent** (and for
    images) in admin → Settings. Chat completions use `response_format` json_schema (strict),
    plus `provider.require_parameters`, so only providers that honour the schema are used.
    Images use the dedicated `POST /api/v1/images` (3:4, 1K, PNG). The cost we record is
    OpenRouter's own `usage.cost` (credits = USD). Reservations are estimated from the live
    model list (`/api/v1/models`, cached 6 h). Per-image prices vary by provider, so an image
    reserves the safe $0.25 unless `model_prices` says otherwise. The model picker only lists
    models that support structured outputs. Errors that arrive with HTTP 200 are treated as
    errors. Checked against the docs on 2026-11-09.
64. **Settings shows a "Paid APIs" overview** (key set or missing, which agents use it, spend
    this month). Keys were env vars at first; see 66 for where they live now.
65. **The compose file asks only for values I provide.** Since 66, that means just the 7
    required secrets, the same list as `.env.example`. The domains, database name and user, `ENVIRONMENT`, the KDP limit (2+2, a
    hard rule, so not configurable), SMTP port 587, Etsy "when made", backup retention (14 days)
    and upscaling (off) are written into `docker-compose.yml` or are code defaults. Fewer knobs
    in Coolify means fewer ways to break a deploy. To change one, edit the compose file and push.
66. **Coolify holds only the 7 infra secrets; every optional integration is set in admin →
    Settings → Integrations** (2026-11-09, owner's choice: deploys must be easy). This covers AI
    keys, web search, Telegram, SMTP, Etsy, Pinterest, the off-site backup target, the Amazon
    tag, Turnstile and Umami.
    - **Storage:** one `settings` row, `integrations`, with an on/off switch per group.
    - **Encryption:** secret fields use Fernet, with a key derived from `SECRET_KEY` (sha256). They
      are write-only in the API (only "set" is returned) and the audit log records only which
      fields changed.
    - **How the code reads them:** `config.get_settings()` merges them over the env settings,
      re-read every 30 s per process, so workers, the bot and beat pick up changes without a
      redeploy. The database connection itself uses `env_settings()`.
    - **Telegram bot:** it waits for a token and exits when the token changes, and Docker
      restarts it.
    - **Website:** it reads Umami, the Turnstile site key and the Amazon tag from
      `GET /api/public/site-config` (ISR, 5 min) instead of build-time `NEXT_PUBLIC_*`.
    - **Env vars:** a non-empty env var still wins, for local tests.
    - **Trade-off:** keys are now in the database and its backups, protected by `SECRET_KEY`. If
      `SECRET_KEY` changes, the saved keys show "enter again".
67. **Empty env vars count as "not set"** (`env_ignore_empty=True`). Coolify passes every
    variable it has stored into every container, including empty leftovers it won't let me
    delete. An empty `MONTHLY_BUDGET_INR` used to crash startup (migrate exit 1, 2026-11-09).
    The weekly KDP limit (2+2) is a `ClassVar` now, so no stray env var can raise it.
68. **Two looks: playful public site, minimalist admin.** The public site follows the owner's
    `index.html` mockup (Plus Jakarta Sans + IBM Plex Serif, cream/sun/sky/coral/leaf). Sun,
    sky and leaf text shades are darkened (`*-600`) to pass WCAG AA. Book grids show at most 3
    per row. The admin deliberately does **not** copy that look. It is a neutral zinc
    greyscale, sans only, with one blue accent and flat bordered surfaces. It is done by
    re-pointing the palette CSS variables inside `.admin` (and `.dark .admin` for dark mode), so
    the existing admin pages changed without per-page edits. Dark mode is saved in localStorage,
    defaults to the OS setting and is applied before paint by an inline script.
69. **Starter content never skips a gate.** `crayonlark starter-content` adds blog posts as
    DRAFTS and niches as PROPOSED, and builds the free printable from the 5 bundled, code-drawn
    pages (`ai_artwork=False`). `crayonlark demo-data` adds two "(Demo)" books that stop at
    "awaiting image approval" and are removed with `--remove`. Its idea approvals are the owner
    acting from the terminal (`cli:demo-data`).
