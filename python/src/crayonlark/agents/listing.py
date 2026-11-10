"""Listing agent: KDP title/subtitle/description/7 keywords/3 categories/age/price plus 3-5 Etsy
listings (full PDF, mini packs, bundle, activity pack) with 13 tags, description and price.

The LLM writes the creative text; code enforces the hard rules afterwards: price floors,
lengths, tag counts, safe HTML, AI-disclosure wording and the blocklist.
"""

from __future__ import annotations

import html
import re
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from crayonlark.core import blocklist, disclosure
from crayonlark.core.enums import ListingStatus
from crayonlark.core.models import Book, Listing
from crayonlark.providers.llm.base import AgentTask, run_task

MIN_KDP_PRICE = 9.99
KDP_BANNED = (
    "free",
    "bestseller",
    "best seller",
    "best-selling",
    "kindle unlimited",
    "amazon",
    "sale",
    "discount",
    "new release",
    "#1",
)
ALLOWED_TAGS = {"p", "br", "b", "strong", "i", "em", "ul", "ol", "li", "h4", "h5", "h6"}
DEFAULT_CATEGORIES = [
    "Children's Books > Activities, Crafts & Games > Coloring Books",
    "Children's Books > Activities, Crafts & Games > Activity Books",
    "Children's Books > Arts, Music & Photography > Drawing",
]
ETSY_PRICES = {"full_pdf": 4.99, "mini_pack": 2.99, "bundle": 6.49, "activity_pack": 3.49}


class KdpListingOut(BaseModel):
    title: str = Field(max_length=120)
    subtitle: str = Field(default="", max_length=120)
    description_html: str = Field(max_length=4000)
    keywords: list[str] = Field(min_length=7, max_length=7)
    categories: list[str] = Field(min_length=3, max_length=3)
    age_min: int = Field(ge=1, le=12)
    age_max: int = Field(ge=2, le=14)
    price_usd: float = Field(ge=MIN_KDP_PRICE)


class EtsyListingOut(BaseModel):
    product_kind: Literal["full_pdf", "mini_pack", "bundle", "activity_pack"]
    title: str = Field(max_length=140)
    tags: list[str] = Field(min_length=13, max_length=13)
    description: str = Field(max_length=6000)
    price_usd: float = Field(ge=0.5)


class ListingAgentOut(BaseModel):
    kdp: KdpListingOut
    etsy: list[EtsyListingOut] = Field(min_length=3, max_length=5)


SYSTEM = """You write product listings for Crayonlark, a small publisher of kids' coloring and
activity books. Write warm, clear, honest copy for parents and teachers. Rules:
- Never mention brands, famous characters, franchises or living artists.
- Never say "handmade" or "hand-drawn". Never claim awards, bestseller status, free, or discounts.
- KDP: title+subtitle ≤ 200 characters together; description in simple HTML (<p>, <b>, <ul>, <li>,
  <br>) under 4000 characters; exactly 7 keyword phrases (≤ 50 chars, what parents search for);
  exactly 3 category paths; price ≥ 9.99 USD.
- Etsy: titles ≤ 140 characters; exactly 13 tags, each ≤ 20 characters, lowercase; describe what
  is included, page count, Letter + A4 sizes, instant download, personal/single classroom use.
Return ONLY JSON matching the schema."""


def plan_etsy_products(n_designs: int, has_activities: bool) -> list[str]:
    kinds = ["full_pdf", "bundle"] if has_activities else ["full_pdf"]
    if has_activities:
        kinds.append("activity_pack")
    if n_designs >= 20:
        kinds += ["mini_pack", "mini_pack"]
    elif n_designs >= 10:
        kinds.append("mini_pack")
    while len(kinds) < 3:
        kinds.append("mini_pack")
    return kinds[:5]


# --------------------------------------------------------------------------- offline (free)


def _theme(book: Book) -> str:
    themes = [t for t in (book.themes or []) if t not in ("demo",)]
    return themes[0] if themes else re.sub(r"(?i)coloring book.*", "", book.title).strip() or "fun"


def _tags(theme: str, extra: list[str]) -> list[str]:
    base = [
        f"{theme} coloring",
        f"{theme} printable",
        "kids coloring pages",
        "printable coloring",
        "coloring pages pdf",
        "kids activity",
        "classroom activity",
        "homeschool printable",
        "toddler coloring",
        "preschool printable",
        "instant download",
        "quiet time activity",
        "rainy day activity",
        "birthday party",
        "kindergarten",
    ]
    out: list[str] = []
    for t in [*extra, *base]:
        t = t.lower()[:20].strip()
        if t and t not in out:
            out.append(t)
    return out[:13]


