import numpy as np

from ui.hologram import palette
from ui.hologram.raster import TAU, Grid, band, edge, gauss

CORE = 0.44
SWEEP = 0.53
TICK_BASE = 0.60
TICK_REACH = 0.14
OUTER = 0.83
HALO_TIGHT = 0.16
HALO_WIDE = 0.30
EPSILON = 1e-3


def _flat(mask: np.ndarray) -> np.ndarray:
    return np.flatnonzero(mask.reshape(-1) > EPSILON)


def _box(grid: Grid, radius: float) -> tuple:
    half = grid.size / 2.0
    low, high = max(0, int(half * (1.0 - radius)) - 1), min(grid.size, int(half * (1.0 + radius)) + 2)
    return slice(low, high), slice(low, high)


class Geometry:
    def __init__(self, grid: Grid) -> None:
        self.grid = grid
        r, theta, px = grid.r, grid.theta, grid.px
        fade = edge(1.0 - r, px * 6.0)
        outside = np.clip(r - CORE, 0.0, None)
        self.halo_tight = gauss(outside, HALO_TIGHT) * fade
        self.halo_wide = gauss(outside, HALO_WIDE) * fade
        self._outer(r, theta, px)
        self._sweep(r, theta, px)
        self._spectrum(r, theta, px)
        self._core(r, theta, px)

    def _outer(self, r, theta, px) -> None:
        line = band(r, OUTER, px * 1.1, px)
        wide = band(r, OUTER, px * 3.2, px)
        self.outer_index = _flat(wide + line)
        self.outer_theta = theta.reshape(-1)[self.outer_index]
        self.outer_line = line.reshape(-1)[self.outer_index]
        self.outer_wide = wide.reshape(-1)[self.outer_index]

    def _sweep(self, r, theta, px) -> None:
        ring = band(r, SWEEP, px * 1.6, px)
        soft = gauss(r - SWEEP, px * 4.0)
        self.sweep_index = _flat(ring + soft)
        self.sweep_theta = theta.reshape(-1)[self.sweep_index]
        self.sweep_ring = ring.reshape(-1)[self.sweep_index]
        self.sweep_soft = soft.reshape(-1)[self.sweep_index]

    def _spectrum(self, r, theta, px, count: int = 64) -> None:
        zone = (r > TICK_BASE - px * 2.0) & (r < TICK_BASE + TICK_REACH + 0.04)
        self.tick_index = np.flatnonzero(zone.reshape(-1))
        rr, tt = r.reshape(-1)[self.tick_index], theta.reshape(-1)[self.tick_index]
        position = (tt + np.pi) / TAU * count
        self.tick_slot = np.floor(position).astype(np.int64) % count
        across = np.abs(position - np.floor(position) - 0.5) * (TAU / count) * rr
        self.tick_cover = edge(px * 0.75 - across, px) * edge(rr - TICK_BASE, px)
        self.tick_r = rr
        self.tick_aura = gauss(rr - (TICK_BASE + 0.07), 0.08)

    def _core(self, r, theta, px) -> None:
        grid = self.grid
        self.core_box = _box(grid, CORE + 0.06)
        box = self.core_box
        rb, tb = r[box], theta[box]
        ub, vb = grid.u[box], grid.v[box]
        inside = edge(CORE - rb, px)
        depth = np.clip(rb / CORE, 0.0, 1.0)
        self.core_inside = inside
        self.core_base = palette.DEEP + (palette.GLASS - palette.DEEP) * (1.0 - depth[..., None])
        self.core_fresnel = depth ** 5 * inside
        self.core_r = rb
        self.core_rim = band(rb, CORE, px * 1.3, px)
        self.core_rim_glow = gauss(rb - CORE, px * 3.0)
        du, dv = (ub + CORE * 0.36) / (CORE * 0.42), (vb + CORE * 0.48) / (CORE * 0.22)
        sheen = np.exp(-(du * du + dv * dv)) * inside
        arc = np.clip(np.cos(tb + 2.25), 0.0, 1.0) ** 8 * band(rb, CORE * 0.93, px * 1.2, px)
        self.specular = 0.16 * sheen + 0.22 * arc
        self.ribbon_inside = edge(CORE * 0.97 - rb, px)
        self.ribbon_axis = grid.axis[box[1]]
        self.ribbon_v = vb
