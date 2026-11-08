from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from crayonlark.print import interior
from crayonlark.print.activities import build_activities
from crayonlark.print.layout import kdp_inside_margin_in, safe_box
from crayonlark.print.validate import validate_pdf


def spec(n_designs: int, **kw) -> interior.InteriorSpec:  # type: ignore[no-untyped-def]
    return interior.InteriorSpec(
        title="Test Book", designs=[Path(f"d{i}.png") for i in range(n_designs)], **kw
    )


def test_page_order_front_matter_and_designs_on_right() -> None:
    plan = interior.plan_pages(spec(12))
    kinds = [p.kind for p in plan]
    assert kinds[:6] == ["title", "copyright", "belongs_to", "blank", "color_test", "blank"]
    for p in plan:
        if p.kind == "design":
            assert p.side == "right"
            assert plan[p.number].kind == "blank"  # blank back (next page)
    assert kinds[-2:] == ["thank_you", "more_books"] or kinds[-3:-1] == ["thank_you", "more_books"]
    assert len(plan) % 2 == 0
    assert [p.number for p in plan] == list(range(1, len(plan) + 1))


def test_activities_and_answers_start_on_right() -> None:
    acts = build_activities({"mazes": 3, "sudoku": [4]})
    plan = interior.plan_pages(spec(10, activities=acts))
    first_act = next(p for p in plan if p.kind == "activity")
    first_ans = next(p for p in plan if p.kind == "answers")
    assert first_act.side == "right" and first_ans.side == "right"
    assert sum(len(p.refs) for p in plan if p.kind == "answers") == 4  # all have answers
    assert all(len(p.refs) <= 2 for p in plan if p.kind == "answers")


def test_too_few_pages_rejected() -> None:
    with pytest.raises(interior.PageCountError):
        interior.plan_pages(spec(3, include_color_test=False))


def test_margins_respect_kdp_gutter() -> None:
    assert kdp_inside_margin_in(100) == 0.375
    assert kdp_inside_margin_in(200) == 0.5
    assert kdp_inside_margin_in(400) == 0.625
    right = safe_box("8.5x11", 1, 400)
    left = safe_box("8.5x11", 2, 400)
    assert right.x == pytest.approx(0.625 * 72)  # gutter on the left of a right-hand page
    assert left.x == pytest.approx(0.5 * 72)
    assert left.x + left.w == pytest.approx((8.5 - 0.625) * 72)
    small = safe_box("8.5x11", 1, 30)
    assert small.x == pytest.approx(0.5 * 72)  # house minimum 0.5 in beats KDP 0.375


def test_render_and_validate(tmp_path: Path, design_png: Path) -> None:
    s = interior.InteriorSpec(
        title="Render Test",
        designs=[design_png] * 10,
        activities=build_activities({"mazes": 1, "sudoku": [4]}),
    )
    out = tmp_path / "interior.pdf"
    plan = interior.render(s, out)
    rep = validate_pdf(out, "8.5x11")
    assert rep.ok, rep.errors
    assert rep.pages == len(plan) >= 24
    assert rep.min_image_dpi is not None and rep.min_image_dpi >= 300
    assert rep.width_in == 8.5 and rep.height_in == 11.0
    assert all("Helvetica" not in f for f in rep.fonts)


def test_square_trim(tmp_path: Path, design_png: Path) -> None:
    s = interior.InteriorSpec(title="Square", trim="8.5x8.5", designs=[design_png] * 10)
    out = tmp_path / "sq.pdf"
    interior.render(s, out)
    rep = validate_pdf(out, "8.5x8.5")
    assert rep.ok, rep.errors


def test_validator_flags_low_dpi(tmp_path: Path) -> None:
    low = tmp_path / "low.png"
    Image.new("L", (600, 800), 255).save(low)
    s = interior.InteriorSpec(title="Low", designs=[low] * 10)
    out = tmp_path / "low.pdf"
    interior.render(s, out)
    rep = validate_pdf(out, "8.5x11")
    assert any("DPI" in e for e in rep.errors)


def test_validator_flags_wrong_trim(tmp_path: Path, design_png: Path) -> None:
    s = interior.InteriorSpec(title="Wrong", designs=[design_png] * 10)
    out = tmp_path / "w.pdf"
    interior.render(s, out)
    assert not validate_pdf(out, "8.5x8.5").ok
