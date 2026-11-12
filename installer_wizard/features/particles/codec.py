import json
import math
import re
import struct

from features.stage import native

MAGIC = b"NXPC"
VERSION = 1
HEADER = 12
MIN_POINTS = 256
MAX_POINTS = 40_000
MAX_PARTS = 24
MAX_BLOB_POINTS = 65_536
FLAG_COLORS = 1
QUANT = 32_767.0
SHAPES = ("sphere", "box", "cylinder", "cone", "torus", "helix", "plane")
COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
MASK = (1 << 64) - 1


class ParticleError(ValueError):
    pass


def _triple(value, default: float, lo: float, hi: float, what: str) -> list[float]:
    if value is None:
        return [default] * 3
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ParticleError(f"{what} must have three numbers")
    out = []
    for v in value:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not lo <= v <= hi:
            raise ParticleError(f"{what} out of range")
        out.append(float(v))
    return out


def validate(spec) -> dict:
    if not isinstance(spec, dict) or not isinstance(spec.get("parts"), list):
        raise ParticleError("spec must contain parts")
    parts = spec["parts"]
    if not 1 <= len(parts) <= MAX_PARTS:
        raise ParticleError("parts must be between 1 and 24")
    clean = []
    for part in parts:
        if not isinstance(part, dict) or part.get("shape") not in SHAPES:
            raise ParticleError("unknown shape")
        color = part.get("color", "#9be7ff")
        if not isinstance(color, str) or not COLOR.match(color):
            raise ParticleError("color must be #rrggbb")
        weight = part.get("weight", 1.0)
        if isinstance(weight, bool) or not isinstance(weight, (int, float)) or not math.isfinite(weight) or not 0.05 <= weight <= 10:
            raise ParticleError("weight out of range")
        clean.append({"shape": part["shape"], "size": _triple(part.get("size"), 1.0, 0.01, 10.0, "size"),
                      "at": _triple(part.get("at"), 0.0, -10.0, 10.0, "position"),
                      "rot": _triple(part.get("rot"), 0.0, -360.0, 360.0, "rotation"),
                      "color": color.lower(), "weight": float(weight)})
    return {"parts": clean}


class _Rng:
    def __init__(self, seed: int) -> None:
        self.state = seed & MASK

    def next(self) -> float:
        self.state = (self.state + 0x9E3779B97F4A7C15) & MASK
        z = self.state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK
        z ^= z >> 31
        return float(z >> 11) / 9_007_199_254_740_992.0


def _shares(parts: list[dict], count: int) -> list[int]:
    mass = [p["weight"] * (p["size"][0] * p["size"][1] + p["size"][1] * p["size"][2] + p["size"][2] * p["size"][0]) for p in parts]
    total = sum(mass)
    exact = [m / total * count for m in mass]
    base = [math.floor(e) for e in exact]
    order = sorted(range(len(parts)), key=lambda i: (-(exact[i] - math.floor(exact[i])), i))
    for i in order[:max(0, count - sum(base))]:
        base[i] += 1
    return base


def _point(shape: str, rng: _Rng) -> tuple[float, float, float]:
    ua, ub, uc = rng.next(), rng.next(), rng.next()
    tau = math.tau
    if shape == "sphere":
        theta = tau * ua
        height = 2.0 * ub - 1.0
        radius = math.sqrt(max(0.0, 1.0 - height * height))
        return radius * math.cos(theta), radius * math.sin(theta), height
    if shape == "box":
        su, sv = 2.0 * ub - 1.0, 2.0 * uc - 1.0
        face = math.floor(ua * 6.0)
        return ((1.0, su, sv), (-1.0, su, sv), (su, 1.0, sv), (su, -1.0, sv), (su, sv, 1.0), (su, sv, -1.0))[min(int(face), 5)]
    if shape == "cylinder":
        theta = tau * ub
        if ua < 0.7:
            return math.cos(theta), 2.0 * uc - 1.0, math.sin(theta)
        radius = math.sqrt(uc)
        return radius * math.cos(theta), 1.0 if ua < 0.85 else -1.0, radius * math.sin(theta)
    if shape == "cone":
        theta = tau * ub
        slope = math.sqrt(ua)
        return slope * math.cos(theta), 1.0 - 2.0 * slope, slope * math.sin(theta)
    if shape == "torus":
        theta, phi = tau * ua, tau * ub
        ring = 1.0 + 0.35 * math.cos(phi)
        return ring * math.cos(theta) / 1.35, 0.35 * math.sin(phi) / 1.35, ring * math.sin(theta) / 1.35
    if shape == "helix":
        turn = 3.0 * tau * ua
        return math.cos(turn) + (ub - 0.5) * 0.08, 2.0 * ua - 1.0, math.sin(turn) + (uc - 0.5) * 0.08
    return 2.0 * ua - 1.0, (uc - 0.5) * 0.02, 2.0 * ub - 1.0


