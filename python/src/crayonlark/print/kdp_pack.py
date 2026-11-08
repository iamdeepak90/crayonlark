"""KDP upload pack: a zip I upload to KDP by hand (no KDP automation, ever).

Contents: interior.pdf, cover.pdf, listing.md (copy-paste fields in KDP's order),
ai-disclosure.md, upload-checklist.md (includes the week slot), cover-thumbnail.jpg.
"""

from __future__ import annotations

import io
import re
import zipfile
from datetime import date, timedelta

from crayonlark.core.models import Book, Listing


def _html_to_md_preview(desc: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", re.sub(r"<[^>]+>", "\n", desc)).strip()


def listing_md(book: Book, kdp: Listing) -> str:
    paper = {
        "white": "Black & white interior with white paper",
        "cream": "Black & white interior with cream paper",
        "color": "Premium color interior with white paper",
    }[book.paper]
    trim = {"8.5x11": "8.5 x 11 in", "8.5x8.5": "8.5 x 8.5 in"}.get(book.trim, book.trim)
    kw = "\n".join(f"{i}. {k}" for i, k in enumerate(kdp.keywords or [], start=1))
    cats = "\n".join(f"{i}. {c}" for i, c in enumerate(kdp.categories or [], start=1))
    return f"""# KDP listing: {book.title}

Copy each field into KDP in this order. (Paperback → *Create paperback*.)

## 1. Paperback Details

**Language:** English

**Book Title:**
```
{kdp.title}
```

**Subtitle:**
```
{kdp.subtitle}
```

**Series:** {book.series or "(none)"}{f"  ·  Series number: {book.volume}" if book.series else ""}

**Edition number:** (leave empty)

**Author:** First name: *(empty)*  ·  Last name: `Crayonlark`

**Description** (paste into KDP's description box as HTML via *Source*/plain editor):
```html
{kdp.description}
```
Preview:

{_html_to_md_preview(kdp.description)}

**Publishing rights:** I own the copyright and I hold the necessary publishing rights.

**Primary audience:** Sexually explicit images or title → **No**.
Reading age: **{kdp.age_min or book.age_min}** to **{kdp.age_max or book.age_max}** years.

**Primary marketplace:** Amazon.com

**Categories** (choose the closest matches in KDP's category picker):
{cats}

**Keywords** (one per box):
{kw}

## 2. Paperback Content

- **Print ISBN:** Get a free KDP ISBN
- **Publication date:** leave empty (uses the publish date)
- **Ink and paper type:** {paper}
- **Trim size:** {trim}
- **Bleed settings:** No Bleed
- **Paperback cover finish:** Matte
- **Manuscript:** upload `interior.pdf` ({book.page_count} pages)
- **Book cover:** *Upload a cover you already have* → `cover.pdf`
- **AI-generated content:** see `ai-disclosure.md`
- **Book preview:** launch the previewer and check every page

## 3. Paperback Rights & Pricing

- **Territories:** All territories (worldwide rights)
- **Primary marketplace:** Amazon.com
- **List price (USD):** ${kdp.price_cents / 100:.2f}
- Let KDP calculate the other marketplaces.
- Expanded distribution: optional (lower royalty)
"""


def checklist_md(book: Book, week_start: date) -> str:
    week_end = week_start + timedelta(days=6)
    return f"""# Upload checklist: {book.title}

**KDP week slot:** Sunday {week_start.isoformat()} → Saturday {week_end.isoformat()} (UTC).
Only upload this book inside that week. Crayonlark plans at most 2 paperbacks + 2 hardcovers per
week (KDP's new-title limit).

- [ ] Open KDP → Bookshelf → *+ Create* → Paperback
- [ ] Paste every field from `listing.md` (in order)
- [ ] Answer the AI questions exactly as in `ai-disclosure.md`
- [ ] Upload `interior.pdf`, choose *No Bleed*, {book.trim} trim, white paper
- [ ] Upload `cover.pdf` (*Upload a cover you already have*)
- [ ] Launch Previewer: no errors, nothing cut off, barcode area empty
- [ ] Set price (never below $9.99) and publish
- [ ] Order an author proof copy
- [ ] In Crayonlark admin: mark the book as **uploaded**, then **proof ordered**, then **live**
      with the ASIN and Amazon link
"""


def build_zip(
    book: Book,
    kdp: Listing,
    interior_pdf: bytes,
    cover_pdf: bytes,
    ai_disclosure_md: str,
    week_start: date,
    thumb_jpg: bytes | None = None,
) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("interior.pdf", interior_pdf)
        z.writestr("cover.pdf", cover_pdf)
        z.writestr("listing.md", listing_md(book, kdp))
        z.writestr("ai-disclosure.md", ai_disclosure_md)
        z.writestr("upload-checklist.md", checklist_md(book, week_start))
        z.writestr("week-slot.txt", f"{week_start.isoformat()}\n")
        if thumb_jpg:
            z.writestr("cover-thumbnail.jpg", thumb_jpg)
    return buf.getvalue()