COLOR_REF_LINE = "- A small color example in the corner of every coloring page"


def _shows_color_refs(book: Book, kind: str) -> bool:
    """Etsy pages with drawings carry a colour example when the book has it on (never KDP)."""
    return bool(book.color_reference) and kind != "activity_pack"


def offline_listing(book: Book, n_designs: int, n_activities: int) -> ListingAgentOut:
    theme = _theme(book)
    ages = f"{book.age_min}-{book.age_max}"
    title = book.title[:120]
    subtitle = (
        book.subtitle
        or f"{n_designs} Simple {theme.title()} Pictures to Color for Kids Ages {ages}"
    )[:120]
    bullets = [
        f"{n_designs} one-sided coloring pages with thick, easy lines",
        "Each picture on its own page, so markers do not bleed through",
        "Large 8.5 x 11 inch pages" if book.trim == "8.5x11" else "Square 8.5 x 8.5 inch pages",
    ]
    if n_activities:
        bullets.append(f"{n_activities} bonus activities (mazes, puzzles and more) with answers")
    desc = (
        f"<p><b>{html.escape(title)}</b> is full of friendly {html.escape(theme)} pictures "
        f"made for little hands, ages {ages}.</p><ul>"
        + "".join(f"<li>{html.escape(b)}</li>" for b in bullets)
        + "</ul><p>A calm, screen-free activity for home, travel and classrooms.</p>"
    )
    kdp = KdpListingOut(
        title=title,
        subtitle=subtitle,
        description_html=desc,
        keywords=[
            f"{theme} coloring book for kids",
            f"{theme} coloring book ages {ages}",
            "coloring books for toddlers",
            "kids activity book",
            "simple coloring pages",
            "preschool coloring book",
            "gift for kids who love drawing",
        ],
        categories=DEFAULT_CATEGORIES,
        age_min=book.age_min,
        age_max=book.age_max,
        price_usd=MIN_KDP_PRICE,
    )
    names = {
        "full_pdf": f"{theme.title()} Coloring Pages for Kids, {n_designs} Printable Pages",
        "bundle": f"{theme.title()} Coloring and Activity Bundle, Printable PDF for Kids",
        "activity_pack": f"{theme.title()} Activity Pages: Mazes, Puzzles, Dot to Dot",
        "mini_pack": f"{theme.title()} Mini Coloring Pack, 10 Printable Pages for Kids",
    }
    etsy = []
    for kind in plan_etsy_products(n_designs, n_activities > 0):
        etsy.append(
            EtsyListingOut(
                product_kind=kind,
                title=f"{names[kind]}, Ages {ages}, Instant Download"[:140],
                tags=_tags(theme, [theme, f"{theme} for kids", f"{theme} pdf"]),
                description=(
                    f"{names[kind]}.\n\nWhat you get:\n- PDF in US Letter and A4 sizes\n"
                    "- Thick, simple lines that are easy to color\n"
                    + (COLOR_REF_LINE + "\n" if _shows_color_refs(book, kind) else "")
                    + "- Instant download, "
                    "print at home as often as you like\n\nLicense: personal and single "
                    "classroom use only. This is a digital item, nothing is shipped."
                ),
                price_usd=ETSY_PRICES[kind],
            )
        )
    return ListingAgentOut(kdp=kdp, etsy=etsy)


# --------------------------------------------------------------------------- enforcement


def safe_html(text: str) -> str:
    """Keep only KDP-allowed tags (no attributes); escape everything else."""
    out = []
    for part in re.split(r"(<[^<>]*>)", text):
        m = re.fullmatch(r"<(/?)([a-zA-Z][a-zA-Z0-9]*)\b[^<>]*>", part)
        if m:
            if m.group(2).lower() in ALLOWED_TAGS:
                out.append(f"<{m.group(1)}{m.group(2).lower()}>")
        else:
            out.append(html.escape(html.unescape(part), quote=False))
    return "".join(out)


