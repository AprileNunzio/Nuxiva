import hashlib
import json
import logging
import os
import secrets
import time

from config import STATE_DIR

log = logging.getLogger("nuxiva.enrollment")

TOKENS_FILE = STATE_DIR / "node_enrollment.json"
DEFAULT_TTL = 24 * 3600
MAX_TTL = 7 * 24 * 3600
MAX_ACTIVE = 16


class EnrollmentError(PermissionError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class EnrollmentTokens:
    def __init__(self) -> None:
        self.items: dict[str, dict] = self._load()

    @staticmethod
    def _load() -> dict[str, dict]:
        if not TOKENS_FILE.exists():
            return {}
        try:
            data = json.loads(TOKENS_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            log.error("Token di iscrizione illeggibili, vengono azzerati: %s", exc)
            return {}
        return data if isinstance(data, dict) else {}

    def _save(self) -> None:
        tmp = TOKENS_FILE.with_suffix(".tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(self.items, handle)
        os.replace(tmp, TOKENS_FILE)

    def _prune(self) -> None:
        now = time.time()
        self.items = {k: v for k, v in self.items.items() if float(v.get("expires", 0)) > now}

    def issue(self, ttl: int = DEFAULT_TTL) -> tuple[str, float]:
        self._prune()
        if len(self.items) >= MAX_ACTIVE:
            raise EnrollmentError("enroll_too_many_tokens")
        lifetime = max(60, min(int(ttl), MAX_TTL))
        token = secrets.token_urlsafe(32)
        expires = time.time() + lifetime
        self.items[_digest(token)] = {"expires": expires}
        self._save()
        return token, expires

    def verify(self, token: str) -> str:
        self._prune()
        digest = _digest(str(token or ""))
        if digest not in self.items:
            raise EnrollmentError("enroll_token_invalid")
        return digest

    def burn(self, digest: str) -> None:
        self.items.pop(digest, None)
        self._save()

    def active(self) -> int:
        self._prune()
        return len(self.items)


tokens = EnrollmentTokens()
