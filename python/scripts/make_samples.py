"""Generate the 5 bundled sample line-art images used by `make demo` (original, simple shapes).

They are deliberately a little "dirty" (soft edges, grey noise, specks) so the cleanup worker
has something to do. Run: uv run python scripts/make_samples.py
"""

from __future__ import annotations

import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

W, H = 1536, 2048
LW = 22
OUT = Path(__file__).resolve().parents[1] / "assets" / "sample_lineart"


def canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("L", (W, H), 255)
    return img, ImageDraw.Draw(img)


def face(d: ImageDraw.ImageDraw, cx: int, cy: int, r: int) -> None:
    d.ellipse((cx - r * 0.45 - 22, cy - r * 0.2 - 22, cx - r * 0.45 + 22, cy - r * 0.2 + 22), fill=0)
    d.ellipse((cx + r * 0.45 - 22, cy - r * 0.2 - 22, cx + r * 0.45 + 22, cy - r * 0.2 + 22), fill=0)
    d.arc((cx - r * 0.5, cy - r * 0.3, cx + r * 0.5, cy + r * 0.55), 20, 160, fill=0, width=LW)


def sun() -> Image.Image:
    img, d = canvas()
    cx, cy, r = W // 2, H // 2, 400
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=0, width=LW)
    for i in range(12):
        a = i * math.pi / 6
        x1, y1 = cx + math.cos(a) * (r + 60), cy + math.sin(a) * (r + 60)
        x2, y2 = cx + math.cos(a) * (r + 240), cy + math.sin(a) * (r + 240)
        d.line((x1, y1, x2, y2), fill=0, width=LW)
    face(d, cx, cy, r)
    return img


def fish() -> Image.Image:
    img, d = canvas()
    d.ellipse((220, 700, 1150, 1350), outline=0, width=LW)
    d.polygon([(1100, 1025), (1380, 760), (1380, 1290)], outline=0, width=LW)
    d.ellipse((380, 900, 450, 970), fill=0)
    d.arc((300, 980, 480, 1120), 300, 60, fill=0, width=LW)
    for x in (600, 760, 920):
        d.arc((x - 90, 830, x + 90, 1220), 300, 60, fill=0, width=LW)
    for i, (bx, by, br) in enumerate([(300, 520, 50), (420, 380, 70), (280, 230, 40)]):
        d.ellipse((bx - br, by - br, bx + br, by + br), outline=0, width=LW - 6 + i)
    d.arc((100, 1500, 1436, 1900), 200, 340, fill=0, width=LW)
    return img


def house() -> Image.Image:
    img, d = canvas()
    d.rectangle((330, 1000, 1130, 1700), outline=0, width=LW)
    d.polygon([(250, 1010), (730, 520), (1210, 1010)], outline=0, width=LW)
    d.rectangle((640, 1350, 820, 1700), outline=0, width=LW)
    d.ellipse((780, 1510, 805, 1535), fill=0)
    for x in (420, 900):
        d.rectangle((x, 1120, x + 150, 1270), outline=0, width=LW)
        d.line((x + 75, 1120, x + 75, 1270), fill=0, width=LW - 8)
    d.ellipse((1180, 260, 1430, 510), outline=0, width=LW)
    d.line((0, 1700, W, 1700), fill=0, width=LW)
    for x in range(120, W, 260):
        d.line((x, 1700, x - 30, 1620), fill=0, width=14)
        d.line((x, 1700, x + 30, 1620), fill=0, width=14)
    return img


def apple() -> Image.Image:
    img, d = canvas()
    d.ellipse((300, 650, 820, 1600), outline=0, width=LW)
    d.ellipse((720, 650, 1240, 1600), outline=0, width=LW)
    d.rectangle((560, 690, 980, 1560), fill=255)
    d.arc((300, 650, 1240, 1600), 20, 160, fill=0, width=LW)
    d.arc((450, 600, 1090, 900), 200, 340, fill=0, width=LW)
    d.line((770, 690, 800, 470), fill=0, width=LW)
    d.ellipse((800, 430, 1080, 560), outline=0, width=LW)
    face(d, 770, 1120, 300)
    return img


def rocket() -> Image.Image:
    img, d = canvas()
    cx = W // 2
    d.polygon([(cx, 250), (cx + 260, 700), (cx + 260, 1450), (cx - 260, 1450), (cx - 260, 700)],
              outline=0, width=LW)
    d.ellipse((cx - 130, 800, cx + 130, 1060), outline=0, width=LW)
    d.polygon([(cx - 260, 1150), (cx - 480, 1550), (cx - 260, 1450)], outline=0, width=LW)
    d.polygon([(cx + 260, 1150), (cx + 480, 1550), (cx + 260, 1450)], outline=0, width=LW)
    d.polygon([(cx - 150, 1450), (cx, 1800), (cx + 150, 1450)], outline=0, width=LW)
    for sx, sy in [(260, 400), (1250, 300), (1180, 1700), (300, 1850), (1300, 1000)]:
        d.line((sx - 50, sy, sx + 50, sy), fill=0, width=14)
        d.line((sx, sy - 50, sx, sy + 50), fill=0, width=14)
    return img


def dirty(img: Image.Image, seed: int) -> Image.Image:
    rng = random.Random(seed)
    img = img.filter(ImageFilter.GaussianBlur(2.2))
    d = ImageDraw.Draw(img)
    for _ in range(40):  # specks
        x, y, r = rng.randrange(W), rng.randrange(H), rng.randrange(2, 6)
        d.ellipse((x - r, y - r, x + r, y + r), fill=rng.randrange(0, 90))
    noise = Image.effect_noise((W, H), 10).point(lambda v: 255 if v > 120 else 245)
    return Image.composite(img, noise, img.point(lambda v: 255 if v < 250 else 0))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for i, (name, fn) in enumerate(
        [("01-happy-sun", sun), ("02-friendly-fish", fish), ("03-little-house", house),
         ("04-smiling-apple", apple), ("05-rocket", rocket)]
    ):
        dirty(fn(), i).save(OUT / f"{name}.png", optimize=True)
        print("wrote", name)


if __name__ == "__main__":
    main()
