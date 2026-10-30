import os

from server.core.core_platform.errors import CortexFailure, fail
from server.core.core_platform.native_bridge import call_native, load_native
from server.core.core_platform.result import Err, Ok, Result

KEY_LEN = 32
NONCE_LEN = 12
TAG_LEN = 16

try:
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
except ImportError:
    AESGCM = None


def _native_ready() -> bool:
    return load_native().is_ok


def _software_ready() -> Result[None, CortexFailure]:
    return Ok(None) if AESGCM is not None else fail("platform.native.unavailable")


def _hkdf_sha256(master: bytes, context: bytes) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=KEY_LEN, salt=None, info=context).derive(master)


def derive_key(master: bytes, context: bytes) -> Result[bytes, CortexFailure]:
    if not master:
        return fail("cortex.crypto.invalid_key_length")
    if _native_ready():
        return call_native(lambda native: bytes(native.cortex_derive_key(master, context)))
    ready = _software_ready()
    return ready.map(lambda _: _hkdf_sha256(master, context)) if ready.is_ok else ready


def seal(key: bytes, associated: bytes, plaintext: bytes) -> Result[bytes, CortexFailure]:
    if len(key) != KEY_LEN:
        return fail("cortex.crypto.invalid_key_length")
    if _native_ready():
        return call_native(lambda native: bytes(native.cortex_seal(key, associated, plaintext)))
    ready = _software_ready()
    if not ready.is_ok:
        return ready
    nonce = os.urandom(NONCE_LEN)
    return Ok(nonce + AESGCM(key).encrypt(nonce, plaintext, associated))


def open_sealed(key: bytes, associated: bytes, sealed: bytes) -> Result[bytes, CortexFailure]:
    if len(key) != KEY_LEN:
        return fail("cortex.crypto.invalid_key_length")
    if len(sealed) < NONCE_LEN + TAG_LEN:
        return fail("cortex.crypto.malformed_ciphertext")
    if _native_ready():
        return call_native(lambda native: bytes(native.cortex_open(key, associated, sealed)))
    ready = _software_ready()
    if not ready.is_ok:
        return ready
    try:
        return Ok(AESGCM(key).decrypt(sealed[:NONCE_LEN], sealed[NONCE_LEN:], associated))
    except InvalidTag:
        return Err(CortexFailure("cortex.crypto.decryption_failed"))
