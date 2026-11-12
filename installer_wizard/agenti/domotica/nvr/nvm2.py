import hashlib
import hmac
import json
import re
import struct

from agenti.nvr import xchacha

MAGIC = b"NVM2"
MAGIC_BLOB = b"NVB1"
CHUNK_SIZE = 65536
TAG_LEN = 16
FRAME_LEN = 4 + CHUNK_SIZE + TAG_LEN
MAX_HEADER = 4096
NONCE_LEN = 24
ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIERS = ("continuous", "event", "pinned")
AAD_DOMAIN = b"nuxiva.nvm2\x00"
FIELDS = ("v", "segment_id", "camera_id", "day", "recorded_at_ms", "duration_ms", "has_audio", "has_video",
          "tier", "plain_bytes", "chunk_count", "nonce")


class FormatError(ValueError):
    pass


def _hkdf(salt: bytes, ikm: bytes, info: bytes) -> bytes:
    prk = hmac.new(salt, ikm, hashlib.sha256).digest()
    return hmac.new(prk, info + b"\x01", hashlib.sha256).digest()


def segment_key(master: bytes, camera_id: str, day: str, segment_id: str) -> bytes:
    day_key = _hkdf(b"nuxiva.vault_media.salt.v1", master[:32], f"camera:{camera_id}|day:{day}".encode())
    return _hkdf(b"nuxiva.vault_media.segment.salt", day_key, segment_id.encode())


def chunk_count_for(plain_bytes: int) -> int:
    return max(1, -(-plain_bytes // CHUNK_SIZE))


def chunk_nonce(base: bytes, index: int) -> bytes:
    tail = bytes(a ^ b for a, b in zip(base[16:], struct.pack(">Q", index)))
    return base[:16] + tail


def chunk_aad(header_raw: bytes, index: int, last: bool) -> bytes:
    return hashlib.sha256(AAD_DOMAIN + header_raw).digest() + struct.pack(">QB", index, 1 if last else 0)


def validate(header: dict) -> dict:
    if not isinstance(header, dict) or list(header) != list(FIELDS):
        raise FormatError("nvr.header.invalid")
    ok = (header["v"] == 2 and all(isinstance(header[k], str) and ID.match(header[k]) for k in ("segment_id", "camera_id"))
          and isinstance(header["day"], str) and DAY.match(header["day"]) and header["tier"] in TIERS
          and all(type(header[k]) is int and header[k] >= 0 for k in ("recorded_at_ms", "duration_ms", "plain_bytes"))
          and all(type(header[k]) is bool for k in ("has_audio", "has_video"))
          and header["chunk_count"] == chunk_count_for(header["plain_bytes"])
          and isinstance(header["nonce"], str) and re.fullmatch(r"[0-9a-f]{48}", header["nonce"]))
    if not ok:
        raise FormatError("nvr.header.invalid")
    return header


def chunk_plain_len(header: dict, index: int) -> int:
    return max(0, min(CHUNK_SIZE, header["plain_bytes"] - index * CHUNK_SIZE))


def frame_offset(data_start: int, index: int) -> int:
    return data_start + index * FRAME_LEN


def frame_len(header: dict, index: int) -> int:
    return 4 + chunk_plain_len(header, index) + TAG_LEN


def py_seal(master: bytes, camera_id: str, day: str, segment_id: str, recorded_at_ms: int, duration_ms: int,
            has_audio: bool, has_video: bool, tier: str, nonce: bytes, raw: bytes) -> bytes:
    if len(nonce) != NONCE_LEN:
        raise FormatError("nvr.nonce.invalid")
    header = validate(dict(zip(FIELDS, (2, segment_id, camera_id, day, int(recorded_at_ms), int(duration_ms),
                                         bool(has_audio), bool(has_video), tier, len(raw), chunk_count_for(len(raw)),
                                         nonce.hex()))))
    header_raw = json.dumps(header, separators=(",", ":"), ensure_ascii=False).encode()
    key = segment_key(master, camera_id, day, segment_id)
    out = bytearray(MAGIC + struct.pack(">I", len(header_raw)) + header_raw)
    count = header["chunk_count"]
    for index in range(count):
        piece = raw[index * CHUNK_SIZE:(index + 1) * CHUNK_SIZE]
        sealed = xchacha.seal(key, chunk_nonce(nonce, index), piece, chunk_aad(header_raw, index, index == count - 1))
        out += struct.pack(">I", len(sealed)) + sealed
    return bytes(out)


def py_header(prefix: bytes) -> tuple[dict, bytes, int]:
    if prefix[:4] != MAGIC or len(prefix) < 8:
        raise FormatError("nvr.header.invalid")
    size = struct.unpack(">I", prefix[4:8])[0]
    if not 0 < size <= MAX_HEADER or len(prefix) < 8 + size:
        raise FormatError("nvr.header.invalid")
    raw = prefix[8:8 + size]
    try:
        header = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise FormatError("nvr.header.invalid") from exc
    return validate(header), raw, 8 + size


def py_open_chunk(master: bytes, prefix: bytes, index: int, frame: bytes) -> bytes:
    header, raw, _ = py_header(prefix)
    count = header["chunk_count"]
    if not 0 <= index < count:
        raise FormatError("nvr.chunk.range")
    size = struct.unpack(">I", frame[:4])[0] if len(frame) >= 4 else -1
    if size != chunk_plain_len(header, index) + TAG_LEN or len(frame) < 4 + size:
        raise FormatError("nvr.chunk.corrupt")
    key = segment_key(master, header["camera_id"], header["day"], header["segment_id"])
    nonce = chunk_nonce(bytes.fromhex(header["nonce"]), index)
    return xchacha.open_(key, nonce, frame[4:4 + size], chunk_aad(raw, index, index == count - 1))


def py_open(master: bytes, data: bytes) -> tuple[dict, bytes]:
    header, _, start = py_header(data)
    count = header["chunk_count"]
    if frame_offset(start, count - 1) + frame_len(header, count - 1) != len(data):
        raise FormatError("nvr.segment.corrupt")
    out = bytearray()
    for index in range(count):
        at = frame_offset(start, index)
        out += py_open_chunk(master, data, index, data[at:at + frame_len(header, index)])
    return header, bytes(out)


def _blob_key(master: bytes, context: str) -> bytes:
    return _hkdf(b"nuxiva.vault_media.blob.v1", master[:32], context.encode())


def py_seal_blob(master: bytes, context: str, nonce: bytes, plain: bytes) -> bytes:
    if not 0 < len(context) <= 128 or len(nonce) != NONCE_LEN:
        raise FormatError("nvr.blob.invalid")
    return MAGIC_BLOB + nonce + xchacha.seal(_blob_key(master, context), nonce, plain, context.encode())


def py_open_blob(master: bytes, context: str, blob: bytes) -> bytes:
    if blob[:4] != MAGIC_BLOB or len(blob) < 4 + NONCE_LEN + TAG_LEN:
        raise FormatError("nvr.blob.invalid")
    return xchacha.open_(_blob_key(master, context), blob[4:4 + NONCE_LEN], blob[4 + NONCE_LEN:], context.encode())


def chunk_span(plain_bytes: int, start: int, end_inclusive: int) -> tuple[int, int] | None:
    if plain_bytes <= 0 or start > end_inclusive or start >= plain_bytes:
        return None
    return start // CHUNK_SIZE, min(end_inclusive, plain_bytes - 1) // CHUNK_SIZE
