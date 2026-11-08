# API keys

Everything is optional. With no keys at all, Crayonlark runs in **offline/manual mode**:
- template text from the offline agents;
- pictures you make yourself in the ChatGPT or Gemini apps and upload;
- KDP packs you upload by hand.

Keys go in environment variables only (Coolify → the app → Environment Variables, or `.env`
locally). Never commit them. After adding a key, redeploy or restart, then choose providers and
models in **admin → Settings → AI providers**. A key alone switches nothing on.

ChatGPT Plus, Gemini Pro and Claude Pro subscriptions do **not** include API access. API keys are
billed separately, by usage.

## AI providers (Phase 6)

| Variable | Where to get it | Used for |
|---|---|---|
| `ANTHROPIC_API_KEY` | console.anthropic.com → API keys | any text agent; vision QA |
| `OPENAI_API_KEY` | platform.openai.com → API keys | text agents, vision QA, image generation |
| `GEMINI_API_KEY` | aistudio.google.com → Get API key | text agents, vision QA, image generation |
| `WEBSEARCH_PROVIDER` + `WEBSEARCH_API_KEY` | brave.com/search/api or tavily.com | optional search for the research agent |

**Spend limits:** set a monthly limit in each provider's billing console as well. Crayonlark's
own guard (`MONTHLY_BUDGET_INR`, default ₹2,000) stops paid calls at 100 %, but a limit at the
provider is a second safety net.

**Rough costs** (prices checked 2026-11-08; see `python/src/crayonlark/providers/pricing.py`):
- **Concepts (60 scene prompts):** about 15k output tokens. That's about $0.30 with
  `claude-opus-5-5`, or under $0.01 with `claude-haiku-5-5` or `gpt-6-luna`.
- **Vision QA:** about 2–3k tokens per image, so roughly $0.05 for 50 images on Opus 5.5, and
  less than a cent on Haiku 5.5.
- **Images:** about $0.03–0.07 per portrait image (`gemini-nano-banana-2.1` is the cheapest),
  so ₹150–300 for a 50-image book.
- **Web search:** $0.005 (Brave) or $0.008 (Tavily) per search, with 2 searches per research run.

Suggested start: research, concept and listing on `claude-opus-5-5`, vision QA on
`claude-haiku-5-5`, images in manual mode until the prompts look right.

## Other keys

| Variable(s) | Purpose | Notes |
|---|---|---|
| `ETSY_API_KEY`, `ETSY_SHARED_SECRET`, `ETSY_SHOP_ID`, `ETSY_TAXONOMY_ID` | Etsy drafts, publish, sales | etsy.com/developers. Callback: `https://admin.<domain>/api/oauth/etsy/callback` |
| `PINTEREST_APP_ID`, `PINTEREST_APP_SECRET` | scheduled pins | developers.pinterest.com. Callback: `https://admin.<domain>/api/oauth/pinterest/callback` |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ADMIN_CHAT_ID` | approvals and alerts on your phone | create the bot with @BotFather. Only your chat id is accepted |
| `SMTP_*`, `OWNER_EMAIL` | free-printable opt-in, contact form, reports | any SMTP provider |
| `AMAZON_ASSOCIATES_TAG` | affiliate tag on Amazon links | optional |
| `NEXT_PUBLIC_TURNSTILE_SITE_KEY` / `TURNSTILE_SECRET` | contact-form captcha | optional |