def enforce(out: ListingAgentOut, book: Book) -> ListingAgentOut:
    k = out.kdp
    k.price_usd = max(MIN_KDP_PRICE, round(k.price_usd, 2))
    k.description_html = safe_html(k.description_html)[:4000]
    if len(k.title) + len(k.subtitle) > 200:
        k.subtitle = k.subtitle[: max(0, 200 - len(k.title))].rstrip()
    k.keywords = [
        kw.strip()[:50] for kw in k.keywords if not any(b in kw.lower() for b in KDP_BANNED)
    ][:7]
    while len(k.keywords) < 7:
        k.keywords.append(f"{_theme(book)} coloring pages")
    for e in out.etsy:
        e.tags = [t.lower().strip()[:20] for t in e.tags]
        e.price_usd = round(max(0.5, e.price_usd), 2)
    return out


def blocklist_hits(lst: Listing, extra: list[str]) -> dict[str, list[str]]:
    return blocklist.check_many(
        {
            "title": lst.title,
            "subtitle": lst.subtitle,
            "description": lst.description,
            "keywords": list(lst.keywords or []),
            "tags": list(lst.tags or []),
            "categories": list(lst.categories or []),
        },
        extra,
    )


# --------------------------------------------------------------------------- run


def run(session: Session, book: Book) -> list[Listing]:
    from crayonlark.core import pipeline
    from crayonlark.print.activities import build_activities

    designs = pipeline.approved_images(book)
    n_acts = len(build_activities(book.activity_plan or {}, seed=book.id))
    prompt = (
        f"Book: {book.title}\nSubtitle idea: {book.subtitle}\nSeries: {book.series} "
        f"vol {book.volume}\nThemes: {', '.join(book.themes or [])}\nAges {book.age_min}-"
        f"{book.age_max}\nTrim {book.trim}, {book.page_count} pages, {len(designs)} coloring "
        f"pages, {n_acts} activity pages.\nScenes: "
        + "; ".join(i.scene_title for i in designs[:40])
        + f"\nEtsy products to write (in this order): "
        f"{', '.join(plan_etsy_products(len(designs), n_acts > 0))}."
        + (
            "\nThe Etsy printable coloring pages have a small color example in the corner of "
            "each page: mention it in the Etsy descriptions (not for the activity pack). The KDP "
            "paperback is black and white: do not mention color examples in the KDP listing."
            if book.color_reference
            else ""
        )
    )
    task = AgentTask(
        agent="listing",
        system=SYSTEM,
        prompt=prompt,
        schema=ListingAgentOut,
        offline=lambda: offline_listing(book, len(designs), n_acts),
        max_tokens=4000,
        book_id=book.id,
    )
    out = enforce(run_task(task), book)
    return save(session, book, out, [i.id for i in designs])


def save(session: Session, book: Book, out: ListingAgentOut, image_ids: list[int]) -> list[Listing]:
    """Replace this book's draft listings (keeps Etsy rows that already exist on Etsy)."""
    session.execute(
        delete(Listing).where(
            Listing.book_id == book.id,
            Listing.status != ListingStatus.APPROVED,
            ~Listing.etsy.has(),
        )
    )
    k = out.kdp
    rows = [
        Listing(
            book_id=book.id,
            platform="kdp",
            product_kind=book.format,
            title=k.title,
            subtitle=k.subtitle,
            description=k.description_html,
            keywords=k.keywords,
            categories=k.categories,
            age_min=k.age_min,
            age_max=k.age_max,
            price_cents=round(k.price_usd * 100),
            ai_disclosure=disclosure.kdp_markdown(book),
            status=ListingStatus.AWAITING_APPROVAL,
        )
    ]
    mini = 0
    for e in out.etsy:
        selection = image_ids
        if e.product_kind == "mini_pack":
            selection = image_ids[mini * 10 : mini * 10 + 10] or image_ids[:10]
            mini += 1
        elif e.product_kind == "activity_pack":
            selection = []
        rows.append(
            Listing(
                book_id=book.id,
                platform="etsy",
                product_kind=e.product_kind,
                title=e.title,
                description=e.description.rstrip() + "\n\n" + disclosure.etsy_text(book),
                tags=e.tags,
                price_cents=round(e.price_usd * 100),
                age_min=book.age_min,
                age_max=book.age_max,
                ai_disclosure=disclosure.etsy_text(book),
                page_selection=selection,
                status=ListingStatus.AWAITING_APPROVAL,
            )
        )
    session.add_all(rows)
    session.flush()
    return list(session.scalars(select(Listing).where(Listing.book_id == book.id)))
