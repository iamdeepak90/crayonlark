from __future__ import annotations

import io
import shutil
from pathlib import Path

import pytest
from PIL import Image

from crayonlark.print import colorize
from crayonlark.print.cover.render import CoverSpec, render, render_html

try:
    from playwright.sync_api import sync_playwright  # noqa: F401

    HAVE_PW = shutil.which("magick") is not None  # proxy for "inside the worker image"
except ImportError:  # pragma: no cover
    HAVE_PW = False


def test_colorize_fills_closed_regions(line_art: bytes) -> None:
    out = Image.open(io.BytesIO(colorize.colorize(line_art))).convert("RGB")
    assert out.getpixel((750, 750)) != (255, 255, 255)  # inside the circle: coloured
    assert out.getpixel((5, 5)) == (255, 255, 255)  # background: white


def test_html_keeps_barcode_area_and_spine_rule(line_art: bytes) -> None:
    html, _g = render_html(
        CoverSpec(title="Dino Fun", subtitle="", trim="8.5x11", page_count=60, hero_png=line_art)
    )
    assert 'class="barcode"' in html
    assert "spine-text" not in html.split("<body>")[1]  # 60 pages: no spine text
    html2, g2 = render_html(
        CoverSpec(title="Dino Fun", subtitle="", trim="8.5x11", page_count=120, hero_png=line_art)
    )
    assert 'class="spine-text"' in html2 and g2.spine_text


@pytest.mark.skipif(not HAVE_PW, reason="needs Chromium (worker image)")
def test_render_cover_pdf(line_art: bytes, tmp_path: Path) -> None:
    out = render(
        CoverSpec(
            title="Ocean Friends Coloring Book",
            subtitle="For Kids Ages 4-8",
            trim="8.5x11",
            page_count=48,
            hero_png=colorize.colorize(line_art),
            thumbs_png=[line_art] * 3,
            blurb="Fun pages.",
            bullets=["30 pages"],
        )
    )
    assert out.report.ok, out.report.errors
    assert out.report.width_in == pytest.approx(out.geometry.width, abs=0.01)
    assert out.report.height_in == pytest.approx(11.25, abs=0.01)
    thumb = Image.open(io.BytesIO(out.thumb_jpg))
    assert thumb.height > thumb.width  # portrait front cover
    (tmp_path / "cover.pdf").write_bytes(out.pdf)
