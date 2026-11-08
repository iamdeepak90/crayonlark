from __future__ import annotations

import io

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from crayonlark.print import cleanup, qa_checks
from tests.conftest import needs_tools, png_bytes


def test_despeckle_removes_small_components_only() -> None:
    mask = np.zeros((200, 200), dtype=np.uint8)
    mask[10:12, 10:12] = 1  # speck
    mask[50:150, 98:102] = 1  # line
    out, removed = cleanup.despeckle(mask, min_speck_px=20)
    assert removed == 1
    assert out[10, 10] == 0 and out[100, 100] == 1


@needs_tools
def test_clean_image_is_pure_bw_300dpi() -> None:
    img = Image.new("L", (1536, 2048), 250)
    d = ImageDraw.Draw(img)
    d.ellipse((300, 300, 1200, 1200), outline=10, width=24)
    for x in range(100, 1500, 300):
        d.ellipse((x, 1800, x + 5, 1805), fill=40)  # specks
    img = img.filter(ImageFilter.GaussianBlur(2))
    res = cleanup.clean_image(png_bytes(img))
    out = Image.open(io.BytesIO(res.png))
    arr = np.asarray(out)
    assert set(np.unique(arr)) <= {0, 255}
    assert out.info.get("dpi", (0, 0))[0] == 300 or round(out.info["dpi"][0]) == 300
    assert max(out.size) <= 3000 and min(out.size) >= 2000
    assert res.specks_removed >= 4
    assert b"<svg" in res.svg
    r = qa_checks.run_checks(res.png, check_text=False)
    assert r.grey_ratio == 0 and r.recommendation == "keep"
