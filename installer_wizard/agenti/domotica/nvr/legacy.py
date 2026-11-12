import hashlib
import hmac
import json
import struct

from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

from agenti.nvr import xchacha

MAGIC_V1 = b"NVM1"


def _hkdf(salt: bytes, ikm: bytes, info: bytes) -> bytes:
    prk = hmac.new(salt, ikm, hashlib.sha256).digest()
    return hmac.new(prk, info + b"\x01", hashlib.sha256).digest()[:32]


def _key(master: bytes, camera_id: str, day: str, segment_id: str) -> bytes:
    day_key = _hkdf(b"nuxiva.vault_media.salt.v1", master[:32], f"camera:{camera_id}|day:{day}".encode())
    return _hkdf(b"nuxiva.vault_media.segment.salt", day_key, segment_id.encode())


def _frames(data: bytes, offset: int):
    while offset < len(data):
        size = struct.unpack(">I", data[offset:offset + 4])[0]
        offset += 4
        yield data[offset:offset + size]
        offset += size


def open_v1(master: bytes, camera_id: str, segment_id: str, data: bytes, fallback_day: str) -> bytes:
    if len(data) < 8 or data[:4] != MAGIC_V1:
        raise ValueError("nvr.legacy.invalid")
    meta_len = struct.unpack(">I", data[4:8])[0]
    meta = json.loads(data[8:8 + meta_len].decode("utf-8"))
    key = _key(master, camera_id, str(meta.get("day") or fallback_day), segment_id)
    out = bytearray()
    base = meta.get("base_nonce")
    if isinstance(base, list) and len(base) == 24:
        nonce = bytes(base)
        for index, frame in enumerate(_frames(data, 8 + meta_len)):
            tail = bytes(a ^ b for a, b in zip(nonce[16:], struct.pack(">Q", index)))
            out += xchacha.open_(key, nonce[:16] + tail, frame)
        return bytes(out)
    cipher = ChaCha20Poly1305(key)
    for frame in _frames(data, 8 + meta_len):
        out += cipher.decrypt(frame[:12], frame[12:], None)
    return bytes(out)
