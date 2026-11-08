"""Listing agent: offline output, rule enforcement, safe HTML, disclosure and the pack zip."""

from __future__ import annotations

import io
import zipfile
from datetime import date

from crayonlark.agents import listing
from crayonlark.core import disclosure
from crayonlark.core.models import Book, Listing
from crayonlark.print import kdp_pack


def _book(**kw: object) -> Book:
    fields: dict[str, object] = dict(
        id=1,
        title="Ocean Friends Coloring Book",
        slug="ocean",
        subtitle="",
        series="Ocean",
        volume=1,
        themes=["ocean animals"],
        age_min=3,
        age_max=6,
        trim="8.5x11",
        format="paperback",
        paper="white",
        page_count=60,
        ai_interior_images=True,
        ai_cover_image=False,
        ai_text=True,
        ai_tools="",
        activity_plan={},
    )
    fields.update(kw)
    return Book(**fields)


def test_offline_listing_follows_the_rules() -> None:
    out = listing.offline_listing(_book(), n_designs=30, n_activities=4)
    assert len(out.kdp.keywords) == 7 and len(out.kdp.categories) == 3
    assert out.kdp.price_usd >= listing.MIN_KDP_PRICE
    assert 3 <= len(out.etsy) <= 5
    kinds = [e.product_kind for e in out.etsy]
    assert kinds[0] == "full_pdf" and "bundle" in kinds and "activity_pack" in kinds
    for e in out.etsy:
        assert len(e.tags) == 13 and all(len(t) <= 20 and t == t.lower() for t in e.tags)
        assert len(e.title) <= 140
    text = (out.kdp.description_html + " ".join(e.description for e in out.etsy)).lower()
    assert "handmade" not in text and "hand-drawn" not in text


def test_plan_without_activities_still_has_three_products() -> None:
    assert listing.plan_etsy_products(8, False) == ["full_pdf", "mini_pack", "mini_pack"]


def test_enforce_price_keywords_and_html() -> None:
    out = listing.offline_listing(_book(), 30, 0)
    out.kdp.price_usd = 9.99
    out.kdp.keywords[0] = "bestseller free coloring book"
    out.kdp.description_html = '<p onclick="x()">Hi</p><script>alert(1)</script><b>ok</b>'
    out = listing.enforce(out, _book())
    assert all("free" not in k for k in out.kdp.keywords) and len(out.kdp.keywords) == 7
    assert out.kdp.description_html == "<p>Hi</p>alert(1)<b>ok</b>"


def test_safe_html_escapes_text() -> None:
    assert listing.safe_html("a < b & <i>c</i>") == "a &lt; b &amp; <i>c</i>"


def test_blocklist_hits_on_listing() -> None:
    lst = Listing(
        platform="etsy",
        title="Cute Bluey coloring pages",
        subtitle="",
        description="",
        keywords=[],
        tags=["peppa pig fun"],
        categories=[],
    )
    hits = listing.blocklist_hits(lst, [])
    assert "title" in hits and "tags" in hits


def test_disclosure_wording() -> None:
    ai = _book()
    assert "Designed by Crayonlark" in disclosure.etsy_text(ai)
    assert "AI tools" in disclosure.etsy_text(ai)
    plain = _book(ai_interior_images=False, ai_text=False)
    assert disclosure.etsy_text(plain) == "Designed by Crayonlark."
    md = disclosure.kdp_markdown(ai, cover_ai=True)
    assert "AI-generated content?** Yes" in md and "cover image" in md
    assert "AI-generated content?** No" in disclosure.kdp_markdown(plain)


def test_pack_zip_contents() -> None:
    book = _book()
    out = listing.offline_listing(book, 30, 2)
    k = out.kdp
    kdp = Listing(
        platform="kdp",
        title=k.title,
        subtitle=k.subtitle,
        description=k.description_html,
        keywords=k.keywords,
        categories=k.categories,
        age_min=3,
        age_max=6,
        price_cents=999,
    )
    data = kdp_pack.build_zip(
        book,
        kdp,
        interior_pdf=b"%PDF-int",
        cover_pdf=b"%PDF-cov",
        ai_disclosure_md=disclosure.kdp_markdown(book),
        week_start=date(2026, 11, 8),
        thumb_jpg=b"jpg",
    )
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = set(z.namelist())
        md = z.read("listing.md").decode()
        assert z.read("interior.pdf") == b"%PDF-int"
        assert "2026-11-08" in z.read("week-slot.txt").decode()
    assert {
        "interior.pdf",
        "cover.pdf",
        "listing.md",
        "ai-disclosure.md",
        "upload-checklist.md",
        "week-slot.txt",
        "cover-thumbnail.jpg",
    } <= names
    # KDP field order: title before description before keywords before categories? (KDP order)
    assert md.index("Book Title") < md.index("Description") < md.index("Keywords")
    assert "9.99" in md
