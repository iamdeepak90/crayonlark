# API keys

Everything is optional. With no keys at all, Crayonlark runs in **offline/manual mode**:
- template text from the offline agents;
- pictures you make yourself in the ChatGPT or Gemini apps and upload;
- KDP packs you upload by hand.

Keys are entered in **admin → Settings → Keys and connections** (not in Coolify). They are stored
encrypted, never shown again, and reach the workers within a minute, so there's no redeploy.
**You only need two AI keys:** OpenRouter (every text agent and the vision check, with Claude
Haiku 5.5, and Sonnet 5.5 for the listing text) and DeepInfra (pictures with FLUX.1 schnell).
The models are fixed in code and switch on as soon as the key is saved. (A non-empty env var
with the same name still wins, which is handy for local testing.)

ChatGPT Plus, Gemini Pro and Claude Pro subscriptions do **not** include API access. API keys are
billed separately, by usage.

## AI providers (Phase 6)

| Key (Settings → Keys and connections) | Where to get it | Used for |
|---|---|---|
| `ANTHROPIC_API_KEY` | console.anthropic.com → API keys | any text agent; vision QA |
| `OPENAI_API_KEY` | platform.openai.com → API keys | text agents, vision QA, image generation |
| `GEMINI_API_KEY` | aistudio.google.com → Get API key | text agents, vision QA, image generation |
| `OPENROUTER_API_KEY` | openrouter.ai → Keys (buy credits first) | any of the above through one key: Claude, GPT, Gemini and many more |
| `DEEPINFRA_API_KEY` | deepinfra.com → Dashboard → API keys (add credit) | the cheapest pictures: FLUX.1 schnell (Apache 2.0), about $0.003 (₹0.26) each |
| `LANGSEARCH_API_KEY` | langsearch.com/api-keys (free) | optional web search for the research agent |
| `TINYFISH_API_KEY` | agent.tinyfish.ai/api-keys (free) | optional web search for the research agent; with both keys, results are merged |

**Other AI keys** (Anthropic, OpenAI, Gemini) are not needed any more; they stay as optional
fields in case the code is switched to them later.

**Spend limits:** set a monthly limit in each provider's billing console as well. Crayonlark's
own guard (admin → Settings → Monthly API budget, default ₹2,000) stops paid calls at 100 %, but a limit at the
provider is a second safety net.

**Rough costs** (prices checked 2026-11-08; see `python/src/crayonlark/providers/pricing.py`):
- **Concepts (40 scene prompts):** about 10k output tokens. That's about $0.20 with
  `claude-opus-5-5`, or under $0.01 with `claude-haiku-5-5` or `gpt-6-luna`.
- **Vision QA:** about 2–3k tokens per image, so roughly $0.05 for 50 images on Opus 5.5, and
  less than a cent on Haiku 5.5.
- **Images:** DeepInfra FLUX.1 schnell is about $0.003 per 1024×1536 picture (4 steps), so
  ₹8–10 for a book (~33 pictures). The others cost $0.03–0.07 per picture (₹100–175 a book).
- **Per-book cap:** admin → Settings → Monthly API budget, "Most per book" (default ₹50).
  Paid calls for a book stop once it has cost that much.
- **Web search:** free. LangSearch has a free plan with a daily allowance. TinyFish search is
  free up to 30/min, 500/hour and 12,000/day. Each research run makes 2 searches.

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
