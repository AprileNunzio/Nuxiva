import hashlib
import math

DIM = 256
WORD = 10
GRAM = 4
PAIR = 6
PPM = 1_000_000
PERMILLE = 1000


def _fold(c: str) -> str:
    table = {
        "àáâãäå": "a",
        "èéêë": "e",
        "ìíîï": "i",
        "òóôõöø": "o",
        "ùúûü": "u",
        "ç": "c",
        "ñ": "n",
        "ýÿ": "y",
    }
    for group, base in table.items():
        if c in group:
            return base
    return c


def normalize(text: str) -> str:
    out: list[str] = []
    gap = True
    for ch in text:
        for c in ch.lower():
            c = _fold(c)
            if c.isalnum():
                out.append(c)
                gap = False
            elif not gap:
                out.append(" ")
                gap = True
    if out and out[-1] == " ":
        out.pop()
    return "".join(out)


def tokens(text: str) -> list[str]:
    return [t for t in normalize(text).split(" ") if t]


def hex_digest(*parts: str) -> str:
    hasher = hashlib.sha256()
    for part in parts:
        hasher.update(part.encode("utf-8"))
        hasher.update(b"\x00")
    return hasher.digest()[:16].hex()


def _feature(text: str) -> tuple[int, int]:
    value = int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "big")
    return value % DIM, -1 if (value >> 32) & 1 else 1


def embed(text: str) -> tuple[tuple[tuple[int, int], ...], int]:
    words = tokens(text)
    cells: dict[int, int] = {}

    def add(feature: str, weight: int) -> None:
        index, sign = _feature(feature)
        cells[index] = cells.get(index, 0) + sign * weight

    for word in words:
        add("w:" + word, WORD)
        padded = "^" + word + "$"
        for i in range(len(padded) - 2):
            add("g:" + padded[i : i + 3], GRAM)
    for a, b in zip(words, words[1:]):
        add(f"b:{a} {b}", PAIR)
    sparse = tuple(sorted((i, v) for i, v in cells.items() if v != 0))
    return sparse, sum(v * v for _, v in sparse)


def cosine_permille(a: tuple, b: tuple) -> int:
    (cells_a, norm_a), (cells_b, norm_b) = a, b
    if norm_a == 0 or norm_b == 0:
        return 0
    other = dict(cells_b)
    dot = sum(v * other.get(i, 0) for i, v in cells_a)
    if dot <= 0:
        return 0
    ratio = float(dot) / (math.sqrt(float(norm_a)) * math.sqrt(float(norm_b)))
    return min(int(math.floor(ratio * 1000.0 + 0.5)), 1000)


def noisy_or(a: int, b: int) -> int:
    miss_a = PERMILLE - min(a, PERMILLE)
    miss_b = PERMILLE - min(b, PERMILLE)
    return PERMILLE - miss_a * miss_b // PERMILLE


def scale(value: int, factor: int) -> int:
    return value * factor // PERMILLE


def _pow2_neg_ppm(x: int) -> int:
    x2 = x * x // PPM
    x3 = x2 * x // PPM
    x4 = x3 * x // PPM
    x5 = x4 * x // PPM
    plus = PPM + 240_227 * x2 // PPM + 9_618 * x4 // PPM
    minus = (693_147 * x + 55_504 * x3 + 1_333 * x5) // PPM
    return max(0, min(plus - minus, PPM))


def halve(value: int, elapsed_ms: int, half_ms: int) -> int:
    if half_ms == 0:
        return value
    whole, rem = divmod(elapsed_ms, half_ms)
    base = value >> min(whole, 31)
    return base * _pow2_neg_ppm(rem * PPM // half_ms) // PPM
