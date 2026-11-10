"""Colour references: a small coloured example of each page, shown in the corner of the Etsy
printable pages (KDP books stay black & white: colour ink would make the print cost several
times higher).

Made from the cleaned line art. First choice is the configured image AI ("colour this page"),
with the original lines put back on top so the example always matches the page. If the AI is
off (manual mode), over budget, fails or returns no colour, the free auto-fill colouring is used
(each closed area gets a friendly palette colour).
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from crayonlark.core import storage
from crayonlark.core.models import Image
from crayonlark.print import colorize

log = logging.getLogger(__name__)

PROMPT = (
    "Colour in this black-and-white children's coloring page, like a neat finished page "
    "coloured by a child with bright, friendly, flat colours (crayon or marker look). Use "
    "natural colours for things (green leaves, blue water, sky blue sky). Keep every black line "
    "exactly where it is, keep the same framing, add no new objects, no text, no shading "
    "noise. Kid-friendly, age-appropriate."
)
AI_INPUT_MAX_H = 1536
MIN_COLOURFULNESS = 0.05  # below this the AI answer is treated as "not coloured"


def color_key(image: Image) -> str:
    return f"{image.book.slug}/{image.id:06d}-color.png"


def make(session: Session, image: Image, use_ai: bool = True) -> dict[str, str]:
    """Create (or redo) the colour reference for one cleaned image. Idempotent."""
    if not image.cleaned_key:
        raise ValueError(f"image {image.id} is not cleaned yet")
    line = storage.get_bytes("processed", image.cleaned_key)
    png, source = None, "autofill"
    if use_ai:
        png = _ai(line, image.book_id)
        source = "ai" if png else "autofill"
    if png is None:
        png = colorize.colorize(colorize.scaled_png(line, 1200), seed=image.id)
    key = color_key(image)
    storage.put_bytes("processed", key, png, "image/png")
    image.color_key, image.color_source = key, source
    return {"image_id": str(image.id), "color_key": key, "source": source}


def _ai(line: bytes, book_id: int) -> bytes | None:
    """AI-coloured version with the original lines on top, or None (→ auto-fill)."""
    from crayonlark.providers import ProviderBusy
    from crayonlark.providers.image import base

    try:
        result = base.edit(PROMPT, colorize.scaled_png(line, AI_INPUT_MAX_H), book_id=book_id)
    except ProviderBusy:
        raise  # rate limit / outage: the job retries later
    except Exception as exc:  # manual mode, over budget, bad key, refused… → free auto-fill
        log.info("colour reference: AI not used (%s: %s)", type(exc).__name__, exc)
        return None
    png = colorize.keep_lines(line, result.data)
    if colorize.colourfulness(png) < MIN_COLOURFULNESS:
        log.info("colour reference: AI answer had no colour, using auto-fill")
        return None
    return png
