import hmac
import threading

from config import STATE_DIR
from sealed import SealedFile

from features.people import private_store
from features.people.fingerprint.model import FINGERS

FILE = STATE_DIR / "fingerprints.vault"
MAX_PER_PERSON = 10


class Bindings:
    def __init__(self) -> None:
        self._lock = threading.Lock()

    def _sealed(self) -> SealedFile:
        return SealedFile(FILE, private_store.KEY_FILE)

    def _load(self) -> dict:
        data = self._sealed().load()
        data.setdefault("people", {})
        data.setdefault("templates", {})
        return data

    def _save(self, data: dict) -> None:
        self._sealed().save(data)

    def enabled(self, slug: str) -> bool:
        with self._lock:
            return bool(self._load()["people"].get(slug, {}).get("enabled"))

    def set_enabled(self, slug: str, value: bool) -> None:
        with self._lock:
            data = self._load()
            data["people"].setdefault(slug, {})["enabled"] = bool(value)
            self._save(data)

    def bind(self, slug: str, reader_key: str, template: str, finger: str, now: float) -> None:
        if finger not in FINGERS:
            raise ValueError("Dito non valido")
        with self._lock:
            data = self._load()
            fingers = {v["finger"] for v in data["templates"].values() if v["slug"] == slug}
            if finger not in fingers and len(fingers) >= MAX_PER_PERSON:
                raise ValueError("Numero massimo di dita raggiunto")
            data["templates"] = {k: v for k, v in data["templates"].items()
                                 if not (v["slug"] == slug and v["finger"] == finger and v["reader"] == reader_key)}
            data["templates"][f"{reader_key}|{template}"] = {"slug": slug, "finger": finger, "reader": reader_key, "at": now}
            self._save(data)

    def resolve(self, reader_key: str, template: str) -> dict | None:
        with self._lock:
            templates = self._load()["templates"]
        wanted = f"{reader_key}|{template}"
        for key, value in templates.items():
            if hmac.compare_digest(key, wanted):
                return value
        return None

    def fingers(self, slug: str) -> list[dict]:
        with self._lock:
            templates = self._load()["templates"]
        rows = [{"finger": v["finger"], "reader": v["reader"], "at": v["at"]} for v in templates.values() if v["slug"] == slug]
        return sorted(rows, key=lambda r: (FINGERS.index(r["finger"]), r["reader"]))

    def forget(self, slug: str, finger: str = "") -> int:
        with self._lock:
            data = self._load()
            keep = {k: v for k, v in data["templates"].items()
                    if not (v["slug"] == slug and (not finger or v["finger"] == finger))}
            removed = len(data["templates"]) - len(keep)
            data["templates"] = keep
            if not finger:
                data["people"].pop(slug, None)
            self._save(data)
        return removed


bindings = Bindings()
