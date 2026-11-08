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
