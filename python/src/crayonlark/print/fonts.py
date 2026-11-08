"""Register the bundled OFL fonts with ReportLab (embedded in every PDF)."""

from __future__ import annotations

from functools import lru_cache

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from crayonlark.core.config import ASSETS_DIR

DISPLAY = "Fredoka-Bold"
DISPLAY_SEMI = "Fredoka-SemiBold"
BODY = "Nunito-Regular"
BODY_BOLD = "Nunito-Bold"


@lru_cache
def register_fonts() -> None:
    for name in (DISPLAY, DISPLAY_SEMI, BODY, BODY_BOLD):
        pdfmetrics.registerFont(TTFont(name, str(ASSETS_DIR / "fonts" / f"{name}.ttf")))
