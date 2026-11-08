# Crayonlark Automation System + Website — Build Prompt for Claude Code

> Paste everything below into Claude Code at the root of your empty repo.
> Tip: after Phase 0, ask Claude Code to save the key rules from this prompt into `CLAUDE.md` so every future session follows them.

---

## Role and goal

You are the lead engineer building **Crayonlark**, a one-person business that makes AI-assisted kids' coloring and activity books, sells paperbacks on **Amazon KDP**, and sells the same designs as **printable PDFs on Etsy**. The repo is empty.

Build two things in one monorepo:

1. **An automation system** of agents/workers that runs on my VPS, so my only jobs are: pick/approve a niche, approve images, approve covers, approve listings, upload the finished pack to KDP by hand, and press "publish" on Etsy drafts.
2. **A public website** at `crayonlark.com` (catalog, free printables, blog), plus a private admin dashboard at `admin.crayonlark.com` for approvals.

Work in phases (below). At the start, write a short plan and the folder layout, then build Phase 0 → Phase 7 in order. Each phase must run and be tested before the next. Use subagents for independent parallel work (e.g. website and worker code), but keep one consistent architecture. Ask me only when a decision is costly to reverse; otherwise choose sensible defaults and note them in `docs/DECISIONS.md`.

## Hard business rules (never break these)

- **No KDP automation.** KDP has no publishing API. Never script, scrape or browser-automate KDP or Amazon. The system only builds a "KDP upload pack" that I upload by hand.
- **No scraping of Amazon or Etsy pages.** Use official APIs only (Etsy Open API v3, Pinterest API v5), or data I paste/upload.
- **KDP new-title limit: 2 paperbacks + 2 hardcovers per week**, resetting Sunday 00:00 UTC. The scheduler must never plan more than this and should show remaining slots on the dashboard.
- **AI disclosure is mandatory** on KDP and Etsy. Every book/listing record stores which parts were AI-generated (interior images, cover image, text), and the packs/listings include correct disclosure wording. Etsy listings use "Designed by" the seller and state in the description that artwork was made with AI tools and edited by the seller. Never call anything "handmade" or "hand-drawn".
- **No famous characters, brands, logos or living artists' styles** (Disney, Pokémon, Bluey, Peppa Pig, Marvel, Crayola, etc.). Add a blocklist check on prompts, titles, tags and descriptions, plus a vision-QA check on images.
- **Kids' content only**: friendly, age-appropriate, accurate (letters, numbers, animal names must be correct).
- **Human approval gates** cannot be skipped by any agent: niche, image set, cover, listing text, Etsy publish.
- **Budget guard:** total paid API spend (LLM + image + anything else) has a monthly cap, default **₹2,000**, set in env. Track cost per call; warn at 80%; hard-stop paid calls at 100% and notify me.

## Infrastructure

- VPS: 4 vCPU, 24 GB RAM, 200 GB SSD, **no GPU**, running **Coolify** (Docker).
- Deliver a single `docker-compose.yml` that Coolify can deploy from the GitHub repo, with healthchecks, named volumes, restart policies and resource limits. Domains and SSL are set in Coolify's UI; document which service gets which domain.
- All secrets come from environment variables set in Coolify. Commit only `.env.example`. Never commit keys.
- Nightly backups of Postgres and object storage to a backup volume, with 14-day retention and a documented restore command.

### Services (suggested; improve if you have a strong reason)

| Service | Tech | Purpose |
|---|---|---|
| `web` | Next.js (App Router, TypeScript, Tailwind) | Public site `crayonlark.com` + admin at `admin.crayonlark.com` (same app, host-based routing) or a separate `admin` app — your choice |
| `api` | Python FastAPI | REST API for admin, webhooks, Telegram callbacks, Etsy/Pinterest OAuth |
| `worker` | Python + Celery (or RQ) with Redis | All agents and heavy jobs; separate queues: `llm`, `images`, `cpu-heavy`, `publish` |
| `scheduler` | Celery beat (or APScheduler) | Weekly plan, nightly upscaling, Pinterest schedule, reports, backups |
| `bot` | Python Telegram bot | Phone approvals (✅/❌ per image, approve cover/listing), alerts, weekly report |
| `postgres` | Postgres 16 | All state |
| `redis` | Redis | Queue + cache |
| `storage` | MinIO (S3-compatible) | Images, PDFs, mockups, packs |

CPU limits: `cpu-heavy` queue (Real-ESRGAN, potrace, PDF builds) concurrency 1–2 so the website stays fast. Run upscaling in a nightly window by default.

## Provider abstraction (important)

