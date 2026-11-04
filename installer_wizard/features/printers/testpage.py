from __future__ import annotations

import io
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

A4_150_DPI = (1240, 1754)
MARGIN = 90
SWATCHES = ((0, 255, 255), (255, 0, 255), (255, 255, 0), (0, 0, 0), (255, 0, 0), (0, 160, 0), (0, 0, 255))


def _font(size: int):
    for name in ("DejaVuSans.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def build_test_page(printer_name: str, assistant: str, now: datetime) -> bytes:
    width, height = A4_150_DPI
    page = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(page)
    draw.rectangle((MARGIN // 2, MARGIN // 2, width - MARGIN // 2, height - MARGIN // 2), outline="black", width=3)
    draw.text((MARGIN, MARGIN), f"{assistant} · test", fill="black", font=_font(64))
    draw.text((MARGIN, MARGIN + 90), printer_name[:60], fill=(60, 60, 60), font=_font(36))
    draw.text((MARGIN, MARGIN + 140), now.strftime("%Y-%m-%d %H:%M:%S"), fill=(90, 90, 90), font=_font(30))
    swatch = (width - 2 * MARGIN) // len(SWATCHES)
    top = MARGIN + 240
    for index, color in enumerate(SWATCHES):
        left = MARGIN + index * swatch
        draw.rectangle((left, top, left + swatch - 10, top + 160), fill=color)
    grey_top = top + 220
    for step in range(11):
        level = int(255 * step / 10)
        left = MARGIN + step * ((width - 2 * MARGIN) // 11)
        draw.rectangle((left, grey_top, left + (width - 2 * MARGIN) // 11 - 6, grey_top + 90), fill=(level, level, level), outline="black")
    grid_top = grey_top + 160
    for x in range(MARGIN, width - MARGIN + 1, 50):
        draw.line((x, grid_top, x, height - MARGIN * 2), fill=(170, 170, 170), width=1)
    for y in range(grid_top, height - MARGIN * 2 + 1, 50):
        draw.line((MARGIN, y, width - MARGIN, y), fill=(170, 170, 170), width=1)
    draw.line((MARGIN, grid_top, width - MARGIN, height - MARGIN * 2), fill="black", width=2)
    draw.line((width - MARGIN, grid_top, MARGIN, height - MARGIN * 2), fill="black", width=2)
    buffer = io.BytesIO()
    page.save(buffer, format="PDF", resolution=150.0)
    return buffer.getvalue()
