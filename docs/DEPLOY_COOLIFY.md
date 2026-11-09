# Deploy on Coolify

Target: one VPS with 4 vCPU, 24 GB RAM and no GPU, running Coolify. The whole stack is one Docker Compose
resource. Only the `web` service gets domains; the API, Postgres, Redis and Garage stay on the
internal network.

## 1. DNS

Create these records at your DNS provider, pointing to the VPS IP:

| Name | Type | Value |
|---|---|---|
| `crayonlark.com` | A | VPS IP |
| `www.crayonlark.com` | A (or CNAME → crayonlark.com) | VPS IP |
| `admin.crayonlark.com` | A | VPS IP |

If you use Cloudflare, start with the proxy **off** (grey cloud) until Coolify has issued the
certificates. After that you can turn it on, with SSL mode "Full (strict)".

## 2. Create the resource

1. Coolify → Projects → New → **Docker Compose** → from your GitHub repo `crayonlark`, branch
   `main`, compose file `docker-compose.yml` (not the dev file).
2. **Domains:** set them on the `web` service only:
   `https://crayonlark.com:3000,https://www.crayonlark.com:3000,https://admin.crayonlark.com:3000`.
   The `:3000` tells Coolify's proxy which container port to use. It does not appear in the
   public URL. Leave every other service without a domain.
3. **Environment variables:** Coolify lists exactly **7**, and all of them are required:
   `SECRET_KEY`, `POSTGRES_PASSWORD`, `GARAGE_RPC_SECRET`, `GARAGE_ADMIN_TOKEN`, `S3_ACCESS_KEY`,
   `S3_SECRET_KEY`, `REVALIDATE_SECRET`. Make them with
   `sh scripts/gen-env.sh ~/crayonlark-prod.env` and paste the file into Coolify's
   *Developer view*. Paste values only: no quotes, no comments. If one is empty, the deploy
   stops and names it. Delete any other variable left over from older deploys.

   Everything optional (AI keys, Telegram, email, Etsy, Pinterest, off-site backup, Amazon tag,
   Turnstile, Umami) is **not** a variable. You switch it on after the first login in
   admin → Settings → Integrations, with no redeploy needed. The monthly budget is there too.

   Keep the 7 secrets in your password manager and never change them after the first deploy.
   The database and file storage are locked to them. Keys saved in Integrations are encrypted
   with `SECRET_KEY`.
4. **Deploy.** The `migrate` service runs once (Garage layout and buckets, then database
   migrations) and the other services wait for it. The first build takes about 10 minutes, mostly
   Chromium and the print toolchain.

## 3. First login

Coolify → the resource → **Terminal** → the `api` container:

```sh
crayonlark create-admin        # asks for email and password; then turn on 2FA in admin → Security
```

Open https://admin.crayonlark.com and log in. Check the dashboard: KDP slots, budget, and jobs
(the scheduler heartbeat appears within 5 minutes).

Optional starter content (same terminal; safe to run again):

```sh
crayonlark starter-content     # 10 blog DRAFTS, 12 PROPOSED niche ideas, the free sample printable
crayonlark demo-data           # 2 example books in the admin pipeline (never public)
crayonlark demo-data --remove  # delete the example books again
```

Nothing goes live by itself: publish the drafts in admin → Blog posts and approve or reject the
niche ideas in admin → Niche ideas.

## 4. Connect the outside services (optional, any time)