def _rotate(p, deg):
    rx, ry, rz = (math.radians(d) for d in deg)
    x, y, z = p
    y, z = y * math.cos(rx) - z * math.sin(rx), y * math.sin(rx) + z * math.cos(rx)
    x, z = x * math.cos(ry) + z * math.sin(ry), -x * math.sin(ry) + z * math.cos(ry)
    x, y = x * math.cos(rz) - y * math.sin(rz), x * math.sin(rz) + y * math.cos(rz)
    return x, y, z


def _quantize(v: float) -> int:
    scaled = max(-QUANT, min(QUANT, v * QUANT))
    return int(scaled + math.copysign(0.5, scaled))


def _shade(channel: int, factor: float) -> int:
    v = max(0.0, min(255.0, channel * factor))
    return min(255, math.floor(v + 0.5))


def encode(positions: list, colors: list) -> bytes:
    colored = bool(colors) and len(colors) == len(positions)
    head = MAGIC + bytes([VERSION, FLAG_COLORS if colored else 0, 0, 0]) + struct.pack("<I", len(positions))
    body = struct.pack(f"<{len(positions) * 3}h", *(v for p in positions for v in p))
    return head + body + (bytes(c for col in colors for c in col) if colored else b"")


def sample_python(spec: dict, count: int, seed: int) -> bytes:
    if not MIN_POINTS <= count <= MAX_POINTS:
        raise ParticleError("count out of range")
    parts = validate(spec)["parts"]
    rng = _Rng(seed)
    raw, tint = [], []
    for part, n in zip(parts, _shares(parts, count)):
        color = [int(part["color"][i:i + 2], 16) for i in (1, 3, 5)]
        sx, sy, sz = part["size"]
        ax, ay, az = part["at"]
        for _ in range(n):
            x, y, z = _point(part["shape"], rng)
            px, py, pz = _rotate((x * sx, y * sy, z * sz), part["rot"])
            raw.append((px + ax, py + ay, pz + az))
            factor = 0.85 + 0.3 * rng.next()
            tint.append([_shade(c, factor) for c in color])
    reach = max((abs(v) for p in raw for v in p), default=0.0)
    scale = 1.0 / reach if reach > 0 else 1.0
    return encode([[_quantize(v * scale) for v in p] for p in raw], tint)


def sample(spec: dict, count: int = 12_000, seed: int = 1) -> bytes:
    clean = validate(spec)
    seed &= MASK
    if native.lib is not None:
        try:
            return bytes(native.lib.particles_sample(json.dumps(clean, separators=(",", ":")), count, seed))
        except ValueError as exc:
            raise ParticleError(str(exc)) from exc
    return sample_python(clean, count, seed)


def count(blob: bytes) -> int:
    if len(blob) < HEADER or blob[:4] != MAGIC or blob[4] != VERSION:
        raise ParticleError("bad header")
    flags = blob[5]
    if flags & ~FLAG_COLORS or blob[6:8] != b"\x00\x00":
        raise ParticleError("unknown flags")
    n = struct.unpack("<I", blob[8:12])[0]
    if n > MAX_BLOB_POINTS:
        raise ParticleError("too many points")
    if len(blob) != HEADER + n * (9 if flags & FLAG_COLORS else 6):
        raise ParticleError("length mismatch")
    return n
