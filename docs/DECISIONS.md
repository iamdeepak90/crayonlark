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
