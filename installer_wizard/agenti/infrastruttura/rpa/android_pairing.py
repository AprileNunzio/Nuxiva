import hashlib
import secrets
import time
from dataclasses import dataclass, field

MAX_ACTIVE = 3
WINDOW = 300
IP_LIMIT = 5
GLOBAL_LIMIT = 20
CODE_DIGITS = 6


class PairingError(PermissionError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass
class Pairing:
    id: str
    token: str
    payload: dict
    expires: float
    code_digest: str = ""
    redeemed: bool = False


@dataclass
class Pairings:
    items: dict[str, Pairing] = field(default_factory=dict)
    failures: dict[str, list[float]] = field(default_factory=dict)
    global_failures: list[float] = field(default_factory=list)

    @staticmethod
    def _digest(code: str) -> str:
        return hashlib.sha256(code.encode("ascii")).hexdigest()

    def _prune(self) -> None:
        now = time.time()
        self.items = {k: v for k, v in self.items.items() if v.expires > now}

    def _recent(self, values: list[float]) -> list[float]:
        now = time.time()
        return [t for t in values if now - t < WINDOW]

    def create(self, token: str, payload: dict, expires: float) -> tuple[str, str]:
        self._prune()
        if len(self.items) >= MAX_ACTIVE:
            raise PairingError("enroll_too_many_tokens")
        taken = {p.code_digest for p in self.items.values()}
        while True:
            code = str(secrets.randbelow(10**CODE_DIGITS)).zfill(CODE_DIGITS)
            if self._digest(code) not in taken:
                break
        handle = secrets.token_urlsafe(9)
        self.items[handle] = Pairing(handle, token, payload, expires, self._digest(code))
        return handle, code

    def revoke(self, handle: str) -> str | None:
        item = self.items.pop(handle, None)
        return item.token if item else None

    def get(self, handle: str) -> Pairing | None:
        self._prune()
        return self.items.get(handle)

    def redeem(self, code: str, ip: str) -> dict:
        self._prune()
        self.global_failures = self._recent(self.global_failures)
        mine = self.failures[ip] = self._recent(self.failures.get(ip, []))
        if len(mine) >= IP_LIMIT or len(self.global_failures) >= GLOBAL_LIMIT:
            raise PairingError("rate_limited")
        digest = self._digest(code) if code.isascii() and code.isdigit() and len(code) == CODE_DIGITS else ""
        match = next((p for p in self.items.values() if digest and p.code_digest == digest and not p.redeemed), None)
        if not match:
            now = time.time()
            mine.append(now)
            self.global_failures.append(now)
            if len(self.global_failures) >= GLOBAL_LIMIT:
                self.items.clear()
            raise PairingError("enroll_code_invalid")
        match.redeemed = True
        match.code_digest = ""
        return match.payload


pairings = Pairings()
