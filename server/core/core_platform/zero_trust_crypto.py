import hmac
import json
from dataclasses import dataclass
from typing import Any, Callable

from server.core.core_platform.errors import CortexFailure, fail
from server.core.core_platform.native_bridge import call_native
from server.core.core_platform.result import Ok, Result

SEAL_CONTEXT_PREFIX = b"nuxiva.cortex.seal."
SIGN_CONTEXT_PREFIX = b"nuxiva.cortex.sign."
MIN_MASTER_SECRET_CHARS = 32


@dataclass(frozen=True, slots=True)
class SignedBlob:
    payload: bytes
    signature: bytes
    public_key: bytes


class ZeroTrustVault:
    def __init__(self, master_secret: Callable[[], str]) -> None:
        self._master_secret = master_secret

    def _master(self) -> Result[bytes, CortexFailure]:
        secret = self._master_secret().encode("utf-8")
        if len(secret) < MIN_MASTER_SECRET_CHARS:
            return fail("platform.vault.weak_secret")
        return Ok(secret)

    def _derive(self, prefix: bytes, purpose: str) -> Result[bytes, CortexFailure]:
        master = self._master()
        if not master.is_ok:
            return master
        context = prefix + purpose.encode("utf-8")
        return call_native(lambda native: native.cortex_derive_key(master.value, context))

    def seal_json(self, purpose: str, payload: Any, associated: bytes = b"") -> Result[bytes, CortexFailure]:
        key = self._derive(SEAL_CONTEXT_PREFIX, purpose)
        if not key.is_ok:
            return key
        plaintext = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        return call_native(lambda native: native.cortex_seal(key.value, associated, plaintext))

    def seal_bytes(self, purpose: str, plaintext: bytes, associated: bytes = b"") -> Result[bytes, CortexFailure]:
        key = self._derive(SEAL_CONTEXT_PREFIX, purpose)
        if not key.is_ok:
            return key
        return call_native(lambda native: native.cortex_seal(key.value, associated, plaintext))

    def open_bytes(self, purpose: str, sealed: bytes, associated: bytes = b"") -> Result[bytes, CortexFailure]:
        key = self._derive(SEAL_CONTEXT_PREFIX, purpose)
        if not key.is_ok:
            return key
        return call_native(lambda native: native.cortex_open(key.value, associated, sealed))

    def open_json(self, purpose: str, sealed: bytes, associated: bytes = b"") -> Result[Any, CortexFailure]:
        opened = self.open_bytes(purpose, sealed, associated)
        return opened.map(json.loads) if opened.is_ok else opened

    def sign(self, purpose: str, payload: bytes) -> Result[SignedBlob, CortexFailure]:
        seed = self._derive(SIGN_CONTEXT_PREFIX, purpose)
        if not seed.is_ok:
            return seed

        def action(native: Any) -> SignedBlob:
            signer = native.RustSigner(seed.value)
            return SignedBlob(payload, signer.sign(payload), signer.public_key())

        return call_native(action)

    def verify(self, purpose: str, blob: SignedBlob) -> Result[bool, CortexFailure]:
        seed = self._derive(SIGN_CONTEXT_PREFIX, purpose)
        if not seed.is_ok:
            return seed

        def action(native: Any) -> bool:
            trusted = native.RustSigner(seed.value).public_key()
            if not hmac.compare_digest(trusted, blob.public_key):
                return False
            return native.cortex_verify(trusted, blob.payload, blob.signature)

        return call_native(action)
