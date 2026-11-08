# Phase reports

## Phase 0: Skeleton ✅
**Built:** monorepo layout; `docker-compose.yml` (Coolify) + `docker-compose.dev.yml`; Postgres 16,
Redis 7, Garage with an idempotent init; one-shot `migrate` service (Garage buckets + Alembic +
default settings); FastAPI `/api/health` (db, redis, storage); Celery worker/heavy/beat; bot
heartbeat; Next.js 16 app with host routing; CI; `.env.example`; `CLAUDE.md`.

**Run/test:** `make up` → `docker compose ... ps` shows everything healthy;
`curl localhost:3000/api/health`; `curl -H 'Host: admin.localhost:3000' localhost:3000/`.

**Verified locally:** all 9 services healthy; `/admin` on the public host returns 404; admin host
returns `X-Robots-Tag: noindex`.

## Phase 1: Print engine (manual mode) ✅
**Built:** `print/qa_checks.py` (resolution, grey ratio, line thickness, black fill, frame, Tesseract
text); `print/cleanup.py` (ImageMagick threshold → despeckle → potrace → 300 DPI render);
activity generators (maze, word search, dot-to-dot, letter/number tracing, 4×4/6×6 sudoku) with
answer keys; `print/interior.py` + `print/validate.py`; `print/etsy_files.py` (Letter + A4, license
page, < 20 MB); `core/pipeline.py` service layer; Celery tasks on `cpu-heavy`; inbox bucket scan;
`core/state_machine.py` + `core/approvals.py`; 5 original sample images; `make demo`.

**Run/test:** `make demo` → `demo-output/<book>/kdp/interior.pdf` and `etsy/*-letter.pdf`,
`*-a4.pdf`. `make test`.

**Verified:** demo produces a 32-page 8.5×11 interior (300 DPI, all fonts embedded), Letter/A4
Etsy PDFs (~0.3 MB each), 0 paid API calls; 39 tests pass; ruff + mypy clean.

## Phase 2: Admin + approvals ✅
**Built:** FastAPI auth (argon2, Redis sessions, httpOnly cookie, TOTP 2FA with QR, login rate
limit 10/15 min per IP and per email, CSRF header check); admin API for books, uploads, image
decisions, image-set approval, manual KDP steps, niches, job monitor with retry, audit log and
settings; Telegram bot (long-polling, `/start` shows your chat id, `/status`, inline ✅/❌ per image,
"Approve image set", niche approve/reject), with Telegram review requests sent from the `publish`
queue; Next.js admin: login, pipeline board (KDP slots, budget, failed jobs), new book form with the
AI-disclosure checkboxes and activity plan, book page with drag-and-drop uploader, keyboard image
grid (arrows, A/R, Z = 100 % zoom), niches, jobs, audit log, settings editor, 2FA setup. KDP slot
counter and budget guard core modules (planned for Phase 3) landed early because the dashboard uses them.

**Run/test:** `make up`, then `make admin` (creates your login), then open http://admin.localhost:3000.
`make test` covers auth, CSRF, rate limits, TOTP, single-admin, audit, Telegram callbacks, the
budget guard, KDP slots and the full manual pipeline. `cd web && pnpm test:e2e` runs the smoke tests.

**You need to:** create a Telegram bot with @BotFather, set `TELEGRAM_BOT_TOKEN`, message the bot
`/start`, and copy the chat id it replies with into `TELEGRAM_ADMIN_CHAT_ID`.

**Verified:** through HTTP on the running stack: login → create book → upload 5 images → QA on
worker-heavy → awaiting approval → approve → 5 cleanups → interior (28 pages) → Etsy PDFs, no
failed jobs. 54 Python tests and 7 Playwright tests pass.

## Phase 3: Covers, listings, KDP pack ✅
**Built:** cover maths (spine per paper type, full wrap, barcode keep-out, spine text from 100
pages); an HTML/CSS cover template rendered by Playwright to an exact-size PDF with embedded fonts,
plus a 150 DPI preview, a JPG thumbnail and a phone-size preview; colourised hero art; 3 colour
themes. Listing agent with Pydantic output (offline provider in tests and demo), with rules
enforced in code; blocklist check on all listing fields; AI-disclosure text from the book fields.
KDP upload pack zip: `interior.pdf`, `cover.pdf`, `listing.md` (KDP field order), `ai-disclosure.md`,
`upload-checklist.md`, `week-slot.txt`, `cover-thumbnail.jpg`. Etsy Letter/A4 PDFs per approved
Etsy listing. Flow: interior → cover (cpu-heavy) → Telegram photo with ✅/🔁 → listings (llm queue)
→ Telegram summary with ✅/🔁 → pack + Etsy files → Telegram "pack ready". Admin pages: cover review
(full wrap, phone size, rebuild with theme/picture/blurb), listing editor (live limits, blocklist
warnings, skip one Etsy product, redraft), KDP packs (slots this week and next 4, downloads,
"I uploaded it" → proof → live with ASIN). Archiving a never-uploaded pack releases its KDP slot.