- **LLM providers:** Anthropic, OpenAI and Google Gemini behind one interface. Each agent's model/provider is configurable in a settings table (editable in admin). Log tokens and cost per call.
- **Image providers:** OpenAI image API and Gemini image API behind one interface, **plus a "manual drop" mode**: I generate images in the ChatGPT/Gemini apps and upload them in admin (or drop them in a MinIO bucket), and the pipeline continues from there. Manual mode must work with zero paid image calls.
- Note: my ChatGPT Plus / Gemini Pro / Claude Pro subscriptions do **not** include API access; API keys are separate and optional.
- Use structured outputs (JSON schemas validated with Pydantic) for every agent response. Retries with backoff; idempotent jobs.

## Data model (minimum)

`niches`, `books` (series, volume, trim, page count, status, AI-disclosure fields, KDP/Etsy links), `pages`/`images` (prompt, provider, QA scores, approval state, file keys), `covers`, `listings` (platform: kdp/etsy, title, subtitle, description, keywords/tags, categories, price, status), `etsy_listings` (Etsy IDs, state), `pins`, `jobs` (status, errors, cost), `api_costs`, `sales` (Etsy via API; KDP via CSV import), `settings`, `audit_log` (every approval and publish, with who/when).

Book status state machine:
`idea → niche_approved → concepts_ready → images_generating → images_qa → awaiting_image_approval → cleaning → building → awaiting_cover_approval → listing_draft → awaiting_listing_approval → kdp_pack_ready → kdp_uploaded (manual) → proof_ordered → live` and in parallel `etsy_drafts_created → etsy_published`.

## Agents / workers

