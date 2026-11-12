import struct

SIZE = 64
PALETTE = {
    "creativita": (168, 123, 255), "percezione": (76, 230, 255), "cognizione": (255, 209, 102),
    "sicurezza": (255, 99, 99), "domotica": (112, 224, 0), "infrastruttura": (100, 160, 255),
    "multimedia": (255, 107, 229), "comunicazione": (94, 242, 255), "conoscenza": (255, 159, 28),
    "salute": (46, 196, 182), "sport": (56, 176, 0), "scienza": (131, 56, 236), "informatica": (72, 191, 227),
}


def crc32(data: bytes) -> int:
    crc = 0xFFFFFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            mask = (-(crc & 1)) & 0xFFFFFFFF
            crc = (crc >> 1) ^ (0xEDB88320 & mask)
    return (~crc) & 0xFFFFFFFF


def adler32(data: bytes) -> int:
    a, b = 1, 0
    for x in data:
        a = (a + x) % 65521
        b = (b + a) % 65521
    return (b << 16) | a


def _chunk(kind: bytes, data: bytes) -> bytes:
    body = kind + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", crc32(body))


def _zlib_stored(raw: bytes) -> bytes:
    out = bytearray(b"\x78\x01")
    blocks = [raw[i:i + 65535] for i in range(0, len(raw), 65535)] or [b""]
    for i, block in enumerate(blocks):
        out.append(1 if i == len(blocks) - 1 else 0)
        out += struct.pack("<HH", len(block), (~len(block)) & 0xFFFF)
        out += block
    out += struct.pack(">I", adler32(raw))
    return bytes(out)


def _seed(ident: str) -> int:
    h = 0x811C9DC5
    for b in ident.encode("utf-8"):
        h = ((h ^ b) * 0x01000193) & 0xFFFFFFFF
    return h


def _mix(base: int, toward: int, weight: int) -> int:
    w = min(weight, 255)
    return min((base * (255 - w) + toward * w) // 255, 255)


def _pixel(px: int, py: int, rgb: tuple, spot: tuple) -> bytes:
    center = SIZE // 2
    dx, dy = px - center, py - center
    d2 = dx * dx + dy * dy
    outer, edge = 28 * 28, 26 * 26
    if d2 > outer:
        return b"\0\0\0\0"
    alpha = min(((outer - d2) * 255) // max(outer - edge, 1), 255) if d2 > edge else 255
    sx, sy = px - spot[0], py - spot[1]
    s2 = sx * sx + sy * sy
    glow = max(200 - s2 // 3, 0)
    shade = min(d2 // 8, 120)
    return bytes([_mix(_mix(v, 255, glow), 0, shade) for v in rgb] + [alpha])


def render(category: str, ident: str) -> bytes:
    rgb = PALETTE.get(category, (155, 231, 255))
    h = _seed(ident)
    spot = (h % 12 + 20, (h >> 8) % 10 + 18)
    raw = bytearray()
    for y in range(SIZE):
        raw.append(0)
        for x in range(SIZE):
            raw += _pixel(x, y, rgb, spot)
    ihdr = struct.pack(">II", SIZE, SIZE) + bytes([8, 6, 0, 0, 0])
    return (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", _zlib_stored(bytes(raw)))
            + _chunk(b"IEND", b""))
