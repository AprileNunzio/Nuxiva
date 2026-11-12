import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import threading
import time

from config import STATE_DIR

log = logging.getLogger("nuxiva.desktop.xr")
FILE = STATE_DIR / "display" / "xr_devices.json"
CODE_TTL = 300
TOKEN_TTL = 30 * 86400
MAX_PENDING = 8
MAX_DEVICES = 16
MAX_FAILURES = 20
FAILURE_WINDOW = 300
DEVICE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")
COOKIE = "nuxiva_xr"


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _text(value, limit: int) -> str:
    return " ".join(re.sub(r"[^\w .,()-]+", " ", str(value or ""), flags=re.UNICODE).split())[:limit]


class XrPairing:

    def __init__(self, clock=time.time) -> None:
        self._clock = clock
        self._lock = threading.Lock()
        self._pending: dict[str, tuple[str, float]] = {}
        self._devices: dict[str, dict] | None = None
        self._failures: list[float] = []

    def _load(self) -> dict[str, dict]:
        if self._devices is None:
            try:
                raw = json.loads(FILE.read_text(encoding="utf-8"))
            except FileNotFoundError:
                raw = {}
            except (OSError, ValueError) as exc:
                log.error("Elenco dei visori illeggibile, nessun visore accoppiato: %s", exc)
                raw = {}
            self._devices = {k: v for k, v in raw.items() if DEVICE.match(str(k)) and isinstance(v, dict)} if isinstance(raw, dict) else {}
        return self._devices

    def _save(self) -> None:
        FILE.parent.mkdir(parents=True, exist_ok=True)
        temporary = FILE.with_suffix(".tmp")
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(self._devices or {}, handle, indent=1)
        os.replace(temporary, FILE)

    def issue(self, approver: str) -> dict:
        now = self._clock()
        code = f"{secrets.randbelow(10 ** 8):08d}"
        with self._lock:
            self._pending = {k: v for k, v in self._pending.items() if v[1] > now}
            if len(self._pending) >= MAX_PENDING:
                self._pending.pop(min(self._pending, key=lambda k: self._pending[k][1]))
            self._pending[_hash(code)] = (_text(approver, 64), now + CODE_TTL)
        return {"code": code, "expires_in": CODE_TTL}

    def redeem(self, code: str, device_id: str, name: str) -> str:
        if not DEVICE.match(str(device_id or "")):
            raise ValueError("invalid_device")
        now = self._clock()
        with self._lock:
            self._failures = [t for t in self._failures if now - t < FAILURE_WINDOW]
            if len(self._failures) >= MAX_FAILURES:
                self._pending.clear()
                raise PermissionError("pairing_locked")
            hit = self._pending.pop(_hash(str(code or "")), None)
            if hit is None or hit[1] < now:
                self._failures.append(now)
                raise PermissionError("pairing_code_invalid")
            devices = self._load()
            if device_id not in devices and len(devices) >= MAX_DEVICES:
                raise ValueError("too_many_devices")
            token = secrets.token_urlsafe(32)
            devices[device_id] = {"name": _text(name, 40) or "Visore", "kind": "xr_headset", "approver": hit[0],
                                  "token": _hash(token), "created": now, "expires": now + TOKEN_TTL, "last_seen": now,
                                  "room": devices.get(device_id, {}).get("room")}
            self._save()
        return token

    def authenticate(self, token: str | None) -> str | None:
        if not token or len(token) > 128:
            return None
        wanted = _hash(token)
        now = self._clock()
        with self._lock:
            for device_id, device in self._load().items():
                if hmac.compare_digest(str(device.get("token", "")), wanted):
                    return device_id if float(device.get("expires", 0)) > now else None
        return None

    def device(self, device_id: str) -> dict | None:
        with self._lock:
            found = self._load().get(device_id)
            return {k: v for k, v in found.items() if k != "token"} if found else None

    def listing(self) -> list[dict]:
        with self._lock:
            return [{"id": k, **{f: v for f, v in d.items() if f != "token"}} for k, d in sorted(self._load().items())]

    def set_room(self, device_id: str, room: str | None) -> None:
        with self._lock:
            devices = self._load()
            if device_id not in devices:
                raise KeyError(device_id)
            devices[device_id]["room"] = room
            self._save()

    def revoke(self, device_id: str) -> None:
        with self._lock:
            devices = self._load()
            if devices.pop(device_id, None) is None:
                raise KeyError(device_id)
            self._save()


pairing = XrPairing()
