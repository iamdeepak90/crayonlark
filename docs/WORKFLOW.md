# Day-to-day workflow

Crayonlark does the repetitive work. You make **two decisions per book**: *Approve for Etsy*
and *Pick for KDP*. Neither can be passed by any agent or by the Autopilot. Telegram pings you
when something is waiting.

## How a book moves (Etsy first, KDP second)

| Step | Who | What happens |
|---|---|---|
| 1. Niche idea | Autopilot (or you, admin → Niche ideas) | With the **Autopilot** on (switch on the Today page), it approves the oldest proposed niche whenever fewer than *keep* books are in progress (max 2 new a day). When the ideas run out, it researches the least-used theme from its list (once a day). Ideas are blocklist-checked. |
| 2. Scene prompts | automatic | The concept agent writes 40 scene prompts. |
| 3. Pictures | Autopilot (paid) | It generates the minimum + 30 % (not all 60) and checks the budget first. Pixel QA and the AI vision check run on every picture. With the image provider on *manual*, upload the pictures yourself. |
| 4. Image set | Autopilot | It keeps the pictures that passed **both** checks (best first, up to the maximum) and rejects the rest. If too few passed, it generates more. With the Autopilot off, you approve them (admin → book → Images, or the Telegram album). |
| 5. Build | automatic | Cleanup (potrace, 300 DPI), colour examples if switched on, interior PDF, KDP cover, listing text, Etsy Letter + A4 PDFs, listing photos. |
| 6. **Approval 1: Etsy** | **you**, admin → *1. Approve for Etsy* | You see the photos, every page, the PDFs, title, price, tags and description. *Approve for Etsy* adds the book to the queue. You can also *Edit text* or *Send back*. |
| 7. Etsy queue | automatic | One book a day goes live on Etsy (from 14:00 UTC by default; change it on the same screen). Pins follow automatically. Keep about a week of books in the queue. |
| 8. Etsy results | automatic | Views and favourites sync every morning, sales every 6 hours. |
| 9. **Approval 2: KDP** | **you**, admin → *2. Pick for KDP* | Books on Etsy are ranked by score (sales × 20 + favourites × 3 + views × 0.2, per week live). Approve only the best: it approves the cover and KDP text and takes the next free weekly slot (2 paperbacks a week, about 8–9 a month). A new book with no Etsy data yet can be approved too. *Not for KDP* hides a book (it stays on Etsy). |
| 10. Upload to KDP | **you**, kdp.amazon.com, by hand | admin → KDP uploads: download the pack and follow `upload-checklist.md`. Mark *uploaded*, *proof ordered*, then *live* with the ASIN. That publishes the book page on crayonlark.com and drafts a blog post. |

If a book seems stuck between automatic steps, open it and press **Continue**.

## Daily (5–10 minutes)
- Read Telegram: things waiting for you, failed jobs, budget warnings (80%), backup failures.
- admin → Today: what is waiting, Etsy queue stock, KDP slots, Autopilot problems, budget.
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
- admin → Costs: spend by agent and book. Adjust the cap in Settings → Monthly API budget, or the models in
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
