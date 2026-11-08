from __future__ import annotations

import pytest

from crayonlark.print.cover.dimensions import BLEED_IN, geometry, spine_width


def test_spine_width_per_paper() -> None:
    assert spine_width(100, "white") == pytest.approx(0.2252)
    assert spine_width(100, "cream") == pytest.approx(0.25)
    assert spine_width(100, "color") == pytest.approx(0.2347)
    with pytest.raises(ValueError):
        spine_width(20)


def test_full_wrap_8_5x11_white_120_pages() -> None:
    g = geometry("8.5x11", 120, "white")
    spine = 120 * 0.002252  # 0.27024
    assert g.spine == pytest.approx(spine)
    assert g.width == pytest.approx(0.125 + 8.5 + spine + 8.5 + 0.125)  # 17.52024
    assert g.height == pytest.approx(11.25)
    assert g.spine_text  # ≥ 100 pages


def test_panels_and_barcode_positions() -> None:
    g = geometry("8.5x8.5", 60)
    assert g.back.x == BLEED_IN and g.back.w == 8.5
    assert g.spine_rect.x == pytest.approx(BLEED_IN + 8.5)
    assert g.front.x == pytest.approx(BLEED_IN + 8.5 + g.spine)
    assert g.front.x + g.front.w + BLEED_IN == pytest.approx(g.width)
    # barcode box sits inside the back cover, bottom right, 0.25 in from the trim edges
    assert g.barcode.x + g.barcode.w == pytest.approx(BLEED_IN + 8.5 - 0.25)
    assert g.barcode.y + g.barcode.h == pytest.approx(BLEED_IN + 8.5 - 0.25)
    assert (g.barcode.w, g.barcode.h) == (2.0, 1.2)
    assert not g.spine_text  # 60 pages: too thin for spine text


def test_spine_text_threshold_configurable() -> None:
    assert geometry("8.5x11", 80, spine_text_min_pages=79).spine_text
    assert not geometry("8.5x11", 78, spine_text_min_pages=79).spine_text
