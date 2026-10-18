import json
from pathlib import Path

from cryptography.fernet import InvalidToken
from sealed import SealedFile


class MemoryStorageError(RuntimeError):
    pass


class PrivateDocument:
    def __init__(self, legacy: Path, key: Path, validate):
        self.legacy = legacy
        self.key = key
        self.sealed = SealedFile(legacy.with_suffix(".sealed"), key)
        self.validate = validate

    def _read(self):
        if not self.key.exists():
            raise MemoryStorageError("encryption_key_missing")
        payload = self.sealed.load()
        if not isinstance(payload, dict) or payload.get("version") != 1 or "data" not in payload:
            raise MemoryStorageError("storage_invalid")
        return self.validate(payload["data"])

    def load(self, default):
        try:
            if self.sealed.data_path.exists():
                data = self._read()
                if self.legacy.exists():
                    old = self.validate(json.loads(self.legacy.read_text(encoding="utf-8")))
                    if old != data:
                        raise MemoryStorageError("storage_conflict")
                    self.legacy.unlink()
                return data
            if not self.legacy.exists():
                return default
            data = self.validate(json.loads(self.legacy.read_text(encoding="utf-8")))
            self.save(data)
            if self._read() != data:
                raise MemoryStorageError("storage_invalid")
            self.legacy.unlink()
            return data
        except (InvalidToken, OSError, ValueError, TypeError, KeyError) as exc:
            raise MemoryStorageError("storage_read_failed") from exc

    def save(self, data) -> None:
        try:
            if self.sealed.data_path.exists() and not self.key.exists():
                raise MemoryStorageError("encryption_key_missing")
            self.key.parent.mkdir(parents=True, exist_ok=True)
            self.sealed.data_path.parent.mkdir(parents=True, exist_ok=True)
            self.sealed.save({"version": 1, "data": data})
        except (InvalidToken, OSError, ValueError, TypeError) as exc:
            raise MemoryStorageError("storage_write_failed") from exc
