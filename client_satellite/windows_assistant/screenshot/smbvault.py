import hashlib
import json
import os
import re
import secrets
from dataclasses import dataclass, field
from pathlib import Path

USER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._\\-]{0,63}$")
TARGET = re.compile(r"^smb://[A-Za-z0-9][A-Za-z0-9.-]{0,252}/[A-Za-z0-9_-]{1,64}$")
MAX_PASSWORD = 256
MAX_FILE = 8192


class CredentialError(ValueError):
    pass


@dataclass(frozen=True)
class Login:
    user: str
    password: str = field(repr=False)


def parse(payload) -> tuple[str, str, str] | None:
    if not isinstance(payload, dict) or not payload:
        return None
    target = str(payload.get("target") or "").strip().rstrip("/")
    user = str(payload.get("user") or "").strip()
    password = str(payload.get("password") or "")
    if not TARGET.match(target) or not USER.match(user):
        raise CredentialError("credentials")
    if not password or len(password) > MAX_PASSWORD or any(ord(c) < 32 or ord(c) == 127 for c in password):
        raise CredentialError("credentials")
    return target.lower(), user, password


class Vault:
    def __init__(self, path: Path, seal, unseal) -> None:
        self.path = path
        self.seal, self.unseal = seal, unseal
        self.fingerprint = ""
        self.key = secrets.token_bytes(32)

    def update(self, payload) -> bool:
        entry = parse(payload)
        if entry is None:
            return self.forget()
        fingerprint = self._fingerprint(entry)
        if fingerprint == self.fingerprint and self.path.exists():
            return False
        target, user, password = entry
        sealed = self.seal(json.dumps({"target": target, "user": user, "password": password}).encode("utf-8"))
        self._write(sealed)
        self.fingerprint = fingerprint
        return True

    def forget(self) -> bool:
        self.fingerprint = ""
        if not self.path.exists():
            return False
        self.path.unlink()
        return True

    def login(self, target: str) -> Login | None:
        try:
            raw = self.path.read_bytes()
        except FileNotFoundError:
            return None
        if len(raw) > MAX_FILE:
            raise CredentialError("vault")
        data = json.loads(self.unseal(raw).decode("utf-8"))
        if not isinstance(data, dict) or data.get("target") != str(target or "").rstrip("/").lower():
            return None
        return Login(str(data.get("user") or ""), str(data.get("password") or ""))

    def _fingerprint(self, entry: tuple) -> str:
        return hashlib.blake2b("\0".join(entry).encode("utf-8"), digest_size=16, key=self.key).hexdigest()

    def _write(self, data: bytes) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_name(f".{self.path.name}.{secrets.token_hex(6)}")
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o600)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, self.path)
        finally:
            if temp.exists():
                temp.unlink()