1. **Research agent:** from a theme I type (or a CSV/paste of competitor data I provide), suggests 10 niches with age range, angle, risks (trademark/character), and seasonality. Uses an optional web-search API if configured; never scrapes Amazon/Etsy. Output goes to approval.
2. **Concept agent:** for an approved niche, writes 60 scene ideas + image prompts using a house prompt template (thick bold black outlines, simple large shapes, pure white background, no shading/grey/text/border, cute friendly style, portrait). Checks the blocklist.
3. **Art agent:** generates images through the image provider, or waits for manual uploads. Stores originals.
4. **QA agent:** (a) Python checks: resolution, grey-pixel ratio, line thickness estimate, black-fill ratio, text detection; (b) vision-model check for anatomy errors, scary faces, text, character lookalikes, age suitability. Scores each image and recommends keep/reject.
5. **Approval (human):** admin grid + Telegram album. I approve 25–50 images per book.
6. **Cleanup worker:** ImageMagick threshold to pure black/white, potrace to vector, render to 300 DPI, optional Real-ESRGAN (CPU, ncnn or PyTorch CPU build) upscaling, remove specks, re-run Python QA.
7. **Activity generator (no AI art):** Python generators for mazes, word searches (with answer keys), dot-to-dot, letter/number tracing, simple sudoku, sized for print.
8. **Interior builder:** builds the KDP interior PDF: 8.5×11 in default (also 8.5×8.5), no bleed, ≥0.5 in safe margin, 300 DPI, each design on a right-hand page with a blank back, title page, "This book belongs to" page, optional colour test page, answer pages, thank-you/review page, "more Crayonlark books" page, copyright line "© {year} Crayonlark. All rights reserved." Validate page count ≥ 24. Embed fonts.
9. **Cover builder:** HTML/CSS templates rendered to PDF with Playwright. Compute full-wrap size from trim, page count and paper type using KDP's published formula (spine width per page for white paper; 0.125 in bleed); keep barcode area empty; spine text only above ~100 pages. Also export a front-cover JPG thumbnail and a phone-size preview for approval. Brand style below.
10. **Listing agent:** writes KDP title, subtitle, description (HTML-safe), 7 keyword phrases, 3 category suggestions, age range, price (default $9.99, never below), plus 3–5 Etsy listings per book (full PDF, mini packs, bundle, activity pack) with title, 13 tags, description, price in USD, and AI-disclosure text. Blocklist check.
11. **Etsy files + mockups:** export each Etsy product as US Letter and A4 PDFs (<20 MB each) with a license page ("personal and single classroom use only"); make 5–10 mockup images (pages on table, grid, what's included, sizes) from templates.
12. **KDP pack builder:** zip with `interior.pdf`, `cover.pdf`, `listing.md` (copy-paste fields in KDP's order), `ai-disclosure.md`, `upload-checklist.md`, and the week slot it uses. Notify me on Telegram.
13. **Etsy publisher:** Etsy Open API v3 with OAuth 2 (PKCE). Create listings as **drafts** (type digital), upload images and digital files, set tags/price/taxonomy. Only publish after my approval in admin. Respect rate limits.
14. **Pinterest scheduler:** Pinterest API v5. Create boards per niche; schedule 3–5 pins/day from listing images with titles, descriptions and the Etsy URL. Spread pins over time.
15. **Website content agent:** when a book goes live, creates/updates its catalog page on the website (description, preview images, Amazon and Etsy links) and drafts an SEO blog post (e.g. "10 free dinosaur coloring pages for kids") for my approval.
16. **Reporter:** weekly Telegram + email summary: books in each status, KDP slots left this week, Etsy sales (API), imported KDP sales (CSV upload in admin), API spend vs cap, top listings, suggested next volumes.

## Admin dashboard (`admin.crayonlark.com`)

- Single-user login (email + password, hashed; optional TOTP 2FA). Rate-limit login. No public sign-up.
- Pages: Pipeline board (cards per book by status), Niche ideas, Image approval grid (keyboard shortcuts, zoom to 100%), Cover approval (full wrap + thumbnail), Listing editor (edit before approving), KDP packs (download, mark as uploaded, enter ASIN/link), Etsy drafts (preview, approve publish), Pinterest queue, Sales (Etsy sync + KDP CSV import), Costs, Settings (providers, models, budget cap, blocklist, prompt templates), Audit log, Job monitor with retry.
- Every approval is mirrored in Telegram for phone use.

## Public website (`crayonlark.com`)

- Next.js, statically generated where possible, fast (good Core Web Vitals), mobile-first, accessible (WCAG AA).
- Pages: Home, Books catalog (filter by age/theme), Book detail (previews, "Buy on Amazon", "Get the printable on Etsy"), Free Printables (download one free sample pack in exchange for an email: double opt-in, store in Postgres, export CSV), Blog (MDX or DB-backed, posts approved in admin), About, Contact (form → email/Telegram, with spam protection), Privacy Policy, Terms, Printable License page.
- SEO: metadata per page, Open Graph images, `sitemap.xml`, `robots.txt`, schema.org `Book`/`Product` and `BreadcrumbList`, canonical URLs, clean slugs.
- Affiliate-ready: Amazon links configurable per book (Amazon Associates tag optional via env).
- Simple, privacy-friendly analytics (self-hosted Plausible or Umami as an optional compose service).
- No user accounts, no payments on the site (sales happen on Amazon and Etsy).

### Brand style

- Name: **Crayonlark**. Tagline: "Little books for big imaginations".
- Mascot: a friendly lark holding a crayon, thick outlines (placeholder SVG until I provide the final logo).
- Colours: sunny yellow, sky blue, coral, on warm white; dark ink text. One bold rounded display font + one readable body font (Google Fonts, self-hosted).
- Must look clearly different from Crayola (no waxy crayon-tip wordmark, no Crayola colour scheme).

## Quality, testing and docs

- Python: ruff + mypy + pytest. TypeScript: eslint + typecheck + Playwright smoke tests.
- Unit tests for: cover dimension maths, interior page order, margin/DPI checks, KDP weekly slot counter, budget guard, blocklist, Etsy payload building (mock API).
- A `make demo` (or script) that runs the whole pipeline on 5 bundled sample line-art images in manual mode with **no paid API calls**, producing a KDP pack and Etsy files locally.
- GitHub Actions CI: lint, typecheck, tests, Docker build.
- Docs: `README.md` (overview), `docs/DEPLOY_COOLIFY.md` (step-by-step: create project, connect repo, set env vars, assign domains, first run, backups/restore), `docs/WORKFLOW.md` (my weekly routine in plain English), `docs/API_KEYS.md` (how to get Etsy, Pinterest, Telegram, OpenAI/Gemini/Anthropic keys), `docs/DECISIONS.md`.

## Phases (build in this order)

- **Phase 0 — Skeleton:** monorepo layout, compose file, Postgres/Redis/MinIO, FastAPI health, Next.js hello pages for both hosts, CI, `.env.example`, `CLAUDE.md` with these rules. *Done when:* `docker compose up` works locally and on Coolify.
- **Phase 1 — Print engine (manual mode):** upload images → cleanup worker → QA checks → interior PDF + activity generators → Etsy PDFs. *Done when:* `make demo` outputs a valid 8.5×11 interior PDF and US Letter/A4 Etsy PDFs.
- **Phase 2 — Admin + approvals:** auth, pipeline board, image approval, Telegram bot, audit log.
- **Phase 3 — Covers + listings + KDP pack:** cover builder, listing agent, blocklist, budget guard, KDP pack + weekly slot counter.
- **Phase 4 — Etsy + Pinterest:** OAuth, drafts, file upload, approve-to-publish, pin scheduler, mockups.
- **Phase 5 — Public website:** all pages, SEO, free-printable email capture, catalog fed from live books, blog with approval.
- **Phase 6 — AI generation:** LLM/image provider abstraction, research, concept, art and vision-QA agents, cost tracking.
- **Phase 7 — Reports and hardening:** sales import/sync, weekly report, backups, resource limits, load check, docs complete.

After each phase: list what was built, how to run/test it, anything I must do (keys, DNS, approvals), and the next phase plan. Keep the code simple and readable; I am one person maintaining this.
