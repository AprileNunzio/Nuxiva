import json
import logging
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

log = logging.getLogger("nuxiva.vault")
MAX_BYTES = 4 << 20


class VaultError(OSError):
    pass


class KeyFile:
    def __init__(self, path: Path, seal, unseal) -> None:
        self.path, self.seal, self.unseal = path, seal, unseal

    def load(self) -> bytes:
        if self.path.is_file():
            try:
                return self.unseal(self.path.read_bytes())
            except OSError as exc:
                raise VaultError(f"chiave della memoria illeggibile: {exc}") from exc
        key = Fernet.generate_key()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_bytes(self.seal(key))
        os.replace(tmp, self.path)
        return key


class Vault:
    def __init__(self, path: Path, key: bytes) -> None:
        self.path, self.fernet = path, Fernet(key)

    def read(self) -> dict:
        if not self.path.is_file():
            return {}
        try:
            raw = self.path.read_bytes()
            if len(raw) > MAX_BYTES:
                raise InvalidToken
            data = json.loads(self.fernet.decrypt(raw).decode("utf-8"))
        except (InvalidToken, ValueError, OSError) as exc:
            broken = self.path.with_suffix(".broken")
            try:
                os.replace(self.path, broken)
            except OSError as move:
                raise VaultError(f"memoria locale illeggibile e non spostabile: {move}") from exc
            log.error("Memoria locale non valida (%s): spostata in %s", exc, broken)
            return {}
        return data if isinstance(data, dict) else {}

    def write(self, data: dict) -> None:
        payload = self.fernet.encrypt(json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        if len(payload) > MAX_BYTES:
            raise VaultError("memoria locale troppo grande")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_bytes(payload)
        os.replace(tmp, self.path)
