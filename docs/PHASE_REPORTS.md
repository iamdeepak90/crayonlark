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
