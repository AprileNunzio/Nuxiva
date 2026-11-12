import struct

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

KEY_LEN = 32
NONCE_LEN = 24
_MASK = 0xFFFFFFFF
_SIGMA = (0x61707865, 0x3320646E, 0x79622D32, 0x6B206574)


def _rotl(value: int, shift: int) -> int:
    return ((value << shift) & _MASK) | (value >> (32 - shift))


def _quarter(s: list, a: int, b: int, c: int, d: int) -> None:
    s[a] = (s[a] + s[b]) & _MASK
    s[d] = _rotl(s[d] ^ s[a], 16)
    s[c] = (s[c] + s[d]) & _MASK
    s[b] = _rotl(s[b] ^ s[c], 12)
    s[a] = (s[a] + s[b]) & _MASK
    s[d] = _rotl(s[d] ^ s[a], 8)
    s[c] = (s[c] + s[d]) & _MASK
    s[b] = _rotl(s[b] ^ s[c], 7)


def hchacha20(key: bytes, nonce16: bytes) -> bytes:
    if len(key) != KEY_LEN or len(nonce16) != 16:
        raise ValueError("xchacha.input.invalid")
    s = [*_SIGMA, *struct.unpack("<8I", key), *struct.unpack("<4I", nonce16)]
    for _ in range(10):
        _quarter(s, 0, 4, 8, 12)
        _quarter(s, 1, 5, 9, 13)
        _quarter(s, 2, 6, 10, 14)
        _quarter(s, 3, 7, 11, 15)
        _quarter(s, 0, 5, 10, 15)
        _quarter(s, 1, 6, 11, 12)
        _quarter(s, 2, 7, 8, 13)
        _quarter(s, 3, 4, 9, 14)
    return struct.pack("<8I", *s[0:4], *s[12:16])


def _split(key: bytes, nonce: bytes) -> tuple[ChaCha20Poly1305, bytes]:
    if len(nonce) != NONCE_LEN:
        raise ValueError("xchacha.nonce.invalid")
    return ChaCha20Poly1305(hchacha20(key, nonce[:16])), b"\x00\x00\x00\x00" + nonce[16:]


def seal(key: bytes, nonce: bytes, plain: bytes, aad: bytes = b"") -> bytes:
    engine, inner = _split(key, nonce)
    return engine.encrypt(inner, plain, aad or None)


def open_(key: bytes, nonce: bytes, sealed: bytes, aad: bytes = b"") -> bytes:
    engine, inner = _split(key, nonce)
    try:
        return engine.decrypt(inner, sealed, aad or None)
    except InvalidTag:
        raise ValueError("chunk authentication failed or corrupted") from None
