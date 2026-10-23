import hashlib
import hmac
import json
import re
import secrets
import threading
import time

from config import STATE_DIR
from sealed import write_private

from features.people.vitals.model import KINDS

FILE = STATE_DIR / "vitals_devices.json"
MAX_PER_PERSON = 6
MAX_TOTAL = 64
MAC_RE = re.compile(r"^[0-9A-F]{2}(:[0-9A-F]{2}){5}$")


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def clean_label(value) -> str:
    return " ".join(str(value or "").split())[:40]


def clean_address(value) -> str:
    address = str(value or "").strip().upper().replace("-", ":")
    if not MAC_RE.match(address):
        raise ValueError("Indirizzo Bluetooth non valido")
    return address


class Book:
    def __init__(self) -> None:
        self._data: dict | None = None
        self._lock = threading.Lock()

    def _all(self) -> dict:
        if self._data is None:
            try:
                loaded = json.loads(FILE.read_text(encoding="utf-8")) if FILE.exists() else {}
            except (OSError, ValueError):
                loaded = {}
            self._data = loaded if isinstance(loaded, dict) else {}
        return self._data

    def _save(self) -> None:
        FILE.parent.mkdir(parents=True, exist_ok=True)
        write_private(FILE, json.dumps(self._all(), ensure_ascii=False).encode("utf-8"))

    def add(self, slug: str, kind: str, label: str, address: str = "") -> tuple[dict, str]:
        if kind not in KINDS:
            raise ValueError("Tipo di dispositivo non valido")
        with self._lock:
            data = self._all()
            if len(data) >= MAX_TOTAL:
                raise ValueError("Numero massimo di dispositivi raggiunto")
            if sum(1 for d in data.values() if d["slug"] == slug) >= MAX_PER_PERSON:
                raise ValueError("Numero massimo di dispositivi per persona raggiunto")
            device = {"id": secrets.token_hex(5), "slug": slug, "kind": kind, "label": clean_label(label) or kind, "created": time.time(), "last": 0.0}
            token = ""
            if kind == "ble":
                device["address"] = clean_address(address)
                if any(d.get("address") == device["address"] for d in data.values()):
                    raise ValueError("Dispositivo già registrato")
            else:
                token = secrets.token_urlsafe(32)
                device["token"] = _hash(token)
            data[device["id"]] = device
            self._save()
        return self.public(device), token

    def rotate(self, slug: str, device_id: str) -> str:
        with self._lock:
            device = self._all().get(device_id)
            if not device or device["slug"] != slug or device["kind"] == "ble":
                raise KeyError(device_id)
            token = secrets.token_urlsafe(32)
            device["token"] = _hash(token)
            self._save()
        return token

    def remove(self, slug: str, device_id: str) -> bool:
        with self._lock:
            device = self._all().get(device_id)
            if not device or device["slug"] != slug:
                return False
            del self._all()[device_id]
            self._save()
        return True

    def forget_person(self, slug: str) -> None:
        with self._lock:
            data = self._all()
            for key in [k for k, d in data.items() if d["slug"] == slug]:
                del data[key]
            self._save()

    def by_token(self, token: str) -> dict | None:
        digest = _hash(str(token))
        for device in self._all().values():
            if device.get("token") and hmac.compare_digest(device["token"], digest):
                return device
        return None

    def by_address(self, address: str) -> dict | None:
        return next((d for d in self._all().values() if d.get("address") == address), None)

    def of(self, slug: str) -> list[dict]:
        return [self.public(d) for d in self._all().values() if d["slug"] == slug]

    def addresses(self) -> list[str]:
        return [d["address"] for d in self._all().values() if d.get("address")]

    def touch(self, device: dict, now: float | None = None) -> None:
        device["last"] = now or time.time()

    @staticmethod
    def public(device: dict) -> dict:
        return {k: v for k, v in device.items() if k != "token"}


book = Book()
