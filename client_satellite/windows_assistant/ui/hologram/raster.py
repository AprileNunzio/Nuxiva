import numpy as np

TAU = 2.0 * np.pi


class Grid:
    def __init__(self, size: int) -> None:
        if size < 16:
            raise ValueError("hologram size too small")
        self.size = size
        half = size / 2.0
        axis = ((np.arange(size, dtype=np.float32) + 0.5) - half) / half
        self.u = np.broadcast_to(axis[None, :], (size, size))
        self.v = np.broadcast_to(axis[:, None], (size, size))
        self.axis = axis
        self.r = np.hypot(self.u, self.v)
        self.theta = np.arctan2(self.v, self.u)
        self.px = np.float32(1.0 / half)


def edge(distance: np.ndarray, px: float) -> np.ndarray:
    return np.clip(distance / px + 0.5, 0.0, 1.0)


def band(r: np.ndarray, center: float, width: float, px: float) -> np.ndarray:
    return edge(width * 0.5 - np.abs(r - center), px)


def gauss(distance: np.ndarray, sigma: float) -> np.ndarray:
    return np.exp(-np.square(distance / sigma))


def wrap(angle: np.ndarray) -> np.ndarray:
    return (angle + np.pi) % TAU - np.pi


class Film:
    def __init__(self, size: int) -> None:
        self.rgb = np.zeros((size, size, 3), dtype=np.float32)
        self.alpha = np.zeros((size, size), dtype=np.float32)

    def over(self, color: np.ndarray, coverage: np.ndarray) -> None:
        cover = np.clip(coverage, 0.0, 1.0)
        keep = 1.0 - cover
        self.rgb = color * cover[..., None] + self.rgb * keep[..., None]
        self.alpha = cover + self.alpha * keep

    def over_box(self, box: tuple, color: np.ndarray, coverage: np.ndarray) -> None:
        cover = np.clip(coverage, 0.0, 1.0)
        keep = 1.0 - cover
        self.rgb[box] = color * cover[..., None] + self.rgb[box] * keep[..., None]
        self.alpha[box] = cover + self.alpha[box] * keep

    def glow(self, color: np.ndarray, intensity: np.ndarray) -> None:
        light = np.clip(intensity, 0.0, None)
        self.rgb += color * light[..., None]
        self.alpha += np.clip(light, 0.0, 1.0) * (1.0 - self.alpha)

    def glow_flat(self, index: np.ndarray, color: np.ndarray, intensity: np.ndarray) -> None:
        light = np.clip(intensity, 0.0, None)
        rgb, alpha = self.rgb.reshape(-1, 3), self.alpha.reshape(-1)
        rgb[index] += color * light[:, None]
        alpha[index] += np.clip(light, 0.0, 1.0) * (1.0 - alpha[index])

    def glow_box(self, box: tuple, color: np.ndarray, intensity: np.ndarray) -> None:
        light = np.clip(intensity, 0.0, None)
        self.rgb[box] += color * light[..., None]
        self.alpha[box] += np.clip(light, 0.0, 1.0) * (1.0 - self.alpha[box])

    def spot(self, grid: "Grid", color: np.ndarray, x: float, y: float, sigma: float, strength: float) -> None:
        half = grid.size / 2.0
        cx, cy, reach = (x + 1.0) * half, (y + 1.0) * half, sigma * half * 3.0
        x0, x1 = max(0, int(cx - reach)), min(grid.size, int(cx + reach) + 2)
        y0, y1 = max(0, int(cy - reach)), min(grid.size, int(cy + reach) + 2)
        if x0 >= x1 or y0 >= y1:
            return
        du = grid.axis[x0:x1][None, :] - x
        dv = grid.axis[y0:y1][:, None] - y
        self.glow_box((slice(y0, y1), slice(x0, x1)), color, strength * np.exp(-(du * du + dv * dv) / (sigma * sigma)))

    def pack(self, opacity: float) -> bytes:
        level = float(np.clip(opacity, 0.0, 1.0))
        alpha = np.clip(np.maximum(self.alpha, self.rgb.max(axis=2)), 0.0, 1.0) * level
        rgb = np.minimum(np.clip(self.rgb * level, 0.0, 1.0), alpha[..., None])
        out = np.empty(alpha.shape + (4,), dtype=np.uint8)
        out[..., 0] = np.rint(rgb[..., 2] * 255.0)
        out[..., 1] = np.rint(rgb[..., 1] * 255.0)
        out[..., 2] = np.rint(rgb[..., 0] * 255.0)
        out[..., 3] = np.rint(alpha * 255.0)
        return out.tobytes()
