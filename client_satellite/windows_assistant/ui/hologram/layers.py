import numpy as np

from ui.hologram import palette
from ui.hologram.geometry import CORE, TICK_BASE, TICK_REACH, Geometry
from ui.hologram.raster import TAU, Film, edge, gauss, wrap

TRAILS = 7
SWEEPS = ((0.0, 1.0, 1.9), (np.pi, 1.0, 1.9), (0.7, -0.62, 1.1))
RIBBON_WEIGHTS = ((1.0, 1.0), (0.7, 0.8), (0.5, 0.65))


def halo(film: Film, geo: Geometry, color: np.ndarray, strength: float, spread: float) -> None:
    film.glow(color, strength * (geo.halo_tight + (geo.halo_wide - geo.halo_tight) * spread))


def outer_ring(film: Film, geo: Geometry, color: np.ndarray, phase: float, strength: float) -> None:
    theta = geo.outer_theta
    dashes = np.clip((np.cos(theta * 36.0 - phase * 0.35) - 0.15) * 3.0, 0.0, 1.0)
    film.glow_flat(geo.outer_index, color, strength * geo.outer_line * dashes)
    marks = np.clip((np.cos(theta * 4.0 + phase * 0.12) - 0.985) * 70.0, 0.0, 1.0)
    film.glow_flat(geo.outer_index, palette.lift(color, 0.4), strength * 1.6 * geo.outer_wide * marks)


def sweeps(film: Film, geo: Geometry, color: np.ndarray, phase: float, strength: float, speed: float) -> None:
    light = np.zeros_like(geo.sweep_ring)
    tips = np.zeros_like(geo.sweep_ring)
    for offset, direction, span in SWEEPS:
        lag = wrap((offset + direction * phase * speed - geo.sweep_theta) * direction) % TAU
        light += np.where(lag < span, (1.0 - lag / span) ** 2, 0.0)
        tips += lag < 0.08
    film.glow_flat(geo.sweep_index, color, strength * light * (geo.sweep_ring + 0.35 * geo.sweep_soft))
    film.glow_flat(geo.sweep_index, palette.lift(color, 0.6), strength * tips * geo.sweep_ring)


def spectrum(film: Film, geo: Geometry, color: np.ndarray, ticks: np.ndarray, strength: float) -> None:
    level = ticks[geo.tick_slot]
    reach = TICK_BASE + 0.025 + TICK_REACH * level
    cover = geo.tick_cover * edge(reach - geo.tick_r, geo.grid.px)
    film.glow_flat(geo.tick_index, palette.lift(color, 0.15), strength * cover * (0.22 + 0.78 * level))
    film.glow_flat(geo.tick_index, color, strength * 0.25 * level * geo.tick_aura)


def core(film: Film, geo: Geometry, color: np.ndarray, breath: float, energy: float) -> None:
    box = geo.core_box
    film.over_box(box, geo.core_base, geo.core_inside * 0.94)
    heart = gauss(geo.core_r, CORE * (0.42 + 0.18 * energy)) * geo.core_inside
    light = 0.55 * geo.core_fresnel * (0.75 + 0.25 * breath) + (0.10 + 0.16 * breath + 0.18 * energy) * heart
    film.glow_box(box, color, light + 0.35 * geo.core_rim_glow)
    film.glow_box(box, palette.lift(color, 0.5), 0.9 * geo.core_rim)


def specular(film: Film, geo: Geometry) -> None:
    film.glow_box(geo.core_box, palette.WHITE, geo.specular)


def ribbons(film: Film, geo: Geometry, color: np.ndarray, curves: list, reveal: float, gain: float) -> None:
    px = geo.grid.px
    reach, height = CORE * 0.84, CORE * 0.62 * gain
    axis = geo.ribbon_axis
    mask = geo.ribbon_inside * edge(reach - np.abs(axis), px * 2.0)[None, :] * reveal
    line_total = np.zeros_like(mask)
    aura_total = np.zeros_like(mask)
    for curve, (bright, thickness) in zip(curves, RIBBON_WEIGHTS):
        xs = np.linspace(-reach, reach, len(curve), dtype=np.float32)
        ys = np.interp(axis, xs, np.asarray(curve, dtype=np.float32) * height, left=0.0, right=0.0)
        slope = np.gradient(ys, axis)
        distance = np.abs(geo.ribbon_v - ys[None, :]) / np.sqrt(1.0 + slope * slope)[None, :]
        line_total += bright * edge(px * thickness - distance, px)
        aura_total += 0.45 * bright * gauss(distance, px * 3.2)
    film.glow_box(geo.core_box, palette.lift(color, 0.3), line_total * mask)
    film.glow_box(geo.core_box, color, aura_total * mask)


def comets(film: Film, geo: Geometry, color: np.ndarray, phase: float, strength: float) -> None:
    radius, px = CORE * 0.56, geo.grid.px
    for head in range(3):
        for trail in range(TRAILS):
            angle = phase * 2.4 + head * TAU / 3.0 - trail * 0.11
            fade = (1.0 - trail / TRAILS) ** 1.6
            film.spot(geo.grid, palette.lift(color, 0.3 * fade), radius * np.cos(angle), radius * np.sin(angle),
                      px * (3.4 - 1.8 * trail / TRAILS), strength * fade)


def motes(film: Film, geo: Geometry, color: np.ndarray, seeds: np.ndarray, phase: float, strength: float) -> None:
    px = geo.grid.px
    for radius, angle, speed, size, twinkle in seeds:
        a = angle + phase * speed
        light = 0.35 + 0.65 * (0.5 + 0.5 * np.sin(phase * 1.3 + twinkle)) ** 2
        film.spot(geo.grid, color, radius * np.cos(a), radius * np.sin(a), px * size, strength * light)
