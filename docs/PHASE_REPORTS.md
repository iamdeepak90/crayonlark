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
