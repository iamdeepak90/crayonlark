"""Colour references: a coloured example in the corner of Etsy pages (never KDP)."""

from __future__ import annotations

import base64
import io
import json
from pathlib import Path

import numpy as np
import pytest
import respx
from PIL import Image as PILImage

from crayonlark.print import colorize


def _png(img: PILImage.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _painted(line_art: bytes, rgb: tuple[int, int, int] = (90, 190, 90)) -> bytes:
    """What an AI colouring might return: same picture, one colour everywhere but the lines,
    at a different size."""
    gray = PILImage.open(io.BytesIO(line_art)).convert("L").resize((1024, 1365))
    out = np.full((gray.height, gray.width, 3), rgb, dtype=np.uint8)
    out[np.asarray(gray) < 128] = (0, 0, 0)
    return _png(PILImage.fromarray(out, "RGB"))


# --------------------------------------------------------------------------- pure helpers


def test_keep_lines_puts_the_original_lines_back(line_art: bytes) -> None:
    # the "AI" version has no lines at all: the merge must still show the original ones
    plain = _png(PILImage.new("RGB", (1024, 1365), (240, 120, 90)))
    merged = PILImage.open(io.BytesIO(colorize.keep_lines(line_art, plain, max_h=800)))
    line = PILImage.open(io.BytesIO(colorize.scaled_png(line_art, 800))).convert("L")
    assert merged.size == line.size
    dark = np.asarray(line) < 60
    px = np.asarray(merged.convert("RGB")).astype(int)
    assert px[dark].max() < 80  # lines stay dark
    assert colorize.colourfulness(_png(merged)) > 0.5  # the rest is coloured


def test_colourfulness_tells_colour_from_black_and_white(line_art: bytes) -> None:
    assert colorize.colourfulness(line_art) == 0.0
    assert colorize.colourfulness(colorize.colorize(colorize.scaled_png(line_art, 800))) > 0.05


def test_print_jpeg_is_small(line_art: bytes) -> None:
    jpg = colorize.print_jpeg(colorize.colorize(line_art), max_h=600)
    assert PILImage.open(io.BytesIO(jpg)).height == 600 and len(jpg) < 200_000


# --------------------------------------------------------------------------- provider requests


def test_edit_requests_send_the_line_art(keys) -> None:  # type: ignore[no-untyped-def]
    from crayonlark.providers.image.gemini_image import GeminiImageProvider
    from crayonlark.providers.image.openai_image import OpenAIImageProvider
    from crayonlark.providers.image.openrouter_image import OpenRouterImageProvider

    png = b"\x89PNG-test"
    url = "data:image/png;base64," + base64.b64encode(png).decode()
    o = OpenAIImageProvider.edit_request("colour it", png, "")
    assert o["images"] == [{"image_url": url}] and o["model"] == "gpt-image-2.5-flare"
    r = OpenRouterImageProvider.edit_request("colour it", png, "some/model")
    assert r["input_references"] == [{"type": "image_url", "image_url": {"url": url}}]
    g = GeminiImageProvider.request("colour it", png)
    assert g["contents"][0]["parts"][1]["inline_data"]["data"] == base64.b64encode(png).decode()


# --------------------------------------------------------------------------- service


def _cleaned_image(db, line_art: bytes, color_reference: bool = True) -> int:  # type: ignore[no-untyped-def]
    from crayonlark.core import pipeline, storage
    from crayonlark.core.actors import HumanActor
    from crayonlark.core.enums import ApprovalState
    from crayonlark.core.models import Image

    with db() as s:
        book = pipeline.create_book(
            s, "Color Ref Book", HumanActor.from_cli("test"), color_reference=color_reference
        )
        img = Image(book_id=book.id, position=1, approval=ApprovalState.APPROVED)
        s.add(img)
        s.flush()
        img.cleaned_key = f"{book.slug}/{img.id:06d}-clean.png"
        print_size = PILImage.open(io.BytesIO(line_art)).resize((2250, 3000))  # 300 DPI page
        storage.put_bytes("processed", img.cleaned_key, _png(print_size), "image/png")
        return img.id


def _use_openai(db) -> None:  # type: ignore[no-untyped-def]
    from crayonlark.core import app_settings

    with db() as s:
        app_settings.set_value("image_provider", {"provider": "openai", "model": ""}, "test", s)


def test_manual_mode_uses_free_autofill(db, needs_storage, line_art) -> None:  # type: ignore[no-untyped-def]
    from crayonlark.core import color_refs, storage
    from crayonlark.core.models import ApiCost, Image

    image_id = _cleaned_image(db, line_art)
    with db() as s:
        img = s.get(Image, image_id)
        out = color_refs.make(s, img)
        assert out["source"] == "autofill" and img.color_source == "autofill"
        assert colorize.colourfulness(storage.get_bytes("processed", img.color_key)) > 0.05
        assert s.query(ApiCost).count() == 0


@respx.mock
def test_ai_colouring_is_used_and_costed(db, needs_storage, line_art, keys) -> None:  # type: ignore[no-untyped-def]
    from crayonlark.core import color_refs, storage
    from crayonlark.core.models import ApiCost, Image

    _use_openai(db)
    route = respx.post("https://api.openai.com/v1/images/edits").respond(
        200, json={"data": [{"b64_json": base64.b64encode(_painted(line_art)).decode()}]}
    )
    image_id = _cleaned_image(db, line_art)
    with db() as s:
        img = s.get(Image, image_id)
        assert color_refs.make(s, img)["source"] == "ai"
        sent = json.loads(route.calls[0].request.content)
        assert sent["images"][0]["image_url"].startswith("data:image/png;base64,")
        ref = PILImage.open(io.BytesIO(storage.get_bytes("processed", img.color_key)))
        assert ref.mode == "RGB" and max(ref.size) <= 1200
        assert s.query(ApiCost).filter(ApiCost.agent == "color_ref").count() == 1


@respx.mock
def test_ai_failure_or_no_colour_falls_back_to_autofill(db, needs_storage, line_art, keys) -> None:  # type: ignore[no-untyped-def]
    from crayonlark.core import color_refs
    from crayonlark.core.models import Image

    _use_openai(db)
    image_id = _cleaned_image(db, line_art)
    route = respx.post("https://api.openai.com/v1/images/edits")
    route.respond(200, json={"data": [{"b64_json": base64.b64encode(line_art).decode()}]})
    with db() as s:  # came back black & white
        assert color_refs.make(s, s.get(Image, image_id))["source"] == "autofill"
    route.respond(400, json={"error": {"message": "refused"}})
    with db() as s:  # refused
        assert color_refs.make(s, s.get(Image, image_id))["source"] == "autofill"


# --------------------------------------------------------------------------- Etsy PDFs


def test_etsy_page_has_the_colour_example(tmp_path: Path, design_png: Path, line_art) -> None:  # type: ignore[no-untyped-def]
    import pikepdf

    from crayonlark.print import etsy_files

    ref = tmp_path / "ref.jpg"
    ref.write_bytes(colorize.print_jpeg(colorize.colorize(line_art)))
    product = etsy_files.EtsyProduct(
        slug="t", title="Test Pages", designs=[design_png, design_png], color_refs=[ref, None]
    )
    reports = etsy_files.render_both(product, tmp_path / "out")
    for rep in reports.values():
        assert rep.ok, rep.errors
        with pikepdf.open(rep.path) as pdf:
            with_ref, without = pdf.pages[2], pdf.pages[3]  # after cover + license
            assert len(with_ref.get_images()) == 2 and len(without.get_images()) == 1


def test_etsy_build_autofills_missing_refs(db, needs_storage, line_art) -> None:  # type: ignore[no-untyped-def]
    from crayonlark.core import pipeline
    from crayonlark.core.models import Book, Image

    image_id = _cleaned_image(db, line_art)
    with db() as s:
        img = s.get(Image, image_id)
        book = s.get(Book, img.book_id)
        assert pipeline.needs_color_refs(book) == [image_id]
        keys = pipeline.build_etsy_pdfs(s, book)
        assert keys and img.color_source == "autofill"
        assert pipeline.needs_color_refs(book) == []


# --------------------------------------------------------------------------- settings flow


def test_niche_setting_flows_to_its_books(db, client, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from crayonlark.core import flows
    from crayonlark.core.enums import EtsyStatus
    from crayonlark.core.models import Book, Niche

    from .test_api_admin import H, login

    monkeypatch.setattr(flows, "queue_concepts", lambda book_id: "job")
    login(client)
    with db() as s:
        n = Niche(theme="ocean", name="Ocean Pals", color_reference=True)
        s.add(n)
        s.flush()
        nid = n.id
    r = client.post(f"/api/admin/niches/{nid}/decision", json={"approve": True}, headers=H)
    book_id = r.json()["book"]["id"]
    with db() as s:
        assert s.get(Book, book_id).color_reference is True
        s.get(Book, book_id).etsy_status = EtsyStatus.NONE

    r = client.post(f"/api/admin/niches/{nid}/color-reference", json={"enabled": False}, headers=H)
    assert r.status_code == 200 and r.json()["books_updated"] == 1
    assert r.json()["color_reference"] is False
    with db() as s:
        assert s.get(Book, book_id).color_reference is False
        s.get(Book, book_id).etsy_status = EtsyStatus.ETSY_PUBLISHED  # files already on Etsy
    r = client.post(f"/api/admin/niches/{nid}/color-reference", json={"enabled": True}, headers=H)
    assert r.json()["books_updated"] == 0
    with db() as s:
        assert s.get(Book, book_id).color_reference is False


def test_switching_a_book_on_after_cleaning_queues_refs(
    db, needs_storage, client, line_art, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    from crayonlark.core import flows
    from crayonlark.core.models import Image

    from .test_api_admin import H, login

    queued: list[tuple[int, list[int]]] = []
    monkeypatch.setattr(flows, "queue_color_refs", lambda b, ids: queued.append((b, ids)) or [])
    login(client)
    image_id = _cleaned_image(db, line_art, color_reference=False)
    with db() as s:
        book_id = s.get(Image, image_id).book_id
    r = client.patch(f"/api/admin/books/{book_id}", json={"color_reference": True}, headers=H)
    assert r.status_code == 200 and queued == [(book_id, [image_id])]


def test_listing_mentions_colour_examples_on_etsy_only() -> None:
    from crayonlark.agents import listing
    from crayonlark.core.models import Book

    book = Book(title="Ocean Pals Coloring Book", themes=["ocean"], age_min=4, age_max=8)
    book.trim, book.subtitle, book.color_reference = "8.5x11", "", True
    out = listing.offline_listing(book, 30, 6)
    assert listing.COLOR_REF_LINE not in out.kdp.description_html
    by_kind = {e.product_kind: e.description for e in out.etsy}
    assert listing.COLOR_REF_LINE in by_kind["full_pdf"]
    assert listing.COLOR_REF_LINE not in by_kind.get("activity_pack", "")
    book.color_reference = False
    assert all(
        listing.COLOR_REF_LINE not in e.description
        for e in listing.offline_listing(book, 30, 6).etsy
    )


@pytest.mark.parametrize("on", [True, False])
def test_book_from_niche_copies_the_setting(db, on: bool) -> None:  # type: ignore[no-untyped-def]
    from crayonlark.core import pipeline
    from crayonlark.core.actors import HumanActor
    from crayonlark.core.enums import NicheStatus
    from crayonlark.core.models import Niche

    with db() as s:
        n = Niche(theme="cats", name="Cat Pals", status=NicheStatus.APPROVED, color_reference=on)
        s.add(n)
        s.flush()
        assert pipeline.book_from_niche(s, n, HumanActor.from_cli("t")).color_reference is on
