import json
import os
import tempfile
import time
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

import native_core


def write_private(path: Path, data: bytes) -> None:
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent)
    tmp = Path(temporary)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def _as_bytes(value) -> bytes:
    if isinstance(value, str):
        return value.encode("utf-8")
    if isinstance(value, (bytes, bytearray, memoryview)):
        return bytes(value)
    raise TypeError("Il dato da cifrare deve essere bytes")


class SealedCipher:

    def __init__(self, key: bytes) -> None:
        engine = native_core.symbol("RustFernet")
        self._rejected = native_core.symbol("SealRejected")
        if engine is None or self._rejected is None:
            native_core.python_fallback("sealed")
            self._rust = None
            self._python = Fernet(key)
        else:
            self._rust = engine(_as_bytes(key))
            self._python = None

    @staticmethod
    def generate_key() -> bytes:
        engine = native_core.symbol("RustFernet")
        if engine is None:
            native_core.python_fallback("sealed")
            return Fernet.generate_key()
        return bytes(engine.generate_key())

    def encrypt(self, data: bytes) -> bytes:
        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise TypeError("Il dato da cifrare deve essere bytes")
        if self._rust is None:
            return self._python.encrypt(bytes(data))
        return bytes(self._rust.encrypt(bytes(data), int(time.time())))

    def decrypt(self, token, ttl: int | None = None) -> bytes:
        raw = _as_bytes(token)
        if self._rust is None:
            return self._python.decrypt(raw, ttl)
        try:
            return bytes(self._rust.decrypt(raw, int(time.time()), ttl))
        except self._rejected as exc:
            raise InvalidToken from exc


class SealedFile:
    def __init__(self, data_path: Path, key_path: Path) -> None:
        self.data_path = data_path
        self.key_path = key_path

    def cipher(self) -> SealedCipher:
        return self._cipher()

    def _cipher(self) -> SealedCipher:
        if not self.key_path.exists():
            write_private(self.key_path, SealedCipher.generate_key())
        return SealedCipher(self.key_path.read_bytes())

    def load(self) -> dict:
        if not self.data_path.exists():
            return {}
        return json.loads(self._cipher().decrypt(self.data_path.read_bytes()))

    def save(self, data: dict) -> None:
        write_private(self.data_path, self._cipher().encrypt(json.dumps(data).encode()))
