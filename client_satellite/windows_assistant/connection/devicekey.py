import hashlib
import re
import secrets

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

DOMAIN = "nuxiva-node-v1"
SEED_RE = re.compile(r"[0-9a-f]{64}")
_RAW = dict(encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)


class DeviceKeyError(ValueError):
    pass


class DeviceKey:
    def __init__(self, seed: bytes) -> None:
        if len(seed) != 32:
            raise DeviceKeyError("device_key_invalid")
        self._seed = seed
        self._key = Ed25519PrivateKey.from_private_bytes(seed)

    @classmethod
    def generate(cls) -> "DeviceKey":
        return cls(secrets.token_bytes(32))

    @classmethod
    def from_hex(cls, value: str) -> "DeviceKey":
        if not isinstance(value, str) or not SEED_RE.fullmatch(value):
            raise DeviceKeyError("device_key_invalid")
        return cls(bytes.fromhex(value))

    @classmethod
    def load(cls, value: str) -> "DeviceKey | None":
        return cls.from_hex(value) if value else None

    def seed_hex(self) -> str:
        return self._seed.hex()

    def public_bytes(self) -> bytes:
        return self._key.public_key().public_bytes(**_RAW)

    def public_hex(self) -> str:
        return self.public_bytes().hex()

    def pairing_code(self) -> str:
        head = hashlib.sha256(self.public_bytes()).digest()[:8]
        return f"{int.from_bytes(head, 'big') % 1_000_000:06d}"

    def sign_at(self, node: str, method: str, path: str, body: bytes, ts: int, nonce: str) -> dict:
        message = "\n".join((DOMAIN, node, method, path, str(ts), nonce, hashlib.sha256(body).hexdigest())).encode()
        return {"X-Nuxiva-Node": node, "X-Nuxiva-Ts": str(ts), "X-Nuxiva-Nonce": nonce,
                "X-Nuxiva-Sig": self._key.sign(message).hex()}

    def sign(self, node: str, method: str, path: str, body: bytes, now: int) -> dict:
        return self.sign_at(node, method, path, body, now, secrets.token_hex(16))
