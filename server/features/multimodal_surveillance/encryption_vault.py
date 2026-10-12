import os
import base64
import hashlib
from typing import Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

class ZeroTrustEncryptionVault:
    def __init__(self, master_secret: str = ""):
        self._master_secret = master_secret or os.getenv("NUXIVA_SURVEILLANCE_KEY", "nuxiva_zero_trust_default_key_2026_secured")
        self._key = hashlib.sha256(self._master_secret.encode("utf-8")).digest()
        self._aesgcm = AESGCM(self._key)

    def encrypt_bytes(self, plaintext: bytes) -> Tuple[bytes, bytes]:
        nonce = os.urandom(12)
        ciphertext = self._aesgcm.encrypt(nonce, plaintext, None)
        return nonce, ciphertext

    def decrypt_bytes(self, nonce: bytes, ciphertext: bytes) -> bytes:
        return self._aesgcm.decrypt(nonce, ciphertext, None)

    def encrypt_string(self, text: str) -> str:
        nonce, ct = self.encrypt_bytes(text.encode("utf-8"))
        combined = nonce + ct
        return base64.b64encode(combined).decode("ascii")

    def decrypt_string(self, encrypted_payload_b64: str) -> str:
        raw = base64.b64decode(encrypted_payload_b64.encode("ascii"))
        nonce = raw[:12]
        ct = raw[12:]
        decrypted = self.decrypt_bytes(nonce, ct)
        return decrypted.decode("utf-8")

    def compute_sha256_hash(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

vault = ZeroTrustEncryptionVault()
