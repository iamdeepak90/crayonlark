from __future__ import annotations

from pathlib import Path

import pikepdf

from crayonlark.print import etsy_files
from crayonlark.print.activities import build_activities


def test_letter_and_a4_under_20mb(tmp_path: Path, design_png: Path) -> None:
    product = etsy_files.EtsyProduct(
        slug="test-pack",
        title="Test Pack",
        designs=[design_png] * 6,
        activities=build_activities({"mazes": 1}),
    )
    reps = etsy_files.render_both(product, tmp_path)
    assert set(reps) == {"letter", "a4"}
    for rep in reps.values():
        assert rep.ok, rep.errors
        assert rep.size_bytes < 20 * 1024 * 1024
        # cover + license + 6 designs + 1 activity + 1 answer page
        assert rep.pages == 10
    assert reps["a4"].width_in == 8.268


def test_license_page_text(tmp_path: Path, design_png: Path) -> None:
    product = etsy_files.EtsyProduct(slug="lic", title="Lic", designs=[design_png])
    rep = etsy_files.render(product, "letter", tmp_path / "lic.pdf")
    with pikepdf.open(rep.path) as pdf:
        assert len(pdf.pages) == 3
