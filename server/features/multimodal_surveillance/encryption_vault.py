import os
import base64
import hashlib
import hmac
from typing import Tuple

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ImportError:
    AESGCM = None

class ZeroTrustEncryptionVault:
    def __init__(self, master_secret: str = ""):
        self._master_secret = master_secret or os.getenv("NUXIVA_SURVEILLANCE_KEY", "nuxiva_zero_trust_default_key_2026_secured")
        self._key = hashlib.sha256(self._master_secret.encode("utf-8")).digest()
        self._aesgcm = AESGCM(self._key) if AESGCM else None

    def encrypt_bytes(self, plaintext: bytes) -> Tuple[bytes, bytes]:
        nonce = os.urandom(12)
        if self._aesgcm:
            ciphertext = self._aesgcm.encrypt(nonce, plaintext, None)
            return nonce, ciphertext
        keystream = hashlib.sha256(self._key + nonce).digest()
        repeated_key = (keystream * ((len(plaintext) // len(keystream)) + 1))[:len(plaintext)]
        ct = bytes(p ^ k for p, k in zip(plaintext, repeated_key))
        mac = hmac.new(self._key, nonce + ct, hashlib.sha256).digest()[:16]
        return nonce, ct + mac

    def decrypt_bytes(self, nonce: bytes, ciphertext: bytes) -> bytes:
        if self._aesgcm:
            return self._aesgcm.decrypt(nonce, ciphertext, None)
        mac = ciphertext[-16:]
        ct = ciphertext[:-16]
        expected_mac = hmac.new(self._key, nonce + ct, hashlib.sha256).digest()[:16]
        if not hmac.compare_digest(mac, expected_mac):
            raise ValueError("Integrity check failed")
        keystream = hashlib.sha256(self._key + nonce).digest()
        repeated_key = (keystream * ((len(ct) // len(keystream)) + 1))[:len(ct)]
        return bytes(c ^ k for c, k in zip(ct, repeated_key))

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
