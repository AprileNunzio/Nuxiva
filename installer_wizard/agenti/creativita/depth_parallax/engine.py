import json
import math

from agenti.stage import native


def _pixel_luma(rgba: bytes, width: int, height: int, x: int, y: int) -> tuple[float, int, list[int]]:
    cx = max(0, min(width - 1, x))
    cy = max(0, min(height - 1, y))
    base = (cy * width + cx) * 4
    r = rgba[base]
    g = rgba[base + 1]
    b = rgba[base + 2]
    a = rgba[base + 3]
    luma = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0
    return luma, a, [r, g, b]


def reconstruct_depth_relief(
    concept: str,
    rgba: bytes,
    width: int,
    height: int,
    max_vertices: int = 2048,
) -> dict:
    if native.lib is not None and hasattr(native.lib, "depth_parallax_reconstruct"):
        try:
            raw = native.lib.depth_parallax_reconstruct(
                str(concept or ""),
                bytes(rgba),
                int(width),
                int(height),
                int(max_vertices),
            )
            return json.loads(raw)
        except Exception:
            pass

    w, h = int(width), int(height)
    if w < 2 or h < 2 or len(rgba) < w * h * 4:
        return {
            "concept": str(concept or ""),
            "width": w,
            "height": h,
            "vertices": [],
            "specular_power": 32.0,
            "parallax_scale": 0.45,
        }

    step = max(1, (w * h) // max(64, int(max_vertices)))
    vertices = []
    idx = 0
    total = w * h
    while idx < total and len(vertices) < max_vertices:
        x = idx % w
        y = idx // w
        luma, alpha, rgb = _pixel_luma(rgba, w, h, x, y)
        if alpha > 24:
            l_left, _, _ = _pixel_luma(rgba, w, h, x - 1, y)
            l_right, _, _ = _pixel_luma(rgba, w, h, x + 1, y)
            l_up, _, _ = _pixel_luma(rgba, w, h, x, y - 1)
            l_down, _, _ = _pixel_luma(rgba, w, h, x, y + 1)

            dx = (l_right - l_left) * 2.0
            dy = (l_down - l_up) * 2.0
            nz = 1.0
            length = max(1e-6, math.sqrt(dx * dx + dy * dy + nz * nz))
            normal = [round(-dx / length, 4), round(-dy / length, 4), round(nz / length, 4)]

            nx = (x / float(w)) * 2.0 - 1.0
            ny = 1.0 - (y / float(h)) * 2.0
            radial = math.sqrt(max(0.0, 1.0 - min(1.0, nx * nx + ny * ny)))
            depth_z = (luma * 0.65 + radial * 0.35) * 0.55

            vertices.append({
                "position": [round(nx, 4), round(ny, 4), round(depth_z, 4)],
                "normal": normal,
                "color_rgb": rgb,
            })
            if depth_z > 0.08 and len(vertices) < max_vertices:
                vertices.append({
                    "position": [round(nx, 4), round(ny, 4), round(-depth_z * 0.75, 4)],
                    "normal": [normal[0], normal[1], -normal[2]],
                    "color_rgb": rgb,
                })
        idx += step

    return {
        "concept": str(concept or ""),
        "width": w,
        "height": h,
        "vertices": vertices,
        "specular_power": 32.0,
        "parallax_scale": 0.45,
    }
