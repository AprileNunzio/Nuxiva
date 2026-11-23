import json
import logging
import os
import secrets
import threading
import time

from config import STATE_DIR
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from agenti.nodes import peer_envelope

log = logging.getLogger("nuxiva.peer")

SEED_FILE = STATE_DIR / "peer_identity.key"
DEFAULT_TTL = 6
_RAW = {"encoding": serialization.Encoding.Raw, "format": serialization.PublicFormat.Raw}


def _read_seed(path) -> bytes | None:
    try:
        text = path.read_text(encoding="ascii").strip()
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        log.error("Identità del server illeggibile, ne creo una nuova: %s", exc)
        return None
    if len(text) == 64 and all(c in "0123456789abcdef" for c in text):
        return bytes.fromhex(text)
    log.error("Identità del server non valida, ne creo una nuova")
    return None


def _write_seed(path, seed: bytes) -> None:
    tmp = path.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="ascii") as handle:
        handle.write(seed.hex())
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


class PeerIdentity:
    def __init__(self, path=SEED_FILE, clock=time.time) -> None:
        seed = _read_seed(path)
        if seed is None:
            seed = secrets.token_bytes(32)
            _write_seed(path, seed)
        self._seed = seed.hex()
        self._key = Ed25519PrivateKey.from_private_bytes(seed)
        self._public = self._key.public_key().public_bytes(**_RAW).hex()
        self._clock = clock
        self._lock = threading.Lock()
        self._last = 0

    @property
    def public_hex(self) -> str:
        return self._public

    def seed_hex(self) -> str:
        return self._seed

    def _next_seq(self, now_ms: int) -> int:
        with self._lock:
            self._last = max(self._last + 1, now_ms)
            return self._last

    def seal(self, message: dict, ttl: int = DEFAULT_TTL) -> dict:
        payload = json.dumps(message, separators=(",", ":"), ensure_ascii=True)
        now_ms = int(self._clock() * 1000)
        seq = self._next_seq(now_ms)
        signature = self._key.sign(peer_envelope.signed_bytes(self._public, seq, now_ms, payload))
        return {"from": self._public, "seq": seq, "ts": now_ms, "ttl": ttl, "payload": payload, "sig": signature.hex()}

    def seal_locate(self, addrs: list[str]) -> dict:
        peer_envelope.check_addrs(addrs)
        return self.seal({"type": "locate", "addrs": list(addrs)})


_identity: PeerIdentity | None = None
_guard = threading.Lock()


def identity() -> PeerIdentity:
    global _identity
    with _guard:
        if _identity is None:
            _identity = PeerIdentity()
        return _identity


def public_id() -> str:
    return identity().public_hex
