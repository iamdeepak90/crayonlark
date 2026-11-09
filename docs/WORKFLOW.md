# Day-to-day workflow

Crayonlark does the repetitive work. You make every decision. Each gate below waits for you, and
no agent can pass it on your behalf. Telegram pings you when something is waiting, and you can
approve image sets from the album the bot sends.

## Making one book (about 1–2 hours of your time, spread over a few days)

| Step | Where | What you do |
|---|---|---|
| 1. Ideas | admin → Niches → *Research* | Enter a theme (for example "farm animals"), paste any notes, and optionally tick "Use web search". You get 10 **proposed** niches. Or add a niche by hand. |
| 2. **Gate: niche** | admin → Niches | Approve one niche and reject the rest. Check that it is kid-friendly and has no famous characters or brands. |
| 3. Book | admin → Books → *New book* from the niche | Pick the trim size and page count. The concept agent writes 60 scene prompts. |
| 4. Pictures | Book page → *Scene prompts & AI images* | **Paid:** *Generate N images* (it checks the budget first). **Free:** copy each prompt into the ChatGPT or Gemini app and upload the result. Python QA and (if enabled) vision QA run on every picture. |
| 5. **Gate: image set** | admin → Books → Images, or the Telegram album | Look at each image at 100%. Keys: `a` approve, `r` reject, `z` zoom, arrows to move. Reject anything odd (hands, faces, stray text, look-alikes). Then approve the set. |
| 6. Build | automatic | Cleanup (potrace, 300 DPI), activities with answer keys, interior PDF, validation. |
| 7. **Gate: cover** | Book page → Cover | Check the full wrap, the thumbnail and the phone preview. Approve or regenerate. |
| 8. **Gate: listing text** | Book page → Listings | Edit and approve the KDP and Etsy text. The AI disclosure is filled in already, so leave it. Never write "handmade" or "hand-drawn". |
| 9. KDP pack | admin → Packs | Download the zip. It holds `interior.pdf`, `cover.pdf`, `listing.md` (in KDP's field order), `ai-disclosure.md` and `upload-checklist.md`. The pack takes one of this week's slots (2 paperback + 2 hardcover, reset Sunday 00:00 UTC). |
| 10. Upload to KDP | kdp.amazon.com, **by hand** | Follow `upload-checklist.md`. Answer KDP's AI questions from `ai-disclosure.md`. Order a proof copy. |
| 11. Proof and live | Book page → KDP steps | Mark *uploaded*, then *proof ordered*. When the book is live, enter the ASIN and Amazon link and mark it *live*. That publishes the book page on crayonlark.com and drafts a blog post. |
| 12. **Gate: blog post** | admin → Blog | Edit and approve the post. |
| 13. **Gate: Etsy publish** | admin → Etsy | Drafts (Letter + A4 PDFs, mockups, tags) are created through the Etsy API. Check them, then *Publish*. Pins are then scheduled automatically, 3–5 per day. |

## Daily (5–10 minutes)
- Read Telegram: things waiting for you, failed jobs, budget warnings (80%), backup failures.
- admin → Dashboard: pipeline board, KDP slots left this week, budget.
- admin → Messages: answer contact-form messages.
- admin → Jobs: retry anything failed. An image stuck on "generating" also gets retried here.

## Weekly
- **Monday 09:00 IST:** the weekly report arrives on Telegram and by email. It covers sales,
  AI spend, what's waiting for you, slots, pins, new subscribers and the last backup.
- **KDP sales:** in KDP Reports, download the royalties report as **CSV** (not xlsx) and upload it in
  admin → Sales. Re-uploading the same file adds nothing twice.
- **Etsy sales** sync on their own every 6 hours once Etsy is connected (or press *Sync now*).
- **Plan the week's KDP uploads** around the slot counter. It never lets you go over 2 + 2.

## Monthly
- admin → Costs: spend by agent and book. Adjust `MONTHLY_BUDGET_INR` or the models in
  Settings → AI providers if needed. Also set a limit in each provider's own billing console.
- admin → Subscribers: export the CSV if you send a newsletter.
- Check that backups are listed (Settings → Backups). Every few months, practise a restore
  (see `DEPLOY_COOLIFY.md`).
- Re-check model prices when providers announce changes (Settings → `model_prices`).

## Rules to keep in mind
- No famous characters, brands, logos or living artists' styles. The blocklist catches names, but
  you catch look-alikes.
- Kids' content only: friendly, age-appropriate, correct facts.
- Don't automate KDP and don't copy data off Amazon or Etsy pages. Upload by hand and paste or
  upload your own reports.
