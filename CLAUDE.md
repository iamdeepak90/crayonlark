# Crayonlark: rules for every session

Crayonlark is a one-person business: AI-assisted kids' coloring/activity books sold as KDP paperbacks
(uploaded **by hand**) and Etsy printable PDFs. The full original brief is in
`crayonlark-claude-code-prompt.md`; decisions are in `docs/DECISIONS.md`.

## Hard business rules (never break)
- **No KDP automation.** No scripting, scraping or browser automation of KDP/Amazon. We only build a
  "KDP upload pack" (zip) that the owner uploads manually.
- **No scraping Amazon or Etsy pages.** Official APIs only (Etsy Open API v3, Pinterest API v5) or data
  the owner pastes/uploads.
- **KDP limit: 2 paperbacks + 2 hardcovers per week**, week resets **Sunday 00:00 UTC**
  (`core/kdp_slots.py`). Never plan more.
- **AI disclosure is mandatory.** Every book/listing records which parts are AI-generated (interior
  images, cover image, text). Etsy uses "Designed by" the seller and states artwork was made with AI
  tools and edited by the seller. Never say "handmade" or "hand-drawn".
- **No famous characters, brands, logos or living artists' styles** (Disney, Pokémon, Bluey, Peppa Pig,
  Marvel, Crayola, …). Blocklist check on prompts/titles/tags/descriptions (`core/blocklist.py`) plus
  vision-QA on images.
- **Kids' content only**: friendly, age-appropriate, factually correct.
- **Human approval gates cannot be skipped by any agent**: niche, image set, cover, listing text, Etsy
  publish. Gate transitions only go through `core/approvals.py`, which requires a `HumanActor`.
- **Budget guard**: every paid API call goes through `core/budget.py` (monthly cap `MONTHLY_BUDGET_INR`,
  default ₹2,000; warn at 80 %, hard stop at 100 %).
- Secrets only in env vars. Commit `.env.example` only.

## Architecture (short)
- `python/` one package `crayonlark`, one image → services `api` (FastAPI), `worker` (Celery queues
  default/llm/images/publish), `worker-heavy` (cpu-heavy, concurrency 1), `scheduler` (beat), `bot`
  (Telegram long-polling), one-shot `migrate`.
- `web/` one Next.js 16 app for both hosts; `proxy.ts` routes `admin.*` to `/app/admin`. Only `web` has
  public domains; `/api/*` is rewritten to the internal API.
- Postgres 16, Redis 7, Garage (S3) for files. Code uses plain S3 via boto3 (`core/storage.py`).
- Providers: `providers/llm/*` and `providers/image/*` behind one interface each; `offline` LLM and
  `manual` image provider cost nothing and are used by tests and `make demo`.

## Conventions
- Keep code simple and readable; the owner maintains this alone.
- Every agent output is a Pydantic model; jobs are idempotent and retried with backoff.
- Python: ruff + mypy + pytest (`make check`). TS: eslint + tsc + Playwright.
- Next.js 16 changed APIs (e.g. `middleware` → `proxy`). Read `web/node_modules/next/dist/docs/`
  before writing Next code.
- New DB columns → `alembic revision --autogenerate` in `python/`, review, commit.
- Record non-obvious choices in `docs/DECISIONS.md`.
