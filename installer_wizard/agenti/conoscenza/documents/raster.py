import io
import math
from functools import lru_cache

SCALE = 200
FONTS = ("DejaVuSans.ttf", "LiberationSans-Regular.ttf", "Arial.ttf", "arial.ttf")
BOLD = ("DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf", "Arial Bold.ttf", "arialbd.ttf")
GRID, AXIS, TICK, TEXT = (238, 238, 238), (204, 204, 204), (85, 85, 85), (51, 51, 51)


def rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


@lru_cache(maxsize=16)
def font(size: int, bold: bool = False):
    from PIL import ImageFont
    for name in BOLD if bold else FONTS:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def width(draw, text: str, f) -> float:
    return draw.textlength(text, font=f)


def fit(draw, text: str, f, limit: float) -> str:
    if width(draw, text, f) <= limit:
        return text
    while text and width(draw, text + "…", f) > limit:
        text = text[:-1]
    return text + "…"


def ticks(low: float, high: float, count: int = 5) -> list[float]:
    span = high - low or abs(high) or 1.0
    raw = span / count
    mag = 10 ** math.floor(math.log10(raw))
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    start = math.floor(low / step) * step
    out = [round(start, 10)]
    while out[-1] < high:
        out.append(round(out[-1] + step, 10))
    return out


def label(v: float) -> str:
    return f"{v:,.0f}".replace(",", ".") if abs(v) >= 100 or float(v).is_integer() else f"{v:.2f}".rstrip("0").rstrip(".")


def pie(draw, chart: dict, colors: list, box: tuple) -> None:
    values = [max(float(v), 0.0) for v in chart["series"][0]["values"]]
    total = sum(values) or 1.0
    x0, y0, x1, y1 = box
    size = min(x1 - x0 - 260, y1 - y0)
    cx, cy = x0 + size / 2 + 20, y0 + (y1 - y0) / 2
    r = size / 2
    start = -90.0
    small = font(int(SCALE * 0.11))
    for i, v in enumerate(values):
        sweep = 360 * v / total
        draw.pieslice((cx - r, cy - r, cx + r, cy + r), start, start + sweep, fill=colors[i % len(colors)],
                      outline="white", width=4)
        mid = math.radians(start + sweep / 2)
        dist = r * (0.78 if chart["chart"] == "doughnut" else 0.6)
        if sweep > 12:
            draw.text((cx + dist * math.cos(mid), cy + dist * math.sin(mid)), f"{v / total:.0%}", font=small,
                      fill="white" if chart["chart"] == "pie" else TEXT, anchor="mm")
        start += sweep
    if chart["chart"] == "doughnut":
        hole = r * 0.58
        draw.ellipse((cx - hole, cy - hole, cx + hole, cy + hole), fill="white")
    legend(draw, [str(c) for c in chart["categories"]], colors, (cx + r + 40, y0 + 20), x1)


def legend(draw, names: list[str], colors: list, origin: tuple, right: float) -> None:
    f = font(int(SCALE * 0.11))
    x, y = origin
    for i, name in enumerate(names):
        draw.rectangle((x, y + 6, x + 22, y + 28), fill=colors[i % len(colors)])
        draw.text((x + 32, y), fit(draw, name, f, right - x - 40), font=f, fill=TEXT)
        y += 40


