import base64
import hashlib
import os
from typing import Tuple

from server.config.env import settings
from server.core.core_platform import aead
from server.core.core_platform.errors import CortexFailure

VAULT_CONTEXT = b"nuxiva.surveillance.vault.v1"
VAULT_AAD = b"nuxiva.surveillance"
MIN_SECRET_CHARS = 32


def _resolve_secret(explicit: str) -> str:
    return explicit or os.getenv("NUXIVA_SURVEILLANCE_KEY", "") or settings.NUXIVA_SECRET_KEY


class ZeroTrustEncryptionVault:
    def __init__(self, master_secret: str = "") -> None:
        secret = _resolve_secret(master_secret).encode("utf-8")
        if len(secret) < MIN_SECRET_CHARS or not secret.strip(b"0"):
            raise CortexFailure("platform.vault.weak_secret")
        self._key = aead.derive_key(secret, VAULT_CONTEXT).unwrap()

    def encrypt_bytes(self, plaintext: bytes) -> Tuple[bytes, bytes]:
        sealed = aead.seal(self._key, VAULT_AAD, plaintext).unwrap()
        return sealed[:aead.NONCE_LEN], sealed[aead.NONCE_LEN:]

    def decrypt_bytes(self, nonce: bytes, ciphertext: bytes) -> bytes:
        if len(nonce) != aead.NONCE_LEN:
            raise CortexFailure("cortex.crypto.malformed_ciphertext")
        return aead.open_sealed(self._key, VAULT_AAD, nonce + ciphertext).unwrap()

    def encrypt_string(self, text: str) -> str:
        nonce, ct = self.encrypt_bytes(text.encode("utf-8"))
        return base64.b64encode(nonce + ct).decode("ascii")

    def decrypt_string(self, encrypted_payload_b64: str) -> str:
        raw = base64.b64decode(encrypted_payload_b64.encode("ascii"), validate=True)
        return self.decrypt_bytes(raw[:aead.NONCE_LEN], raw[aead.NONCE_LEN:]).decode("utf-8")

    def compute_sha256_hash(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()


vault = ZeroTrustEncryptionVault()
