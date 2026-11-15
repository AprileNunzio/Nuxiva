import hashlib
import hmac
import json
import logging
import os
import secrets
import threading
from pathlib import Path

from permissions.catalog import BY_KEY, CAPABILITIES, LEGACY_ASK, POLICY_VERSION, Level
from settings import paths, protect

log = logging.getLogger("nuxiva.permissions")


def _key() -> bytes:
    paths.ensure()
    if paths.KEY_FILE.exists():
        return protect.unseal(paths.KEY_FILE.read_bytes())
    key = secrets.token_bytes(32)
    paths.KEY_FILE.write_bytes(protect.seal(key))
    return key


def _canonical(levels: dict, folders: list, version: int = 0) -> bytes:
    body = {"levels": levels, "folders": folders}
    if version:
        body["v"] = version
    return json.dumps(body, sort_keys=True, ensure_ascii=False).encode()


class Policy:
    def __init__(self, file: Path = paths.PERMISSIONS_FILE) -> None:
        self.file = file
        self.secret = _key()
        self.lock = threading.Lock()
        self.levels = {c.key: c.default for c in CAPABILITIES}
        self.folders: list[str] = []
        self.tampered = False
        self._load()

    def _mac(self, levels: dict, folders: list, version: int = 0) -> str:
        return hmac.new(self.secret, _canonical(levels, folders, version), hashlib.sha256).hexdigest()

    def _load(self) -> None:
        if not self.file.exists():
            self.save()
            return
        try:
            data = json.loads(self.file.read_text(encoding="utf-8"))
        except ValueError:
            data = {}
        levels, folders = data.get("levels") or {}, data.get("folders") or []
        version = data.get("v", 0)
        if not isinstance(version, int) or isinstance(version, bool) or not 0 <= version <= POLICY_VERSION:
            version = -1
        if not isinstance(levels, dict) or not isinstance(folders, list) or version < 0 or \
                not hmac.compare_digest(str(data.get("mac", "")), self._mac(levels, folders, version)):
            self.tampered = True
            log.error("Il file dei permessi è stato modificato fuori da NUXIVA: ripristino i valori sicuri")
            self.save()
            return
        for key, value in levels.items():
            if key in BY_KEY and value in Level._value2member_map_:
                self.levels[key] = Level(value)
        self.folders = [str(Path(f)) for f in folders if isinstance(f, str) and Path(f).is_absolute()]
        if version < POLICY_VERSION:
            for key in LEGACY_ASK:
                if self.levels[key] is Level.ASK:
                    self.levels[key] = Level.ALLOW
            self.save()

    def save(self) -> None:
        with self.lock:
            levels = {k: v.value for k, v in self.levels.items()}
            body = {"levels": levels, "folders": self.folders, "v": POLICY_VERSION,
                    "mac": self._mac(levels, self.folders, POLICY_VERSION)}
            tmp = self.file.with_suffix(".tmp")
            tmp.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(tmp, self.file)

    def level(self, key: str) -> Level:
        return self.levels[key]

    def set(self, key: str, level: Level) -> None:
        if key not in BY_KEY:
            raise KeyError(key)
        self.levels[key] = Level(level)
        self.save()

    def set_folders(self, folders: list[str]) -> None:
        cleaned = []
        for raw in folders:
            path = Path(raw.strip())
            if not path.is_absolute() or not path.is_dir():
                raise ValueError(f"Cartella non valida: {raw}")
            cleaned.append(str(path.resolve()))
        self.folders = list(dict.fromkeys(cleaned))
        self.save()

    def summary(self) -> dict:
        return {k: v.value for k, v in self.levels.items()}