def cartesian(draw, chart: dict, colors: list, box: tuple) -> None:
    kind, series = chart["chart"], chart["series"]
    cats = [str(c) for c in chart["categories"]]
    values = [float(v) for s in series for v in s["values"]] or [0.0]
    low = min(0.0, min(values)) if kind in ("bar", "column", "area") else min(values)
    scale = ticks(low, max(values))
    lo, hi = scale[0], scale[-1] if scale[-1] > scale[0] else scale[0] + 1
    f = font(int(SCALE * 0.1))
    x0, y0, x1, y1 = box
    if len(series) > 1:
        legend_w = max(width(draw, s["name"], f) for s in series) + 60
        legend(draw, [s["name"] for s in series], colors, (x1 - legend_w, y0), x1)
        x1 -= legend_w + 20
    horizontal = kind == "bar"
    gutter = (max(width(draw, c, f) for c in cats) if horizontal else max(width(draw, label(t), f) for t in scale)) + 24
    if chart.get("unit"):
        gutter += 34
    px0, py0, px1, py1 = x0 + gutter, y0 + 10, x1, y1 - (70 if horizontal and chart.get("unit") else 40)
    n, k = len(cats), max(len(series), 1)

    def at(v: float) -> float:
        frac = (v - lo) / (hi - lo)
        return px0 + frac * (px1 - px0) if horizontal else py1 - frac * (py1 - py0)

    for t in scale:
        p = at(t)
        if horizontal:
            draw.line((p, py0, p, py1), fill=GRID, width=2)
            draw.text((p, py1 + 10), label(t), font=f, fill=TICK, anchor="ma")
        else:
            draw.line((px0, p, px1, p), fill=GRID, width=2)
            draw.text((px0 - 12, p), label(t), font=f, fill=TICK, anchor="rm")
    draw.line((px0, py1, px1, py1), fill=AXIS, width=2)
    draw.line((px0, py0, px0, py1), fill=AXIS, width=2)
    slot = ((py1 - py0) if horizontal else (px1 - px0)) / max(n, 1)
    for i, c in enumerate(cats):
        mid = (py0 if horizontal else px0) + slot * (i + 0.5)
        if horizontal:
            draw.text((px0 - 12, mid), fit(draw, c, f, gutter - 24), font=f, fill=TICK, anchor="rm")
        else:
            draw.text((mid, py1 + 10), fit(draw, c, f, slot - 6), font=f, fill=TICK, anchor="ma")
    base = at(max(lo, 0.0) if lo <= 0 <= hi else lo)
    bar = slot * 0.8 / k
    for j, s in enumerate(series):
        color = colors[j % len(colors)]
        vals = [float(v) for v in s["values"]][:n]
        if kind in ("bar", "column"):
            for i, v in enumerate(vals):
                a = (py0 if horizontal else px0) + slot * i + slot * 0.1 + bar * j
                if horizontal:
                    draw.rectangle((min(base, at(v)), a, max(base, at(v)), a + bar - 2), fill=color)
                else:
                    draw.rectangle((a, min(base, at(v)), a + bar - 2, max(base, at(v))), fill=color)
            continue
        points = [(px0 + slot * (i + 0.5), at(v)) for i, v in enumerate(vals)]
        if kind == "area" and points:
            tint = tuple(int(ch + (255 - ch) * 0.65) for ch in color)
            draw.polygon([(points[0][0], base), *points, (points[-1][0], base)], fill=tint)
        if kind != "scatter" and len(points) > 1:
            draw.line(points, fill=color, width=6, joint="curve")
        dot = 9 if kind == "scatter" else 7
        for x, y in points:
            draw.ellipse((x - dot, y - dot, x + dot, y + dot), fill=color)
    if chart.get("unit"):
        if horizontal:
            draw.text(((px0 + px1) / 2, y1 - 4), chart["unit"], font=f, fill=TICK, anchor="md")
        else:
            draw.text((x0 + 4, (py0 + py1) / 2), chart["unit"], font=f, fill=TICK, anchor="lm")


def png(chart: dict, theme: dict, width_in: float = 6.4, height_in: float = 3.4) -> bytes:
    from PIL import Image, ImageDraw
    w, h = int(width_in * SCALE), int(height_in * SCALE)
    image = Image.new("RGB", (w, h), "white")
    draw = ImageDraw.Draw(image)
    colors = [rgb(c) for c in theme["chart"]]
    top = 30
    if chart.get("title"):
        title = font(int(SCALE * 0.15), bold=True)
        draw.text((30, 24), fit(draw, chart["title"], title, w - 60), font=title, fill=rgb(theme["dark"]))
        top = 24 + int(SCALE * 0.15) + 40
    box = (30, top, w - 30, h - 30)
    if chart["chart"] in ("pie", "doughnut"):
        pie(draw, chart, colors, box)
    else:
        cartesian(draw, chart, colors, box)
    buf = io.BytesIO()
    image.save(buf, format="PNG", optimize=True, dpi=(SCALE, SCALE))
    return buf.getvalue()