| Service | Steps |
|---|---|
| **Telegram** | @BotFather → `/newbot` → token. Paste it in Settings → Integrations → Telegram, switch on, save. Send your bot `/start`; it replies with your chat id. Add that, save. The bot picks it up within a minute. |
| **Email** | Any SMTP provider on port 587 (Brevo, Resend, SES, Zoho…). Settings → Integrations → Email. |
| **Etsy** | etsy.com/developers → create an app with callback `https://admin.crayonlark.com/api/oauth/etsy/callback`. Enter keystring, shared secret and shop id in Settings → Integrations → Etsy, then admin → Etsy → Connect. Find the taxonomy id with `crayonlark etsy-taxonomy --search coloring` (api terminal) and enter it in the same card. |
| **Pinterest** | developers.pinterest.com → app with callback `https://admin.crayonlark.com/api/oauth/pinterest/callback`. Enter both values in Settings → Integrations → Pinterest, then admin → Pinterest → Connect. |
| **AI providers** | Enter keys in Settings → Integrations → AI providers, then choose models per agent in Settings → AI providers & models. |
| **Analytics (optional)** | Deploy Umami as its own Coolify one-click service (for example `stats.crayonlark.com`), then enter its URL and website id in Settings → Integrations → Website extras. The site picks it up within 5 minutes. |

## 5. Backups and restore

- Every night at 03:00 IST, `worker-heavy` writes a database dump and mirrors every Garage bucket
  into the `backups` volume. Dumps and deleted files are kept for 14 days.
  The status is in admin → Settings → Backups. A failed backup sends a Telegram alert.
- **Off-site copy (recommended):** create a bucket at Backblaze B2, Cloudflare R2 or Wasabi and
  set `BACKUP_S3_ENDPOINT`, `BACKUP_S3_BUCKET`, `BACKUP_S3_ACCESS_KEY` and `BACKUP_S3_SECRET_KEY`
  (plus `BACKUP_S3_REGION` if the provider needs it). The same dumps and changed files are then
  uploaded there every night. Without this, a dead disk loses everything.
- **Run a backup now:** admin → Settings → Backups → Run backup now. Or, in the `worker-heavy`
  terminal: `crayonlark backup`.
- **Restore:**
  1. In Coolify, stop `api`, `worker`, `scheduler` and `bot`. Alternatively, SSH to the server
     and run `docker stop` on their containers.
  2. In the `worker-heavy` terminal:
     ```sh
     crayonlark backup-list                     # pick a day
     crayonlark restore --day 2026-11-08        # asks before replacing the database
     ```
  3. Start the stopped services again (or redeploy) and check the admin dashboard.

  The restore replaces the database with that night's dump and puts back every mirrored file
  that is missing or changed in Garage. If you work from an SSH shell in the compose directory,
  `scripts/restore.sh <day>` does all of these steps.
- **Practise once:** restore a recent day on a test server, or locally with `make up`, before you
  need it.

## 6. Resources

Memory limits add up to 13.5 GB of the 24 GB. That leaves room for the OS, Coolify, Umami and
file cache.

| Service | CPU | Memory |
|---|---|---|
| postgres | 1 | 2 GB (shared_buffers 512 MB) |
| redis | 0.5 | 512 MB |
| garage | 0.5 | 1 GB |
| api | 1 | 1 GB |
| web | 1 | 1 GB |
| worker | 1.5 | 3 GB |
| worker-heavy | 2 | 4 GB |
| scheduler | 0.25 | 512 MB |
| bot | 0.25 | 512 MB |

`worker-heavy` (PDFs, cleanup, mockups, backups) runs one job at a time and is capped at 2 CPUs,
so the website stays fast while a book is being built. CPU caps add up to more than 4 on
purpose: they are ceilings, not reservations.

**Load check:** from your laptop, `uv run --with httpx python scripts/loadcheck.py https://crayonlark.com 20 30`
(20 users for 30 seconds; run it at a quiet hour).
Locally this measured about 536 requests/s with 20 users, p95 103 ms and 0 errors. Pages are
cached (ISR) and refreshed every 5 minutes or on change.

## 7. Updating

Push to `main`, then press Redeploy in Coolify (or turn on auto-deploy). `migrate` runs first
on every deploy, so database migrations apply automatically. Volumes (`pgdata`, `garage-*`,
`backups`, `work`) survive redeploys. Never delete them in Coolify.
