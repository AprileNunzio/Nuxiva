import math

ATTACK = 0.55
RELEASE = 0.12
GAIN = 12.0
CURVE = 0.6
FLOOR = 0.12
POINTS = 33
LAYERS = ((1.0, 1.6, 1.0), (0.7, 2.3, -1.3), (0.45, 3.1, 1.9))


def normalize(level: float, gain: float = GAIN) -> float:
    return min(1.0, max(0.0, float(level) * gain) ** CURVE)


class Flow:
    def __init__(self) -> None:
        self.amplitude = 0.0

    def feed(self, level: float) -> float:
        target = normalize(level)
        rate = ATTACK if target > self.amplitude else RELEASE
        self.amplitude += (target - self.amplitude) * rate
        return self.amplitude

    def ribbons(self, phase: float, points: int = POINTS) -> list[list[float]]:
        amp = FLOOR + (1.0 - FLOOR) * self.amplitude
        out = []
        for weight, frequency, speed in LAYERS:
            ys = []
            for i in range(points):
                u = i / (points - 1)
                taper = math.sin(math.pi * u) ** 1.5
                ys.append(weight * amp * taper * math.sin(frequency * 2 * math.pi * u + phase * speed))
            out.append(ys)
        return out
