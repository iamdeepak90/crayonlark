from __future__ import annotations

import io

from PIL import Image, ImageDraw

from crayonlark.print import qa_checks
from tests.conftest import gradient, png_bytes


def test_clean_line_art_passes(line_art: bytes) -> None:
    r = qa_checks.run_checks(line_art, check_text=False)
    assert r.recommendation == "keep", r.failures
    assert r.grey_ratio < 0.01
    assert 0.01 < r.black_fill < 0.2
    assert 25 < r.line_px_at_print < 50  # 24 px stroke on 2048 px → ~35 px at 3000 px


def test_shading_and_low_res_fail() -> None:
    r = qa_checks.run_checks(gradient(), check_text=False)
    assert r.recommendation == "reject"
    assert any("shading" in f for f in r.failures)
    small = png_bytes(Image.new("L", (500, 700), 255))
    r2 = qa_checks.run_checks(small, check_text=False)
    assert any("resolution" in f for f in r2.failures)


def test_thin_lines_fail() -> None:
    img = Image.new("L", (1536, 2048), 255)
    ImageDraw.Draw(img).ellipse((300, 300, 1200, 1200), outline=0, width=1)
    r = qa_checks.run_checks(png_bytes(img), check_text=False)
    assert any("thin" in f for f in r.failures)


def test_heavy_black_fill_fails() -> None:
    img = Image.new("L", (1536, 2048), 255)
    ImageDraw.Draw(img).rectangle((0, 0, 1536, 1200), fill=0)
    r = qa_checks.run_checks(png_bytes(img), check_text=False)
    assert any("solid black" in f for f in r.failures)


def test_border_detected(line_art: bytes) -> None:
    img = Image.open(io.BytesIO(line_art))
    ImageDraw.Draw(img).rectangle((10, 10, 1525, 2037), outline=0, width=20)
    r = qa_checks.run_checks(png_bytes(img), check_text=False)
    assert r.border_ratio > 0.9
    assert any("border" in w for w in r.warnings)


def test_transparent_png_flattened_on_white() -> None:
    img = Image.new("RGBA", (1536, 2048), (0, 0, 0, 0))
    ImageDraw.Draw(img).ellipse((300, 300, 1200, 1200), outline=(0, 0, 0, 255), width=24)
    r = qa_checks.run_checks(png_bytes(img), check_text=False)
    assert r.black_fill < 0.1