**Run/test:** `make demo` now also writes `demo-output/<slug>/kdp-pack-<slug>.zip`, `kdp/cover.pdf`,
cover previews and 6 Etsy PDFs, all validated, still with 0 paid calls. `make test` adds listing
rules, safe HTML, disclosure, pack zip and the full cover → listings → pack flow (including the
GateError for non-humans, the Telegram cover button and the blocklist refusal).

**You need to:** nothing new. Real listing text needs an LLM key (Phase 6). Until then the
offline agent writes plain, correct drafts that you edit in admin.

**Verified:** `make demo` passes. Over HTTP on the running stack: book 4 → cover v1 → approve →
offline listings → approval refused for "Peppa Pig" in an Etsy title → fixed → approved → pack +
6 Etsy PDFs, slot counter 1/2 paperbacks this week, no failed jobs. 73 Python tests pass; eslint,
tsc and the admin pages were checked with screenshots.

## Phase 4: Etsy + Pinterest ✅
**Built:** OAuth connect flows for Etsy (PKCE S256) and Pinterest from admin, with tokens
encrypted in Postgres and refreshed automatically. Etsy client: `x-api-key keystring:secret`,
Bearer `user_id.token`, 5 req/s throttle, 429/`retry-after` handling, daily quota shown in admin.
Pure payload builder plus a rule check (taxonomy set, 13 tags, the "Designed by" disclosure line,
no "handmade"). Idempotent draft creation (draft → 8 mockup images → Letter + A4 files).
Approve-to-publish gate in admin and Telegram (`✅ Publish on Etsy`), then activation. Pillow
mockups from the real PDFs (8 Etsy images + 2 pins per product). Pinterest client (boards with
bookmark paging, pins as base64 JPEG with `ai_disclosures`), pin planner (3–5/day with jitter)
and a 15-minute beat poster. Admin pages: **Etsy drafts** (connect, problems, mockups, create
drafts, retry, approve & publish) and **Pinterest** (connect, boards, scheduled/posted/failed pins
with cancel/retry). `crayonlark etsy-taxonomy <word>` finds the taxonomy id. `make demo` now also
writes the mockups.

**Flow:** listings approved → pack + Etsy PDFs → mockups → (if Etsy is connected) drafts →
Telegram/admin "approve publish" (you) → active on Etsy → pins scheduled → posted.

**Run/test:** `make test` adds mocked Etsy and Pinterest runs (respx): 429 retry, headers,
form fields, idempotent re-run, the publish gate, pin payload and the daily pin limit.

**You need to:** create the Etsy app (callback `https://admin.crayonlark.com/api/oauth/etsy/callback`),
set `ETSY_API_KEY`, `ETSY_SHARED_SECRET`, `ETSY_SHOP_ID`, connect in admin → Etsy, then run
`crayonlark etsy-taxonomy coloring` and set `ETSY_TAXONOMY_ID`. Create a Pinterest app (redirect
`https://admin.crayonlark.com/api/oauth/pinterest/callback`), set `PINTEREST_APP_ID` and
`PINTEREST_APP_SECRET`, then connect in admin → Pinterest. Etsy requires an HTTPS callback, so
connecting only works on the deployed admin. After the first real draft, check on Etsy that the
tags and the files look right before you approve publishing.

**Verified:** 78 Python tests pass, plus ruff and mypy. On the running stack, mockups were built
for the Ocean book (8 per product), the Etsy and Pinterest pages render, and OAuth refuses without
keys (400) or without a session (401). The real Etsy and Pinterest calls are untested until the
keys exist.

## Phase 5: Public website ✅
**Built:**
- **Public API** (`docs/PUBLIC_API.md`): catalog with age/theme filters, book detail with related books, filters, blog, sitemap data, free printable, subscribe → confirm → download (double opt-in), unsubscribe, contact form (honeypot, time trap, per-IP limits, optional Turnstile), and cached public media.
- **Backend services:** server-side HTML sanitiser; SMTP email; website images in `public-assets` (front cover plus 4 sample pages); on-demand revalidation of the web app.
- **Website content agent:** drafts a public description and a blog post. The post only goes live after you approve it, and the blocklist is checked again at publish.
- **Go-live hook:** "Mark live" now triggers assets → visible on site → blog draft → revalidate.
- **Public site** (Next 16): Home, Books with filters, Book page (cover, "Peek inside", Amazon/Etsy buttons, AI note), Free printables with confirm and unsubscribe, Blog, About (honest about AI), Contact, Privacy, Terms, License. Also canonical/OG/Twitter metadata, a generated `/og.png`, JSON-LD (Organization, WebSite, Book, Product, BreadcrumbList, BlogPosting), `sitemap.xml`, `robots.txt`, optional Umami, mobile-first layout, and empty states when the API is down.
- **Admin:** Blog posts (edit Markdown, publish/unpublish), Subscribers (counts, confirmed-only CSV export), Messages. Book page gains "Show/Hide on website" and "Use as free printable".

