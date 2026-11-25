import json
import os
import re
import secrets
import threading
import time
from pathlib import Path

from config import STATE_DIR

ROOT = Path(STATE_DIR) / "holo" / "catalog"
ASSET_ID = re.compile(r"^[a-f0-9]{24}$")
MAX_PER_SUBJECT = 4


class Catalog:

    def __init__(self, root: Path = ROOT) -> None:
        self.root = root
        self.lock = threading.Lock()

    def _index_path(self) -> Path:
        return self.root / "index.json"

    def _load(self) -> dict:
        try:
            data = json.loads(self._index_path().read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        return data if isinstance(data, dict) else {}

    def _save(self, data: dict) -> None:
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        tmp = self._index_path().with_suffix(".tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, separators=(",", ":"))
        tmp.replace(self._index_path())

    def path(self, asset_id: str) -> Path | None:
        if not ASSET_ID.match(str(asset_id or "")):
            return None
        found = self.root / f"{asset_id}.glb"
        return found if found.is_file() else None

    def best(self, key: str) -> dict | None:
        with self.lock:
            entries = self._load().get(key) or []
        alive = [e for e in entries if self.path(e.get("id", ""))]
        return max(alive, key=lambda e: e.get("score", 0)) if alive else None

    def add(self, key: str, glb: bytes, record: dict) -> dict:
        asset_id = secrets.token_hex(12)
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        target = self.root / f"{asset_id}.glb"
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(glb)
        entry = {**record, "id": asset_id, "added": round(time.time(), 3)}
        with self.lock:
            data = self._load()
            items = [entry, *(data.get(key) or [])]
            items.sort(key=lambda e: e.get("score", 0), reverse=True)
            for dropped in items[MAX_PER_SUBJECT:]:
                old = self.path(dropped.get("id", ""))
                if old:
                    old.unlink()
            data[key] = items[:MAX_PER_SUBJECT]
            self._save(data)
        return entry


catalog = Catalog()
