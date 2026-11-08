"""Etsy listing images and Pinterest pins, made with Pillow from the real product PDF.

Pages are rasterised from the Letter PDF with Ghostscript, so every mockup shows exactly what the
buyer downloads. Etsy images are 2400x1800 (4:3), pins 1000x1500 (2:3). No props, brands or
claims like "handmade" ever appear on them.
"""

from __future__ import annotations

import io
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from crayonlark.core.config import ASSETS_DIR
from crayonlark.print import brand

ETSY_SIZE = (2400, 1800)
PIN_SIZE = (1000, 1500)
FONT_DIR = ASSETS_DIR / "fonts"


@dataclass
class MockupSpec:
    title: str  # short product name, e.g. "Ocean Friends Coloring Pages"
    kind: str  # full_pdf | mini_pack | bundle | activity_pack
    page_count: int
    ages: str
    theme: str = "sunny"  # background colour key in brand.COLORS


def _font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    name = "Fredoka-Bold.ttf" if bold else "Nunito-Regular.ttf"
    return ImageFont.truetype(str(FONT_DIR / name), size)


def _hex(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def _bg(key: str) -> tuple[int, int, int]:
    return _hex(brand.COLORS.get(key, brand.COLORS["sun"]))


def pdf_pages(pdf: Path, first: int, last: int, dpi: int = 80) -> list[Image.Image]:
    """Rasterise pages first..last (1-based) with Ghostscript."""
    with tempfile.TemporaryDirectory(prefix="gs-") as t:
        pattern = Path(t) / "p-%03d.png"
        subprocess.run(
            [
                "gs",
                "-q",
                "-dSAFER",
                "-dBATCH",
                "-dNOPAUSE",
                "-sDEVICE=png16m",
                f"-r{dpi}",
                f"-dFirstPage={first}",
                f"-dLastPage={last}",
                "-dTextAlphaBits=4",
                "-dGraphicsAlphaBits=4",
                f"-sOutputFile={pattern}",
                str(pdf),
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )
        return [Image.open(p).convert("RGB").copy() for p in sorted(Path(t).glob("p-*.png"))]


def page_count(pdf: Path) -> int:
    import pikepdf

    with pikepdf.open(pdf) as doc:
        return len(doc.pages)


def _paper(page: Image.Image, height: int, angle: float = 0.0) -> Image.Image:
    """A page as a sheet of paper with a soft shadow, optionally rotated (RGBA)."""
    w = round(page.width * height / page.height)
    sheet = page.resize((w, height), Image.Resampling.LANCZOS)
    pad = 40
    out = Image.new("RGBA", (w + pad * 2, height + pad * 2), (0, 0, 0, 0))
    shadow = Image.new("RGBA", out.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rectangle(
        (pad + 10, pad + 14, pad + w + 10, pad + height + 14), fill=(31, 35, 51, 90)
    )
    out = Image.alpha_composite(out, shadow.filter(ImageFilter.GaussianBlur(14)))
    out.paste(sheet, (pad, pad))
    return out.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True) if angle else out


def _banner(img: Image.Image, text: str, sub: str, y: int, color: tuple[int, int, int]) -> None:
    d = ImageDraw.Draw(img)
    size = 120
    while size > 50 and d.textlength(text, font=_font(size)) > img.width * 0.88:
        size -= 6
    f = _font(size)
    tw = d.textlength(text, font=f)
    d.text(((img.width - tw) / 2, y), text, font=f, fill=_hex(brand.COLORS["ink"]))
    if sub:
        fs = _font(round(size * 0.45), bold=False)
        sw = d.textlength(sub, font=fs)
        box = (
            (img.width - sw) / 2 - 30,
            y + size + 20,
            (img.width + sw) / 2 + 30,
            y + size + 40 + fs.size,
        )
        d.rounded_rectangle(box, radius=30, fill=color)
        d.text(((img.width - sw) / 2, y + size + 28), sub, font=fs, fill=(255, 255, 255))


def _canvas(size: tuple[int, int], theme: str) -> Image.Image:
    img = Image.new("RGBA", size, (*_hex(brand.COLORS["cream"]), 255))
    d = ImageDraw.Draw(img)
    w, h = size
    d.ellipse((-w * 0.2, h * 0.55, w * 0.45, h * 1.4), fill=(*_bg(theme), 255))
    d.ellipse((w * 0.7, -h * 0.35, w * 1.25, h * 0.35), fill=(*_bg("sky"), 255))
    return img


def _jpeg(img: Image.Image) -> bytes:
    out = io.BytesIO()
    img.convert("RGB").save(out, format="JPEG", quality=88, optimize=True)
    return out.getvalue()


def _footer(img: Image.Image) -> None:
    d = ImageDraw.Draw(img)
    f = _font(round(img.width * 0.022), bold=False)
    text = f"{brand.NAME} · {brand.SITE}"
    d.text((img.width * 0.04, img.height * 0.93), text, font=f, fill=_hex(brand.COLORS["ink"]))


def hero(pages: list[Image.Image], spec: MockupSpec) -> bytes:
    img = _canvas(ETSY_SIZE, spec.theme)
    picks = pages[:3] if len(pages) >= 3 else (pages * 3)[:3]
    w = ETSY_SIZE[0]
    for page, (cx, angle) in zip(
        picks[1:] + picks[:1], [(0.25, 7), (0.75, -7), (0.5, 0)], strict=True
    ):
        sheet = _paper(page, 1120, angle)
        img.alpha_composite(sheet, (round(w * cx - sheet.width / 2), 440))
    _banner(
        img,
        spec.title,
        f"{spec.page_count} printable pages · Ages {spec.ages}",
        60,
        _hex(brand.COLORS["coral"]),
    )
    _footer(img)
    return _jpeg(img)


def grid(pages: list[Image.Image], spec: MockupSpec) -> bytes:
    img = _canvas(ETSY_SIZE, "sky")
    _banner(
        img,
        "What's inside",
        f"{spec.page_count} pages, US Letter + A4",
        50,
        _hex(brand.COLORS["coral"]),
    )
    shown = pages[:8]
    cols = 4
    cell_w, cell_h = 520, 640
    x0 = (ETSY_SIZE[0] - cols * cell_w) // 2
    for i, page in enumerate(shown):
        sheet = _paper(page, cell_h - 80)
        x = x0 + (i % cols) * cell_w + (cell_w - sheet.width) // 2
        y = 380 + (i // cols) * cell_h
        img.alpha_composite(sheet, (x, y))
    return _jpeg(img)


def closeup(page: Image.Image, spec: MockupSpec) -> bytes:
    img = _canvas(ETSY_SIZE, spec.theme)
    img.alpha_composite(_paper(page, 1600, -4), (90, 60))
    d = ImageDraw.Draw(img)
    f = _font(80)
    lines = (
        ["Mazes, puzzles", "and more, with", "answer keys"]
        if spec.kind == "activity_pack"
        else ["Thick, simple", "lines that are", "easy to color"]
    )
    for i, line in enumerate(lines):
        d.text((1560, 620 + i * 110), line, font=f, fill=_hex(brand.COLORS["ink"]))
    return _jpeg(img)


def info_card(spec: MockupSpec) -> bytes:
    img = _canvas(ETSY_SIZE, "sun")
    d = ImageDraw.Draw(img)
    _banner(
        img,
        "Instant download",
        "Print at home, as often as you like",
        140,
        _hex(brand.COLORS["coral"]),
    )
    rows = [
        "PDF in US Letter (8.5 x 11 in) and A4",
        f"{spec.page_count} pages"
        + (", answers included" if spec.kind == "activity_pack" else ", one picture per page"),
        f"Made for kids ages {spec.ages}",
        "Personal and single-classroom use",
        "Digital file: nothing is shipped",
    ]
    f = _font(68, bold=False)
    for i, row in enumerate(rows):
        y = 640 + i * 150
        d.ellipse((560, y + 18, 600, y + 58), fill=_hex(brand.COLORS["coral"]))
        d.text((640, y), row, font=f, fill=_hex(brand.COLORS["ink"]))
    _footer(img)
    return _jpeg(img)


def pin(page: Image.Image, spec: MockupSpec) -> bytes:
    img = _canvas(PIN_SIZE, spec.theme)
    sheet = _paper(page, 1000, 0)
    img.alpha_composite(sheet, ((PIN_SIZE[0] - sheet.width) // 2, 360))
    _banner(img, spec.title, f"Printable · Ages {spec.ages}", 50, _hex(brand.COLORS["coral"]))
    _footer(img)
    return _jpeg(img)


def build_set(pdf: Path, spec: MockupSpec, max_images: int = 8) -> dict[str, bytes]:
    """5–8 Etsy images (hero first) plus 1–2 Pinterest pins, from the Letter PDF.

    Product PDFs start with a title page and the licence page (see etsy_files.render); the
    pictures and activities from page 3 on are what we show."""
    n = page_count(pdf)
    inner = pdf_pages(pdf, 3, min(n, 14)) if n >= 3 else []
    if not inner:
        inner = pdf_pages(pdf, 1, 1)
    out = {
        "etsy-01-hero.jpg": hero(inner, spec),
        "etsy-02-inside.jpg": grid(inner, spec),
        "etsy-03-closeup.jpg": closeup(inner[0], spec),
        "etsy-04-info.jpg": info_card(spec),
    }
    extra = inner[1 : max_images - 3]
    for i, page in enumerate(extra, start=5):
        canvas = _canvas(ETSY_SIZE, "sun" if i % 2 else "sky")
        canvas.alpha_composite(_paper(page, 1640), ((ETSY_SIZE[0] - 1300) // 2, 40))
        out[f"etsy-{i:02d}-page.jpg"] = _jpeg(canvas)
    out["pin-01.jpg"] = pin(inner[0], spec)
    if len(inner) > 1:
        out["pin-02.jpg"] = pin(inner[-1], spec)
    return out