**Run/test:** `make test` (83 Python tests, including visibility rules, sanitiser, blog gate, opt-in and spam limits). `cd web && pnpm build && pnpm test:e2e` gives 46 passed, 1 skipped (the 390px test runs only in the mobile project), with the API unreachable on purpose.

**You need to:**
- **SMTP:** set `SMTP_*` and `OWNER_EMAIL`. Without them, emails are only logged, so double opt-in can't complete.
- **Optional:** `AMAZON_ASSOCIATES_TAG`, Turnstile keys, Umami.
- **Legal pages:** review Privacy, Terms and License. They are templates.
- **Local blog draft:** the Ocean book has one waiting for your approval in admin → Blog posts.

**Verified:**
- On the running stack, book 4 → kdp-uploaded → live triggered: public assets, the catalog entry, the book page, a blog draft (awaiting approval) and a free printable (3 pages).
- Home and book page checked by screenshot at 1280 px and 390 px.
- The public pages were built by a subagent and reviewed: content rules, an independent build and the Playwright run.

## Phase 6: AI generation ✅
**Built:**
- **LLM providers** behind one interface (`providers/llm/`):
  - **Claude:** official `anthropic` SDK. Structured JSON output, adaptive thinking with `effort`, streaming, and a server-side refusal fallback on Opus 5.5 / Sonnet 5.5.
  - **OpenAI:** Responses API with strict JSON schema.
  - **Gemini:** generateContent with a JSON schema.
  - **All three:** support image input for vision. Every answer is validated with Pydantic, with one repair retry. Refusals are charged but not retried.
- **Image providers** (`providers/image/`): OpenAI (`gpt-image-2.5-flare`, 1024x1536) and Gemini (`gemini-nano-banana-2.1`, 3:4), plus **manual** mode. Cost is computed from the usage each provider returns.
- **Budget guard everywhere:** every LLM, image and web-search call reserves → settles in `api_costs`, recording tokens, images and the model that actually answered. Prices are in `providers/pricing.py`, can be overridden in Settings (`model_prices`), and unknown models are priced high.
- **Agents:**
  - **Research:** 10 niches from a theme plus your pasted notes plus optional Brave or Tavily search, with Amazon and Etsy excluded. Saved as *proposed* niches; blocklisted ideas are dropped.
  - **Concept:** 60 scenes through the house prompt template, blocklist-filtered. Runs automatically when you create a book from a niche.
  - **Art:** one idempotent job per image, started only by the "Generate N images" button, after a budget check.
  - **Vision QA:** anatomy, scary faces, text, lookalikes, age and line art. Runs after the Python QA on the llm queue. A failed check never blocks the book.
- **Admin:**
  - **Costs page:** month vs cap, daily spend, by agent, by book, last 100 calls.
  - **Settings → AI providers & models:** per agent, with prices shown. A provider can't be chosen without its key.
  - **Book page → "Scene prompts & AI images":** write prompts, generate, copy prompts, upload a picture per prompt, retry failed ones.
  - **Niches:** a "Use web search" checkbox.
- `make demo` now also writes 60 offline scene prompts. It still makes 0 paid calls.
- **Docs:** `docs/API_KEYS.md` (new), decisions 43–52.

**Run/test:**
- `make test`: 97 Python tests. The new ones cover provider requests and responses with mocked HTTP, the strict schemas, cost maths, refusal and repair, the web-search exclusions, the research and concept agents, and the vision verdict merge.
- Web: lint, typecheck and build pass; Playwright 49 passed, 1 skipped. Logged-in admin smoke tests run when `E2E_ADMIN_EMAIL` and `E2E_ADMIN_PASSWORD` are set.

**You need to:**
1. **Choose keys:** add the AI keys you want (see `docs/API_KEYS.md`), restart, then pick models in admin → Settings → AI providers. Until then everything stays offline/manual and free.
2. **Spend limits:** set a monthly limit in each provider's billing console as well.
3. **QA threshold:** on the existing local database, lower `qa_thresholds.min_side_px` to 840 in Settings (new installs get it by default). Otherwise 1024-px API images fail QA.
4. **Local research test data:** 10 proposed "farm animals" niches are waiting in admin → Niches. Approve or reject them as you like.
5. **Model IDs:** the provider model IDs and prices were checked on 2026-11-08 and change often. Re-check them when you add a key.

**Not verified yet:**
- **Real paid calls:** none were made (no keys). They're covered by mocked tests only.
- **Concepts panel on a live book:** not exercised on the running stack, because that needs a book that has passed an approval gate. Only the API behind it was tested end to end.
- **Known limit:** if an image job uses up all its retries on a network error, the image stays "generating". Retry it from the Jobs page.

**Next (Phase 7):** Etsy sales sync, KDP CSV import, weekly Telegram + email report, nightly backups with 14-day retention plus restore, resource review, load check, and the README / DEPLOY_COOLIFY / WORKFLOW docs.
