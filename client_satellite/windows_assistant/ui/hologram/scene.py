import numpy as np

from ui.hologram import layers, palette
from ui.hologram.geometry import Geometry
from ui.hologram.motion import Motion
from ui.hologram.raster import Film, Grid

POINTS = 72
MOTES = 18
SEED = 0x4E58
AMBIENT_GAIN = 1.6


def _seeds() -> np.ndarray:
    rng = np.random.default_rng(SEED)
    return np.column_stack((rng.uniform(0.5, 0.94, MOTES), rng.uniform(0.0, 2.0 * np.pi, MOTES),
                            rng.uniform(-0.08, 0.08, MOTES), rng.uniform(0.9, 1.8, MOTES),
                            rng.uniform(0.0, 2.0 * np.pi, MOTES))).astype(np.float32)


class Scene:
    def __init__(self, size: int) -> None:
        self.grid = Grid(int(size))
        self.geo = Geometry(self.grid)
        self.seeds = _seeds()

    @property
    def size(self) -> int:
        return self.grid.size

    def compose(self, motion: Motion) -> Film:
        geo, color, phase = self.geo, motion.color.astype(np.float32), motion.phase
        amp, energy, breath = motion.amplitude, motion.energy, motion.pulse()
        dim = 0.45 if motion.state == "offline" else 1.0
        film = Film(self.grid.size)
        layers.halo(film, geo, color, dim * (0.16 + 0.12 * breath + 0.22 * energy + 0.35 * amp), amp)
        layers.motes(film, geo, palette.lift(color, 0.25), self.seeds, phase, dim * (0.18 + 0.22 * energy))
        layers.outer_ring(film, geo, color, phase, dim * (0.22 + 0.18 * energy))
        layers.spectrum(film, geo, color, motion.ticks, dim * (0.55 + 0.45 * energy))
        speed = 1.4 if motion.state == "thinking" else 0.25 + 0.55 * energy
        layers.sweeps(film, geo, color, phase, dim * (0.28 + 0.5 * energy), speed)
        layers.core(film, geo, color, breath, energy)
        if motion.state == "thinking":
            layers.comets(film, geo, color, phase, 0.95)
        if motion.reveal > 0.02:
            gain = 1.0 + AMBIENT_GAIN * (1.0 - amp)
            layers.ribbons(film, geo, color, motion.flow.ribbons(phase, POINTS), motion.reveal, gain)
        layers.specular(film, geo)
        return film

    def render(self, motion: Motion) -> bytes:
        return self.compose(motion).pack(motion.opacity)
