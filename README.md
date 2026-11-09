# Crayonlark

AI-assisted kids' coloring and activity books, made by one person:
- **KDP paperbacks.** Crayonlark builds an upload pack; you upload it to KDP **by hand**.
- **Etsy printable PDFs.** Drafts are created through the official API and published only after you approve them.
- **crayonlark.com and admin.crayonlark.com.** The public website, plus the admin where every decision is made.

The hard rules (no KDP automation, no scraping, AI disclosure, no famous characters, human
approval gates, monthly budget cap) are in [`CLAUDE.md`](CLAUDE.md).

## How it fits together

```
idea → niche approved → concepts → images → QA → (you approve images) → cleanup → interior PDF
     → cover → (you approve) → listings → (you approve) → KDP upload pack → you upload to KDP
     → proof → live → website + blog draft → (you approve)        Etsy: drafts → (you approve) → published
```

| Folder | What |
|---|---|
| `python/` | One Python package (`crayonlark`) and one image. It runs as `api` (FastAPI), `worker` (Celery: default/llm/images/publish), `worker-heavy` (PDFs, cleanup, backups), `scheduler` (beat), `bot` (Telegram) and the one-shot `migrate`. |
| `web/` | One Next.js 16 app for both the public site and the admin (`proxy.ts` routes `admin.*`). |
| `docs/` | [Deploy on Coolify](docs/DEPLOY_COOLIFY.md) · [Daily workflow](docs/WORKFLOW.md) · [API keys](docs/API_KEYS.md) · [Decisions](docs/DECISIONS.md) · [Public API](docs/PUBLIC_API.md) · [Phase reports](docs/PHASE_REPORTS.md) |
| `scripts/` | `gen-env.sh`, `backup.sh`, `restore.sh`, `loadcheck.py` |

Services: Postgres 16, Redis 7 and Garage (S3) for files. Only `web` is public; everything else
stays on the internal Docker network.

## Run it locally

Needs Docker (give Docker Desktop at least 8 GB of memory), plus Node 22 and pnpm for web development.

```sh
make up        # creates .env with random secrets, builds and starts everything
make admin     # create your admin login
make demo      # the whole pipeline on 5 sample images: KDP pack + Etsy PDFs, zero paid calls
```

- Public site: http://localhost:3000
- Admin: http://admin.localhost:3000 (`*.localhost` resolves to your machine in most browsers)
- Demo files: `./demo-output/`

Other commands: `make test`, `make check` (ruff, mypy, pytest, eslint, tsc), `make logs`,
`make psql`, `make shell`, `make down`. Web: `cd web && pnpm dev` and `pnpm test:e2e`.

## No keys needed to start

With no API keys, every agent runs **offline** (free template text) and images are
**manual**: you make pictures in the ChatGPT or Gemini apps from the prompts shown in admin, then upload them.
Add keys later and pick models in admin → Settings → AI providers (see `docs/API_KEYS.md`). Every
paid call goes through the budget guard (`MONTHLY_BUDGET_INR`, default ₹2,000).

## Maintenance

- **Backups:** every night at 03:00 IST, kept 14 days. To restore, run `scripts/restore.sh` (see the deploy doc).
- **Weekly report:** Telegram and email, Monday 09:00 IST.
- **New database columns:** `cd python && uv run alembic revision --autogenerate -m "..."`. Review the file, then commit it.
