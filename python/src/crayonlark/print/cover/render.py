"""Cover builder: Jinja2 HTML/CSS template → Playwright Chromium → PDF (exact full-wrap size).

Also produces: full-wrap preview PNG, front-cover JPG thumbnail and a phone-size preview
(how the cover looks as a small Amazon/Etsy thumbnail).
"""

from __future__ import annotations

import base64
import io
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import jinja2
from PIL import Image

from crayonlark.core.config import ASSETS_DIR
from crayonlark.print import brand
from crayonlark.print.cover.dimensions import TEXT_SAFE_IN, CoverGeometry, geometry
from crayonlark.print.validate import ValidationReport

THEMES = {
    "sunny": {
        "bg": "#FFC93C",
        "ink": "#1F2333",
        "accent": "#FF6F59",
        "blob1": "#FFE08A",
        "blob2": "#5BC0EB",
    },
    "sky": {
        "bg": "#5BC0EB",
        "ink": "#1F2333",
        "accent": "#FF6F59",
        "blob1": "#9ED8F2",
        "blob2": "#FFC93C",
    },
    "coral": {
        "bg": "#FF8A73",
        "ink": "#1F2333",
        "accent": "#5BC0EB",
        "blob1": "#FFB4A5",
        "blob2": "#FFC93C",
    },
}
PREVIEW_DPI = 100
THUMB_DPI = 150


@dataclass
class CoverSpec:
    title: str
    subtitle: str
    trim: str
    page_count: int
    paper: str = "white"
    ages: str = "4-8"
    hero_png: bytes = b""
    thumbs_png: list[bytes] = field(default_factory=list)
    back_title: str = "Color, create and have fun!"
    blurb: str = ""
    bullets: list[str] = field(default_factory=list)
    series: str = ""
    theme: str = "sunny"
    spine_text_min_pages: int = 100


@dataclass
class CoverOutput:
    pdf: bytes
    preview_png: bytes
    thumb_jpg: bytes
    phone_jpg: bytes
    geometry: CoverGeometry
    report: ValidationReport


def _data_uri(png: bytes, mime: str = "image/png") -> str:
    return f"data:{mime};base64," + base64.b64encode(png).decode()


def _title_pt(title: str) -> int:
    n = len(title)
    return 46 if n <= 22 else 40 if n <= 34 else 34 if n <= 48 else 28


def render_html(spec: CoverSpec, show_guides: bool = False) -> tuple[str, CoverGeometry]:
    g = geometry(spec.trim, spec.page_count, spec.paper, spec.spine_text_min_pages)
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(ASSETS_DIR / "cover_templates")),
        autoescape=jinja2.select_autoescape(["html"]),
    )
    hero_aspect = "3 / 4"
    if spec.hero_png:
        with Image.open(io.BytesIO(spec.hero_png)) as im:
            hero_aspect = f"{im.width} / {im.height}"
    html = env.get_template("classic.html").render(
        g=g,
        c=THEMES.get(spec.theme, THEMES["sunny"]),
        fonts=(ASSETS_DIR / "fonts").as_uri(),
        safe=TEXT_SAFE_IN,
        title=spec.title,
        subtitle=spec.subtitle,
        ages=spec.ages,
        title_pt=_title_pt(spec.title) if g.trim_h >= 10 else _title_pt(spec.title) - 6,
        subtitle_pt=15 if len(spec.subtitle) < 50 else 12,
        hero=_data_uri(spec.hero_png) if spec.hero_png else "",
        hero_aspect=hero_aspect,
        thumbs=[_data_uri(t) for t in spec.thumbs_png[:3]],
        mascot=_data_uri(brand.mascot_png(gray=False, width=300)),
        back_title=spec.back_title,
        blurb=spec.blurb,
        bullets=spec.bullets[:5],
        spine_label=f"{spec.title}  ·  Crayonlark",
        spine_pt=max(8, min(18, int(g.spine * 72 * 0.55))),
        show_guides=show_guides,
    )
    return html, g


def exact_page_box(path: Path, width_in: float, height_in: float) -> None:
    """Chromium rounds the paper size to whole CSS pixels (up to ~0.01 in too wide). The layout
    is anchored top-left, so we set the exact KDP size; only a sliver of outer bleed is cut."""
    import pikepdf

    with pikepdf.open(path, allow_overwriting_input=True) as pdf:
        box = [0, 0, round(width_in * 72, 3), round(height_in * 72, 3)]
        mb = pdf.pages[0].mediabox
        top = float(mb[3])
        for page in pdf.pages:
            page.mediabox = pikepdf.Array(box)
            if top != box[3]:  # keep the top edge where the layout starts
                page.mediabox = pikepdf.Array([0, top - box[3], box[2], top])
            if "/CropBox" in page.obj:
                del page.obj["/CropBox"]
        pdf.save(path)


def render(spec: CoverSpec) -> CoverOutput:
    from playwright.sync_api import sync_playwright

    from crayonlark.print.validate import validate_cover_pdf

    html, g = render_html(spec)
    with tempfile.TemporaryDirectory(prefix="cover-") as t, sync_playwright() as p:
        tmp = Path(t)
        page_file = tmp / "cover.html"
        page_file.write_text(html, encoding="utf-8")
        browser = p.chromium.launch(args=["--no-sandbox"])
        try:
            page = browser.new_page(
                viewport={"width": round(g.width * 96), "height": round(g.height * 96)},
                device_scale_factor=THUMB_DPI / 96,
            )
            page.goto(page_file.as_uri(), wait_until="load")
            page.evaluate("document.fonts.ready")
            pdf_path = tmp / "cover.pdf"
            page.pdf(
                path=str(pdf_path),
                width=f"{g.width}in",
                height=f"{g.height}in",
                print_background=True,
                page_ranges="1",
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
            )
            shot = page.screenshot(type="png", full_page=False)
        finally:
            browser.close()
        exact_page_box(pdf_path, g.width, g.height)
        report = validate_cover_pdf(pdf_path, g.width, g.height)
        pdf = pdf_path.read_bytes()

    full = Image.open(io.BytesIO(shot)).convert("RGB")
    scale = full.width / g.width  # px per inch
    front = full.crop(
        (
            round(g.front.x * scale),
            round(g.front.y * scale),
            round((g.front.x + g.front.w) * scale),
            round((g.front.y + g.front.h) * scale),
        )
    )
    preview = full.resize((round(g.width * PREVIEW_DPI), round(g.height * PREVIEW_DPI)))
    phone = front.copy()
    phone.thumbnail((360, 480))

    def enc(img: Image.Image, fmt: str) -> bytes:
        b = io.BytesIO()
        img.save(b, format=fmt, quality=88)
        return b.getvalue()

    return CoverOutput(
        pdf=pdf,
        preview_png=enc(preview, "PNG"),
        thumb_jpg=enc(front, "JPEG"),
        phone_jpg=enc(phone, "JPEG"),
        geometry=g,
        report=report,
    )
